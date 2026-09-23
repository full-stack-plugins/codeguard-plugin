"""Stop 应用服务只返回结果，宿主适配器负责 stdout 与 fail-open 协议。"""
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
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))


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

    def test_stop_output_failure_keeps_statistics_for_retry(self):
        import stop_summary

        class BrokenOutput:
            def write(self, _value):
                raise OSError("host output unavailable")

        self.home.mkdir()
        state = self.home / "session_state.json"
        state.write_text('{"python":{"total":2,"passed":1,"failed":1,"auto_fixed":0}}',
                         encoding="utf-8")
        with patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            with patch.object(stop_summary.sys, "stdout", BrokenOutput()), self.assertRaises(OSError):
                stop_summary.main({})
            self.assertEqual(2, json.loads(state.read_text())["python"]["total"])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, stop_summary.main({}))
            self.assertIn("共 2 次检查", output.getvalue())
            self.assertFalse(state.exists())

    def test_stop_flush_failure_keeps_statistics_for_retry(self):
        import stop_summary

        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host flush unavailable")

        self.home.mkdir()
        state = self.home / "session_state.json"
        state.write_text('{"python":{"total":1,"passed":1,"failed":0,"auto_fixed":0}}',
                         encoding="utf-8")
        with patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            with patch.object(stop_summary.sys, "stdout", BrokenFlush()), self.assertRaises(OSError):
                stop_summary.main({})
            self.assertEqual(1, json.loads(state.read_text())["python"]["total"])

    def test_concurrent_write_during_delivery_is_not_deleted(self):
        from codeguard.hook_state import bump_state
        from codeguard.session_application import prepare_summary

        self.home.mkdir()
        state = self.home / "session_state.json"
        state.write_text('{"python":{"total":1,"passed":1,"failed":0,"auto_fixed":0}}',
                         encoding="utf-8")
        with patch.dict(os.environ, {"CODEGUARD_HOME": str(self.home)}):
            prepared = prepare_summary(ROOT / ".session_state.json", self.repo)
            self.assertIn("共 1 次检查", prepared.lines[0])
            bump_state(state, "python", True)
            prepared.acknowledge()
            self.assertEqual(2, json.loads(state.read_text())["python"]["total"])
            retry = prepare_summary(ROOT / ".session_state.json", self.repo)
            self.assertIn("共 2 次检查", retry.lines[0])
            retry.acknowledge()
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
