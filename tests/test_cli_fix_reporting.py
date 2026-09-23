"""CLI 修复输出不得把 formatter 退出码误称为已修改文件。"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("ruff"), "real Ruff checker is required")
class CliFixReportingTests(unittest.TestCase):
    def test_noop_formatter_does_not_claim_file_was_fixed(self):
        with tempfile.TemporaryDirectory(prefix="cg-fix-report-") as temporary:
            root = Path(temporary) / "project"
            root.mkdir()

            def git(*args: str) -> None:
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

            git("init", "-q")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "CodeGuard Test")
            target = root / "sample.py"
            target.write_text("value = 1\n", encoding="utf-8")
            git("add", "sample.py")
            git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "base")
            target.write_text("value = 2\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(PLUGIN / "scripts" / "fix.py"), "--lang", "python", str(root)],
                cwd=root, env={**os.environ, "CODEGUARD_HOME": str(Path(temporary) / "state")},
                capture_output=True, text=True, timeout=30, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("执行成功", result.stdout)
            self.assertIn("文件变化未验证", result.stdout)
            self.assertNotIn("✅ fixed", result.stdout)
            self.assertEqual("value = 2\n", target.read_text(encoding="utf-8"))
