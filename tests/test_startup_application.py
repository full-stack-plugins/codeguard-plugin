"""SessionStart 的发现、探活与报告不依赖宿主输出或通知。"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class StartupApplicationTests(unittest.TestCase):
    def test_no_detected_languages_is_silent(self):
        from codeguard import startup_application

        with patch.object(startup_application, "detect_languages", return_value=[]):
            report = startup_application.build_startup_report(Path.cwd())
        self.assertEqual("", report.text)
        self.assertIsNone(report.notification)

    def test_missing_tool_returns_message_and_notification_without_printing(self):
        from codeguard import startup_application

        with tempfile.TemporaryDirectory(prefix="cg-start-app-") as tmp:
            project = Path(tmp)
            output = io.StringIO()
            with patch.object(startup_application, "detect_languages", return_value=["python"]), \
                    patch.object(startup_application, "detect_linter_config", return_value={}), \
                    patch.object(startup_application, "load_user_config", return_value={}), \
                    patch.object(startup_application.ToolchainProbe, "probe",
                                 return_value=(False, "检查器不可用")), \
                    patch.dict(startup_application.LANG_COMMANDS,
                               {"python": {"install_hint": "安装 ruff"}}), \
                    contextlib.redirect_stdout(output):
                report = startup_application.build_startup_report(
                    project, plugin_version="0.13.0", enabled_plugin_orgs=("one", "two"))
        self.assertEqual("", output.getvalue())
        self.assertIn("python（检查器不可用）", report.text)
        self.assertIn("双副本同时启用", report.text)
        self.assertEqual("codeguard 部分检查未生效", report.notification[0])


if __name__ == "__main__":
    unittest.main()
