"""UserPromptSubmit 应用层返回软提醒，不直接占用 stdout 或宿主通知。"""
from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]


class PromptApplicationTests(unittest.TestCase):
    def test_hook_does_not_acknowledge_before_stdout_flush(self):
        import user_prompt_validator
        from codeguard.prompt_application import PromptResult

        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host flush unavailable")

        payload = {"user_prompt": "提交代码", "session_id": "session-1"}
        delivered = []
        with patch.object(user_prompt_validator, "read_payload", return_value=payload), \
                patch.object(user_prompt_validator, "ensure_user_path"), \
                patch.object(user_prompt_validator, "find_project_root", return_value=Path.cwd()), \
                patch.object(user_prompt_validator.prompt_application, "evaluate_prompt",
                             return_value=PromptResult("检查反馈", _on_delivered=lambda: delivered.append(True))), \
                patch.object(sys, "stdout", BrokenFlush()), self.assertRaises(OSError):
            user_prompt_validator.main()
        self.assertEqual([], delivered)

    def test_non_git_prompt_does_not_read_config_or_emit_host_output(self):
        from codeguard.prompt_application import evaluate_prompt

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = evaluate_prompt("提交代码", project_root=None, session_id=None,
                                     load_config=lambda: self.fail("非 Git 目录不应加载配置"))
        self.assertEqual("", output.getvalue())
        self.assertIn("不是 git 仓库", result.additional_context)
        self.assertIsNone(result.notification)

    def test_safety_only_violation_has_soft_context_and_no_blocking_exit(self):
        from codeguard import prompt_application

        with tempfile.TemporaryDirectory(prefix="cg-prompt-app-") as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            with patch.object(prompt_application, "skip_gate_via_git_config", return_value=False), \
                    patch.object(prompt_application, "detect_languages", return_value=[]), \
                    patch.object(prompt_application, "run_gate", return_value=([], [])), \
                    patch.object(prompt_application, "check_commit_safety",
                                 return_value=[(".env", "密钥", "git rm --cached .env")]):
                result = prompt_application.evaluate_prompt(
                    "提交代码", project_root=repo, session_id=None, load_config=dict)
        self.assertIn(".env", result.additional_context)
        self.assertIn("密钥/凭据", result.additional_context)
        self.assertIsNotNone(result.notification)

    def test_completed_event_is_recorded_only_after_host_delivery(self):
        from codeguard import prompt_application

        with tempfile.TemporaryDirectory(prefix="cg-prompt-delivery-") as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            with patch.object(prompt_application, "skip_gate_via_git_config", return_value=False), \
                    patch.object(prompt_application, "detect_languages", return_value=["python"]), \
                    patch.object(prompt_application, "check_identity", return_value="content-id"), \
                    patch.object(prompt_application, "completed_event", return_value=None), \
                    patch.object(prompt_application, "run_gate", return_value=([], [])), \
                    patch.object(prompt_application, "check_commit_safety", return_value=[]), \
                    patch.object(prompt_application, "record_completed_event") as record:
                result = prompt_application.evaluate_prompt(
                    "提交代码", project_root=repo, session_id="session-1", load_config=dict)
                record.assert_not_called()
                result.acknowledge()
                record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
