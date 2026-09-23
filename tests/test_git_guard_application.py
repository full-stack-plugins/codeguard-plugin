"""PreToolUse 的 Git 决策返回结构化结果，不直接写宿主 stdout/stderr。"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]

import pre_tool_git_guard


class GitGuardApplicationTests(unittest.TestCase):
    def test_explicit_non_git_target_never_falls_back_to_callers_repo(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-explicit-target-") as tmp:
            base = Path(tmp).resolve()
            repo, plain = base / "repo", base / "plain"
            repo.mkdir()
            plain.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            for command in (f"cd {plain} && git push origin main",
                            f"git -C {plain} commit -m x"):
                with self.subTest(command=command), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])) as run_gate, \
                        patch.object(git_guard_application, "fallback_roots", return_value=[]) as fallback, \
                        patch.object(git_guard_application, "check_commit_safety", return_value=[]):
                    result = git_guard_application.evaluate_git_command(
                        command, cwd=repo, load_config=dict)
                    self.assertEqual(2, result.exit_code)
                    self.assertIn(str(plain), result.stderr)
                    self.assertIn("目标", result.stderr)
                    run_gate.assert_not_called()
                    fallback.assert_not_called()

    def test_explicit_git_c_overrides_non_git_cd_target(self):
        from codeguard.git_context import resolve_project_roots

        with tempfile.TemporaryDirectory(prefix="cg-explicit-override-") as tmp:
            base = Path(tmp).resolve()
            repo, plain = base / "repo", base / "plain"
            repo.mkdir()
            plain.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            roots = resolve_project_roots(
                f"cd {plain} && git -C {repo} commit -m x", cwd=repo)
            self.assertEqual([repo], roots)

    def test_staging_intent_uses_explicit_callers_cwd(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-staging-cwd-") as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            (repo / "new.py").write_text("print(1)\n", encoding="utf-8")
            with patch.object(Path, "cwd", return_value=repo.parent), \
                    patch.object(git_guard_application, "run_gate", return_value=([], [])) as run_gate, \
                    patch.object(git_guard_application, "check_commit_safety", return_value=[]):
                result = git_guard_application.evaluate_git_command(
                    "git add '*.py' && git commit -m x", cwd=repo, load_config=dict)
            self.assertEqual(0, result.exit_code)
            self.assertEqual(["new.py"], run_gate.call_args.kwargs["extra"])

    def test_git_root_observation_failure_is_not_fail_open(self):
        from codeguard import git_guard_application
        from git_snapshot import SnapshotError

        with patch.object(git_guard_application, "resolve_project_roots",
                          side_effect=SnapshotError("rev-parse failed")), \
                patch.object(git_guard_application, "fallback_roots") as fallback:
            result = git_guard_application.evaluate_git_command(
                "git commit -m x", cwd=Path.cwd(), load_config=dict)
        self.assertEqual(2, result.exit_code)
        self.assertIn("rev-parse failed", result.stderr)
        fallback.assert_not_called()

    def test_real_hook_blocks_explicit_non_git_target(self):
        with tempfile.TemporaryDirectory(prefix="cg-hook-target-") as tmp:
            base = Path(tmp).resolve()
            repo, plain = base / "repo", base / "plain"
            repo.mkdir()
            plain.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            payload = {"tool_name": "Bash", "tool_use_id": "explicit-target",
                       "tool_input": {"command": f"cd {plain} && git push origin main"}}
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                input=json.dumps(payload), cwd=repo, capture_output=True, text=True,
                env={**os.environ, "CODEGUARD_HOME": str(base / "state")}, timeout=15, check=False)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn(str(plain), result.stderr)
        self.assertIn("目标 UNVERIFIED", result.stderr)

    def test_no_git_repository_blocks_with_diagnostic_without_printing(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-guard-app-") as tmp:
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(git_guard_application, "resolve_project_roots", return_value=[]), \
                    patch.object(git_guard_application, "fallback_roots", return_value=[]), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                result = git_guard_application.evaluate_git_command(
                    "git push", cwd=Path(tmp), load_config=dict)
        self.assertEqual(2, result.exit_code)
        self.assertIn("未检测到任何 git 仓", result.stderr)
        self.assertEqual((), result.contexts)
        self.assertEqual("", output.getvalue() + errors.getvalue())

    def test_inline_bypass_returns_context_and_audit_without_printing(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-guard-inline-") as tmp:
            root = Path(tmp)
            output = io.StringIO()
            with patch.object(git_guard_application, "resolve_project_roots", return_value=[root]), \
                    patch.object(git_guard_application, "skip_gate_via_git_config", return_value=False), \
                    patch.object(git_guard_application, "inline_skip_gate", return_value=True), \
                    patch.object(git_guard_application, "record_skip_event") as record, \
                    contextlib.redirect_stdout(output):
                result = git_guard_application.evaluate_git_command(
                    "git -c codeguard.skipGate=true commit -m ok", cwd=root, load_config=dict)
        self.assertEqual(0, result.exit_code)
        self.assertIn("内联豁免", result.contexts[0])
        record.assert_called_once()
        self.assertEqual("", output.getvalue())

    def test_blocked_event_is_not_marked_complete_before_host_output(self):
        class BrokenOutput:
            def write(self, _text):
                raise OSError("host output unavailable")

        payload = {"tool_use_id": "event-1", "tool_input": {"command": "git commit -m x"}}

        def block(_payload):
            print("blocked")
            return 2

        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "_main", side_effect=block), \
                patch.object(pre_tool_git_guard, "completed_event", return_value=None), \
                patch.object(pre_tool_git_guard, "record_completed_event") as record, \
                patch.object(sys, "stdout", BrokenOutput()):
            self.assertEqual(2, pre_tool_git_guard.main())
        record.assert_not_called()

    def test_blocked_event_is_not_cached_if_host_flush_fails(self):
        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host flush unavailable")

        payload = {"tool_use_id": "event-2", "tool_input": {"command": "git commit -m x"}}

        def block(_payload):
            print("blocked")
            return 2

        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "_main", side_effect=block), \
                patch.object(pre_tool_git_guard, "completed_event", return_value=None), \
                patch.object(pre_tool_git_guard, "record_completed_event") as record, \
                patch.object(sys, "stdout", BrokenFlush()):
            self.assertEqual(2, pre_tool_git_guard.main())
        record.assert_not_called()

    def test_block_without_event_id_still_blocks_if_stderr_flush_fails(self):
        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host stderr flush unavailable")

        def block(_payload):
            print("blocked", file=sys.stderr)
            return 2

        payload = {"tool_input": {"command": "git push"}}
        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "_main", side_effect=block), \
                patch.object(sys, "stderr", BrokenFlush()):
            self.assertEqual(2, pre_tool_git_guard.main())

    def test_cached_block_remains_blocked_if_replay_cannot_write(self):
        class BrokenOutput:
            def write(self, _text):
                raise OSError("host output unavailable")

        payload = {"tool_use_id": "event-3", "tool_input": {"command": "git push"}}
        cached = {"code": 2, "stdout": "blocked\n", "stderr": ""}
        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "completed_event", return_value=cached), \
                patch.object(pre_tool_git_guard, "_main") as run, \
                patch.object(sys, "stdout", BrokenOutput()):
            self.assertEqual(2, pre_tool_git_guard.main())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
