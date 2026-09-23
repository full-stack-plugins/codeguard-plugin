"""真实 Git 与检查进程覆盖缓存身份；不以缓存文件存在作为行为证明。"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]
import gate_lib
import post_tool_lint
import user_prompt_validator
from codeguard import gate as gate_application
from detect_lang import LANG_COMMANDS
from user_config import get_overrides


class CacheIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-cache-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", "/dev/null")
        (self.repo / "a.py").write_text("value = 0\n")
        self.git("add", "a.py")
        self.git("commit", "-qm", "base")
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"CODEGUARD_HOME": str(self.root / "home")}).start()
        patch.object(gate_application, "_gate_cache_path", return_value=self.root / "cache.json").start()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True,
                              text=True, capture_output=True).stdout.strip()

    def checker(self, body):
        script = self.root / "checker.py"
        counter = self.root / "count"
        script.write_text("from pathlib import Path\n"
                          f"p=Path({str(counter)!r})\n"
                          "n=int(p.read_text())+1 if p.exists() else 1\np.write_text(str(n))\n" + body)
        definition = {"lint": [sys.executable, str(script)], "probe": [sys.executable, "--version"]}
        patch.dict(LANG_COMMANDS, {"python": definition}).start()
        (self.repo / "a.py").write_text("value = 1\n")
        return counter

    def run_gate(self, cfg=None, **kwargs):
        return gate_lib.run_gate(self.repo, cfg or {}, ["python"], **kwargs)

    def test_equal_size_equal_mtime_edit_invalidates_actual_result(self):
        count = self.checker("import sys\nraise SystemExit(1 if '= 2' in Path('a.py').read_text() else 0)\n")
        self.assertEqual(([], []), self.run_gate())
        path = self.repo / "a.py"
        before = path.stat()
        path.write_text("value = 2\n")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        failures, _ = self.run_gate()
        self.assertEqual("2", count.read_text())
        self.assertEqual("python", failures[0][0])

    def test_user_configuration_change_executes_again(self):
        count = self.checker("raise SystemExit(0)\n")
        self.run_gate({"lint_timeout_seconds": 10})
        self.run_gate({"lint_timeout_seconds": 20})
        self.assertEqual("2", count.read_text())

    def test_unknown_is_not_reused_after_checker_recovers(self):
        count = self.checker("raise SystemExit(2 if n == 1 else 0)\n")
        self.assertTrue(self.run_gate()[1])
        self.assertEqual(([], []), self.run_gate())
        self.assertEqual("2", count.read_text())

    def test_project_override_refreshes_in_same_process_even_with_same_stat(self):
        path = self.repo / "codeguard.json"
        path.write_text('{"gate_scope":"delta","exclude":["old"]}')
        self.assertEqual(["old"], get_overrides(self.repo)["exclude"])
        before = path.stat()
        path.write_text('{"gate_scope":"delta","exclude":["new"]}')
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(["new"], get_overrides(self.repo)["exclude"])

    def test_linked_worktree_index_content_is_in_identity(self):
        other = self.root / "linked"
        self.git("worktree", "add", "-q", "--detach", str(other))
        target = other / "a.py"
        target.write_text("value = 1\n")
        self.git("add", "a.py", cwd=other)
        target.write_text("value = 9\n")
        before = target.stat()
        first = gate_lib._gate_cache_key(other, ["python"])
        target.write_text("value = 2\n")
        self.git("add", "a.py", cwd=other)
        target.write_text("value = 9\n")
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertNotEqual(first, gate_lib._gate_cache_key(other, ["python"]))

    def test_unmodified_inputs_reuse_soft_result_but_never_exact_gate(self):
        count = self.checker("raise SystemExit(0)\n")
        self.git("add", "a.py")
        self.run_gate()
        self.run_gate()
        self.assertEqual("1", count.read_text())
        self.run_gate(exact=True, lanes=("staged",))
        self.assertEqual("2", count.read_text())

    def test_future_dated_entry_is_not_reused(self):
        count = self.checker("raise SystemExit(0)\n")
        self.run_gate()
        path = self.root / "cache.json"
        data = json.loads(path.read_text())
        data["ts"] += 100000
        path.write_text(json.dumps(data))
        self.run_gate()
        self.assertEqual("2", count.read_text())

    def test_save_does_not_mark_content_changed_during_check_as_completed(self):
        count = self.checker("if n == 1: Path('a.py').write_text('value = 2\\n')\nraise SystemExit(0)\n")
        patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(self.repo / "a.py")}).start()
        patch.object(post_tool_lint, "find_project_root", return_value=self.repo).start()
        patch.object(post_tool_lint, "load_user_config", return_value={"auto_fix_on_save": False}).start()
        with contextlib.redirect_stdout(io.StringIO()):
            post_tool_lint.main()
            post_tool_lint.main()
        self.assertEqual("2", count.read_text())

    def test_prompt_dedup_cannot_hide_new_failure_for_same_text(self):
        count = self.checker("import sys\nprint('F821: fixture')\n"
                             "raise SystemExit(1 if '= 2' in Path('a.py').read_text() else 0)\n")
        patch.object(user_prompt_validator, "read_payload", return_value={
            "session_id": "same", "user_prompt": "提交 Python 代码"}).start()
        patch.object(user_prompt_validator, "find_project_root", return_value=self.repo).start()
        patch.object(user_prompt_validator, "load_user_config", return_value={}).start()
        patch.object(user_prompt_validator, "notify", return_value=None).start()
        with contextlib.redirect_stdout(io.StringIO()):
            user_prompt_validator.main()
        (self.repo / "a.py").write_text("value = 2\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            user_prompt_validator.main()
        self.assertEqual("2", count.read_text())
        self.assertIn("F821", out.getvalue())

    def test_budget_failure_disables_cache_not_checking(self):
        from codeguard import fingerprint
        count = self.checker("raise SystemExit(0)\n")
        with patch.object(fingerprint, "repository_identity",
                          partial(fingerprint.repository_identity, max_bytes=1)):
            self.assertEqual(([], []), self.run_gate())
            self.assertEqual(([], []), self.run_gate())
        self.assertEqual("2", count.read_text())

    def test_malformed_cache_result_is_rechecked(self):
        count = self.checker("raise SystemExit(0)\n")
        self.run_gate()
        path = self.root / "cache.json"
        data = json.loads(path.read_text())
        data["failures"] = {"status": "PASS"}
        path.write_text(json.dumps(data))
        self.assertEqual(([], []), self.run_gate())
        self.assertEqual("2", count.read_text())

    def test_ignored_linter_configuration_invalidates_save_dedup(self):
        self.checker("raise SystemExit(0)\n")
        (self.repo / ".gitignore").write_text("ruff.toml\n")
        config = self.repo / "ruff.toml"
        config.write_text('line-length = 88\n')
        patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(self.repo / "a.py")}).start()
        patch.object(post_tool_lint, "find_project_root", return_value=self.repo).start()
        patch.object(post_tool_lint, "load_user_config", return_value={"auto_fix_on_save": False}).start()
        with contextlib.redirect_stdout(io.StringIO()):
            post_tool_lint.main()
        before = config.stat()
        config.write_text('line-length = 99\n')
        os.utime(config, ns=(before.st_atime_ns, before.st_mtime_ns))
        with contextlib.redirect_stdout(io.StringIO()):
            post_tool_lint.main()
        self.assertEqual("2", (self.root / "count").read_text())

    def test_push_upstream_change_invalidates_identity(self):
        self.git("branch", "baseline")
        (self.repo / "a.py").write_text("value = 1\n")
        self.git("add", "a.py")
        self.git("commit", "-qm", "next")
        branch = self.git("branch", "--show-current")
        self.git("config", f"branch.{branch}.remote", ".")
        self.git("config", f"branch.{branch}.merge", "refs/heads/baseline")
        before = gate_lib._gate_cache_key(self.repo, ["python"], mode="push")
        self.git("update-ref", "refs/heads/baseline", "HEAD")
        self.assertNotEqual(before, gate_lib._gate_cache_key(self.repo, ["python"], mode="push"))

    def test_newline_filename_content_is_not_lost_in_git_listing(self):
        target = self.repo / "line\nbreak.py"
        target.write_text("value = 1\n")
        self.git("add", target.name)
        before = gate_lib._gate_cache_key(self.repo, ["python"])
        stamp = target.stat()
        target.write_text("value = 2\n")
        os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertNotEqual(before, gate_lib._gate_cache_key(self.repo, ["python"]))

    def test_save_content_change_with_restored_mtime_reexecutes(self):
        count = self.checker("raise SystemExit(0)\n")
        patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(self.repo / "a.py")}).start()
        patch.object(post_tool_lint, "find_project_root", return_value=self.repo).start()
        patch.object(post_tool_lint, "load_user_config", return_value={"auto_fix_on_save": False}).start()
        with contextlib.redirect_stdout(io.StringIO()):
            post_tool_lint.main()
        target = self.repo / "a.py"
        stamp = target.stat()
        target.write_text("value = 2\n")
        os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with contextlib.redirect_stdout(io.StringIO()):
            post_tool_lint.main()
        self.assertEqual("2", count.read_text())

    def test_missing_or_external_symlink_input_disables_cache(self):
        from codeguard.fingerprint import repository_identity
        outside = self.root / "external.py"
        outside.write_text("value = 1\n")
        (self.repo / "link.py").symlink_to(outside)
        self.assertIsNone(repository_identity(self.repo))
        self.assertIsNone(repository_identity(self.root / "missing"))


if __name__ == "__main__":
    unittest.main()
