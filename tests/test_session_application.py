"""Stop 应用服务只返回结果，宿主适配器负责 stdout 与 fail-open 协议。"""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class SessionApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-session-app-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
        self.home = self.root / "state"

    def test_consume_summary_returns_lines_without_host_output_and_drains_once(self):
        from codeguard.session_application import consume_summary

        self.home.mkdir()
        (self.home / "session_state.json").write_text(
            '{"python":{"total":2,"passed":1,"failed":1,"auto_fixed":0}}', encoding="utf-8")
        output = io.StringIO()
        with patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}), \
                contextlib.redirect_stdout(output):
            first = consume_summary(ROOT / ".session_state.json", self.repo)
            second = consume_summary(ROOT / ".session_state.json", self.repo)
        self.assertEqual("", output.getvalue())
        self.assertEqual(1, len(first))
        self.assertIn("共 2 次检查", first[0])
        self.assertIn("无 linter 记录", second[0])

    def test_skipgate_reminder_is_a_separate_result_line(self):
        from codeguard.session_application import consume_summary

        subprocess.run(["git", "config", "codeguard.skipGate", "true"], cwd=self.repo,
                       check=True, capture_output=True)
        with patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            lines = consume_summary(ROOT / ".session_state.json", self.repo)
        self.assertEqual(2, len(lines))
        self.assertIn("仍为 true", lines[1])


if __name__ == "__main__":
    unittest.main()
