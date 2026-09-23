"""门禁应用独立执行、准确审计归属和基线不确定性回归。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]
import gate_lib


class GateApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-application-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "state"
        self.repo = self.root / "repo"
        self.repo.mkdir()
        for args in (("init", "-q"), ("config", "user.name", "fixture"),
                     ("config", "user.email", "fixture@example.invalid"),
                     ("config", "core.hooksPath", "/dev/null")):
            self.git(*args)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True,
                              text=True, capture_output=True).stdout

    @unittest.skipIf(shutil.which("ruff") is None,
                     "ruff 不在 PATH：本用例依赖真实 python lint 判定（见 requirements-dev.txt）")
    def test_application_runs_without_hook_directory_or_host_modules(self):
        script = ("import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);"
                  "from codeguard.gate import run_gate;"
                  "result=run_gate(Path(sys.argv[2]),{},['python'],exact=True);"
                  "print(json.dumps([result, 'gate_lib' in sys.modules, 'mcp' in sys.modules]))")
        (self.repo / "a.py").write_text("undefined_name()\n")
        self.git("add", "a.py")
        proc = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT / "scripts"), str(self.repo)],
                              env={**os.environ, "CODEGUARD_HOME": str(self.home)},
                              capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(0, proc.returncode, proc.stderr)
        result, legacy_imported, host_imported = json.loads(proc.stdout)
        self.assertIn("F821", result[0][0][1])
        self.assertFalse(legacy_imported)
        self.assertFalse(host_imported)

    @unittest.skipIf(shutil.which("ruff") is None,
                     "ruff 不在 PATH：本用例依赖真实 python lint 判定（见 requirements-dev.txt）")
    def test_snapshot_audit_has_original_worktree_session_and_actual_argv(self):
        (self.repo / "a.py").write_text("undefined_name()\n")
        self.git("add", "a.py")
        payload = {"session_id": "review-session", "tool_input": {"command": "git commit -m fixture"}}
        proc = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")], cwd=self.repo,
                              env={**os.environ, "CODEGUARD_HOME": str(self.home)},
                              input=json.dumps(payload), text=True, capture_output=True, timeout=20, check=False)
        self.assertEqual(2, proc.returncode, proc.stderr)
        entries = [json.loads(line) for line in (self.home / "gate-decisions.jsonl").read_text().splitlines()]
        entry = next(row for row in entries if row["lang"] == "python")
        self.assertEqual(str(self.repo), entry["worktree"])
        self.assertTrue(entry.get("session_scope"))
        self.assertIn("a.py", entry["cmd"])
        self.assertNotEqual(str(self.repo), entry.get("execution_root"))

    def test_unknown_baseline_output_never_grants_waiver(self):
        (self.repo / "a.py").write_text("BAD\n")
        self.git("add", "a.py")
        self.git("commit", "-qm", "base")
        command = [sys.executable, "-c", "print('F821 undefined'); raise SystemExit(2)", "{file}"]
        self.assertIsNone(gate_lib.baseline_stale_finding(self.repo, "a.py", command, "F821 undefined"))

    def test_unknown_current_check_is_not_hidden_by_known_baseline_failure(self):
        (self.repo / "a.py").write_text("OLD\n")
        self.git("add", "a.py")
        self.git("commit", "-qm", "base")
        (self.repo / "a.py").write_text("NEW\n")
        command = [sys.executable, "-c", ("import pathlib,sys;print('F821 undefined');"
                   "raise SystemExit(2 if 'NEW' in pathlib.Path(sys.argv[1]).read_text() else 1)"), "{file}"]
        with patch.dict(gate_lib.LANG_COMMANDS, {"python": {"lint": command}}), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            failures, notes = gate_lib._run_gate_uncached(self.repo, {}, ["python"],
                                                         scope="delta", changed=["a.py"])
        self.assertEqual([], failures)
        self.assertTrue(any("未验证" in note for note in notes), notes)
        self.assertFalse(any("豁免" in note for note in notes), notes)

    def test_parallel_checks_aggregate_in_requested_order_and_audit_each_command(self):
        commands = {
            lang: {"lint": [sys.executable, "-c",
                            f"import time;time.sleep({delay});print('F821 {lang}');raise SystemExit(1)"]}
            for lang, delay in (("python", 0.15), ("javascript", 0.01))
        }
        with patch.dict(gate_lib.LANG_COMMANDS, commands), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            failures, notes = gate_lib._run_gate_uncached(self.repo, {}, ["python", "javascript"])
        self.assertEqual(["python", "javascript"], [row[0] for row in failures])
        self.assertEqual([], notes)
        entries = [json.loads(line) for line in (self.home / "gate-decisions.jsonl").read_text().splitlines()]
        self.assertEqual(["python", "javascript"], [entry["lang"] for entry in entries])
        for entry in entries:
            self.assertEqual(commands[entry["lang"]]["lint"], entry["cmd"])
            self.assertEqual(1, entry["rc"])
            self.assertEqual("FAIL", entry["status"])

    def test_parallel_worker_exception_preserves_other_failure_and_audit(self):
        from codeguard import gate as gate_application

        original = gate_application.check_language
        command = [sys.executable, "-c", "print('F821 javascript');raise SystemExit(1)"]

        def check_or_crash(root, cfg, lang, **kwargs):
            if lang == "python":
                raise RuntimeError("SECRET_SENTINEL")
            return original(root, cfg, lang, **kwargs)

        with patch.dict(gate_application.LANG_COMMANDS, {"javascript": {"lint": command}}), \
                patch.object(gate_application, "check_language", side_effect=check_or_crash), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            failures, notes = gate_application.run_batch(
                self.repo, {}, ["python", "javascript"], scope="repo")

        self.assertEqual(["javascript"], [failure[0] for failure in failures])
        self.assertTrue(any("python UNVERIFIED" in note for note in notes), notes)
        self.assertNotIn("SECRET_SENTINEL", "\n".join(notes))
        entries = [json.loads(line) for line in (self.home / "gate-decisions.jsonl").read_text().splitlines()]
        self.assertEqual(["javascript"], [entry["lang"] for entry in entries])
