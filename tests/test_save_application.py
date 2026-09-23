"""PostToolUse 应用层负责保存检查，宿主适配器负责 JSON/通知。"""
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


class SaveApplicationTests(unittest.TestCase):
    def test_hook_does_not_acknowledge_before_stdout_flush(self):
        import post_tool_lint
        from codeguard.save_application import SaveResult

        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host flush unavailable")

        delivered = []
        with patch.object(post_tool_lint, "ensure_user_path"), \
                patch.object(post_tool_lint, "find_project_root", return_value=Path.cwd()), \
                patch.object(post_tool_lint.save_application, "evaluate_save",
                             return_value=SaveResult("检查反馈", _on_delivered=lambda: delivered.append(True))), \
                patch.object(sys, "stdout", BrokenFlush()), self.assertRaises(OSError):
            post_tool_lint._main({"file_path": "main.py"})
        self.assertEqual([], delivered)

    def test_project_only_checker_reports_unverified_without_running(self):
        from codeguard import save_application

        with tempfile.TemporaryDirectory(prefix="cg-save-app-") as tmp:
            root = Path(tmp)
            file_path = root / "main.py"
            file_path.write_text("print(1)\n", encoding="utf-8")
            output = io.StringIO()
            with patch.object(save_application, "detect_language", return_value="python"), \
                    patch.dict(save_application.LANG_COMMANDS,
                               {"python": {"lint": ["python", "-V"], "append_files": False}}), \
                    patch.object(save_application, "run") as run, \
                    contextlib.redirect_stdout(output):
                result = save_application.evaluate_save(str(file_path), root, {})
        self.assertEqual("", output.getvalue())
        self.assertIn("项目级检查", result.additional_context)
        run.assert_not_called()

    def test_unverified_lint_never_auto_fixes_or_records_completion(self):
        from codeguard import save_application

        with tempfile.TemporaryDirectory(prefix="cg-save-unknown-") as tmp:
            root = Path(tmp)
            file_path = root / "main.py"
            file_path.write_text("print(1)\n", encoding="utf-8")
            with patch.object(save_application, "detect_language", return_value="python"), \
                    patch.dict(save_application.LANG_COMMANDS,
                               {"python": {"lint": ["ruff", "check", "{file}"],
                                           "format": ["ruff", "format", "{file}"]}}), \
                    patch.object(save_application, "project_uses_linter", return_value=True), \
                    patch.object(save_application, "check_identity", return_value=None), \
                    patch.object(save_application, "run", return_value=(2, "", "config invalid")) as run, \
                    patch.object(save_application, "bump_state") as bump:
                result = save_application.evaluate_save(str(file_path), root, {"auto_fix_on_save": True})
                result.acknowledge()
        self.assertIn("UNVERIFIED", result.additional_context)
        self.assertEqual(1, run.call_count)
        bump.assert_not_called()

    def test_passed_check_records_statistics_only_after_delivery(self):
        from codeguard import save_application

        with tempfile.TemporaryDirectory(prefix="cg-save-delivery-") as tmp:
            root = Path(tmp)
            file_path = root / "main.py"
            file_path.write_text("print(1)\n", encoding="utf-8")
            with patch.object(save_application, "detect_language", return_value="python"), \
                    patch.dict(save_application.LANG_COMMANDS,
                               {"python": {"lint": ["ruff", "check", "{file}"]}}), \
                    patch.object(save_application, "project_uses_linter", return_value=True), \
                    patch.object(save_application, "check_identity", return_value=None), \
                    patch.object(save_application, "run", return_value=(0, "", "")), \
                    patch.object(save_application, "bump_state") as bump:
                result = save_application.evaluate_save(str(file_path), root, {})
                bump.assert_not_called()
                result.acknowledge()
                bump.assert_called_once_with("python", passed=True, auto_fixed=False)


if __name__ == "__main__":
    unittest.main()
