"""真实多进程验证状态更新，真实 Hook 验证会话归属和未知结果后的重试。"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]
import post_tool_lint
from detect_lang import LANG_COMMANDS


class StateStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-state-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "state"
        self.env = {**os.environ, "CODEGUARD_HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1"}

    def test_parallel_statistics_skip_events_and_audits_do_not_lose_updates(self):
        source = (
            "import sys,time;from pathlib import Path;"
            "sys.path[:0]=[sys.argv[1]+'/scripts',sys.argv[1]+'/hooks'];"
            "import post_tool_lint,gate_lib;"
            "root=Path(sys.argv[2]);(root/('ready-'+sys.argv[3])).touch();\n"
            "while not (root/'go').exists(): time.sleep(0.005)\n"
            "for i in range(35):\n"
            " post_tool_lint.bump_state('python',True)\n"
            " gate_lib.record_skip_event('fixture')\n"
            " gate_lib.record_gate_decision(root,'python',[sys.argv[3],str(i)],0,'PASS','fixture',limit=1000)\n")
        processes = [subprocess.Popen([sys.executable, "-c", source, str(ROOT), str(self.root), str(n)],
                                      env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for n in range(6)]
        try:
            deadline = time.monotonic() + 15
            while len(list(self.root.glob("ready-*"))) != 6 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(6, len(list(self.root.glob("ready-*"))))
            (self.root / "go").touch()
            for proc in processes:
                _out, err = proc.communicate(timeout=30)
                self.assertEqual(0, proc.returncode, err)
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate()
        state = json.loads((self.home / "session_state.json").read_text())
        self.assertEqual(210, state["python"]["total"])
        self.assertEqual(210, state["python"]["passed"])
        self.assertEqual(210, state["_skip"]["count"])
        logs = [json.loads(line) for line in (self.home / "gate-decisions.jsonl").read_text().splitlines()]
        self.assertEqual(210, len(logs))
        self.assertEqual(210, len({tuple(row["cmd"]) for row in logs}))

    def hook(self, name, repo, payload):
        result = subprocess.run([sys.executable, str(ROOT / "hooks" / name)], cwd=repo,
                                env=self.env, input=json.dumps(payload), text=True,
                                capture_output=True, timeout=20, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("fail-open", result.stderr)
        return result.stdout

    def repo(self, name):
        repo = self.root / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        (repo / "a.py").write_text("print(1)\n")
        return repo

    @unittest.skipIf(shutil.which("ruff") is None,
                     "ruff 不在 PATH：本用例依赖真实 python lint 判定（见 requirements-dev.txt）")
    def test_stop_does_not_consume_another_sessions_statistics(self):
        repo = self.repo("repo")
        for session in ("first", "second"):
            out = self.hook("post_tool_lint.py", repo,
                            {"session_id": session, "tool_input": {"file_path": str(repo / "a.py")}})
            self.assertIn("passed", out)
        first = self.hook("stop_summary.py", repo, {"session_id": "first"})
        second = self.hook("stop_summary.py", repo, {"session_id": "second"})
        self.assertIn("共 1 次检查", first)
        self.assertIn("共 1 次检查", second)

    @unittest.skipIf(shutil.which("ruff") is None,
                     "ruff 不在 PATH：本用例依赖真实 python lint 判定（见 requirements-dev.txt）")
    def test_same_session_in_two_worktrees_has_separate_statistics(self):
        left, right = self.repo("left"), self.root / "right"
        for args in (("config", "user.name", "fixture"), ("config", "user.email", "test@example.invalid"),
                     ("config", "core.hooksPath", "/dev/null"), ("add", "a.py"), ("commit", "-qm", "base"),
                     ("worktree", "add", "-q", "--detach", str(right))):
            subprocess.run(["git", *args], cwd=left, check=True, capture_output=True)
        for repo in (left, right):
            out = self.hook("post_tool_lint.py", repo,
                            {"session_id": "same", "tool_input": {"file_path": str(repo / "a.py")}})
            self.assertIn("passed", out)
        for repo in (left, right):
            out = self.hook("stop_summary.py", repo, {"session_id": "same"})
            self.assertIn("共 1 次检查", out)

    def test_unknown_result_does_not_suppress_immediate_retry(self):
        target = self.root / "a.py"
        target.write_text("print(1)\n")
        checker = self.root / "checker.py"
        checker.write_text("from pathlib import Path\np=Path('attempts')\n"
                           "n=int(p.read_text())+1 if p.exists() else 1\np.write_text(str(n))\n"
                           "raise SystemExit(2 if n==1 else 0)\n")
        commands = {"lint": [sys.executable, str(checker), "{file}"]}
        with patch.dict(os.environ, self.env), patch.dict(LANG_COMMANDS, {"python": commands}), \
                patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(target)}), \
                patch.object(post_tool_lint, "find_project_root", return_value=self.root), \
                patch.object(post_tool_lint, "load_user_config", return_value={"auto_fix_on_save": False}), \
                patch.object(post_tool_lint, "DEDUP_FILE", self.home / "hook_dedup.json"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                post_tool_lint.main()
                post_tool_lint.main()
            self.assertEqual("2", (self.root / "attempts").read_text())
            self.assertIn("UNVERIFIED", out.getvalue())
            self.assertIn("passed", out.getvalue())

    @unittest.skipIf(shutil.which("ruff") is None,
                     "ruff 不在 PATH：本用例依赖真实 python lint 判定（见 requirements-dev.txt）")
    def test_duplicate_hard_gate_event_cannot_turn_a_rejection_into_permission(self):
        repo = self.repo("repo")
        (repo / "a.py").write_text("undefined_variable()\n")
        subprocess.run(["git", "add", "a.py"], cwd=repo, check=True, capture_output=True)
        payload = {"session_id": "one", "tool_use_id": "same-event",
                   "tool_input": {"command": "git commit -m fixture"}}
        for _ in range(2):
            result = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                                    cwd=repo, env=self.env, input=json.dumps(payload), text=True,
                                    capture_output=True, timeout=20, check=False)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("F821", result.stderr)

    def test_transaction_error_keeps_previous_data_and_removes_temporary_files(self):
        from codeguard.storage import update_json

        path = self.root / "sample.json"
        path.write_text('{"count": 3}')
        def failing_change(state):
            state["count"] = 4
            raise ValueError("fixture")
        with self.assertRaises(ValueError):
            update_json(path, failing_change)
        self.assertEqual({"count": 3}, json.loads(path.read_text()))
        with patch("codeguard.storage.os.replace", side_effect=OSError("disk failure")), self.assertRaises(OSError):
            update_json(path, lambda state: state.update(count=5))
        self.assertEqual({"count": 3}, json.loads(path.read_text()))
        self.assertEqual([], list(self.root.glob("*.tmp")))

    @unittest.skipIf(shutil.which("ruff") is None,
                     "ruff 不在 PATH：本用例依赖真实 python lint 判定（见 requirements-dev.txt）")
    def test_same_hard_event_rechecks_changed_content_after_permission(self):
        repo = self.repo("repo")
        payload = {"session_id": "one", "tool_use_id": "same-event",
                   "tool_input": {"command": "git commit -m fixture"}}
        for content, expected_code in (("print(1)\n", 0), ("undefined_variable()\n", 2)):
            (repo / "a.py").write_text(content)
            subprocess.run(["git", "add", "a.py"], cwd=repo, check=True, capture_output=True)
            result = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                                    cwd=repo, env=self.env, input=json.dumps(payload), text=True,
                                    capture_output=True, timeout=20, check=False)
            self.assertEqual(expected_code, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("fail-open", result.stderr)
            if expected_code == 2:
                self.assertIn("F821", result.stderr)

    def test_unverified_prompt_is_not_silenced_by_seen_event(self):
        repo = self.repo("repo")
        (repo / "ruff.toml").write_text("invalid = [\n")
        subprocess.run(["git", "add", "a.py"], cwd=repo, check=True, capture_output=True)
        payload = {"session_id": "same", "user_prompt": "提交 Python 代码"}
        for _ in range(2):
            out = self.hook("user_prompt_validator.py", repo, payload)
            self.assertIn("未验证", out)

    def test_failed_observer_is_retried_before_completion_is_recorded(self):
        from codeguard import hook_state

        self.assertTrue(hasattr(hook_state, "observe_once"), "必须按完成结果去重，不能预占检查事件")
        attempts = []
        def observe():
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError("fixture")
            return 0
        with patch.dict(os.environ, self.env):
            with self.assertRaises(RuntimeError):
                hook_state.observe_once("start:fixture", observe)
            self.assertEqual(0, hook_state.observe_once("start:fixture", observe))
            self.assertEqual(0, hook_state.observe_once("start:fixture", observe))
        self.assertEqual(2, len(attempts))

    def test_stop_consumption_and_concurrent_new_writes_do_not_lose_counts(self):
        from codeguard.storage import take_json

        source = ("import sys;sys.path[:0]=[sys.argv[1]+'/scripts',sys.argv[1]+'/hooks'];"
                  "import post_tool_lint;\nfor _ in range(80): post_tool_lint.bump_state('python',True)\n")
        workers = [subprocess.Popen([sys.executable, "-c", source, str(ROOT)], env=self.env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(3)]
        total = 0
        deadline = time.monotonic() + 20
        try:
            while any(p.poll() is None for p in workers) and time.monotonic() < deadline:
                total += take_json(self.home / "session_state.json").get("python", {}).get("total", 0)
                time.sleep(0.003)
            for worker in workers:
                _out, err = worker.communicate(timeout=5)
                self.assertEqual(0, worker.returncode, err)
            total += take_json(self.home / "session_state.json").get("python", {}).get("total", 0)
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                worker.communicate()
        self.assertEqual(240, total)


if __name__ == "__main__":
    unittest.main()
