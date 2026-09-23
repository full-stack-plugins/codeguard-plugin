"""PreToolUse 的 Git 决策返回结构化结果，不直接写宿主 stdout/stderr。"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]

import pre_tool_git_guard


class GitGuardApplicationTests(unittest.TestCase):
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
