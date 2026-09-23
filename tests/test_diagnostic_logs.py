"""原始诊断日志必须保留内容，但不得借文件链接扩大写入面。"""
from __future__ import annotations

import hashlib
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from codeguard import reporting, save_application, storage
from codeguard.language_check import run_check
from codeguard.registry import LANG_COMMANDS


class DiagnosticLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-log-safety-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = (self.base / "project").resolve()
        self.root.mkdir()

    def _failed_check(self, log_dir: Path) -> dict:
        command = [sys.executable, "-c", "print('private evidence'); raise SystemExit(1)"]
        with patch.dict(LANG_COMMANDS, {"python": {"lint": command, "gate": command}}):
            return run_check(["python"], self.root, log_dir=log_dir)[0]

    @unittest.skipIf(os.name == "nt", "POSIX file modes and symlinks required")
    def test_project_failure_log_is_private_with_permissive_umask(self):
        previous = os.umask(0o022)
        try:
            result = self._failed_check(self.root / "out")
        finally:
            os.umask(previous)
        log_path = Path(result["log_path"])
        self.assertEqual(0o600, stat.S_IMODE(log_path.stat().st_mode))
        self.assertIn("private evidence", log_path.read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "POSIX symlinks required")
    def test_project_failure_log_replaces_symlink_without_overwriting_target(self):
        target = self.base / "do-not-overwrite.txt"
        target.write_text("original", encoding="utf-8")
        log_dir = self.root / "out"
        log_dir.mkdir()
        log_path = log_dir / ".codeguard-last.log"
        log_path.symlink_to(target)

        result = self._failed_check(log_dir)

        self.assertEqual("original", target.read_text(encoding="utf-8"))
        self.assertEqual(log_path, Path(result["log_path"]))
        self.assertFalse(log_path.is_symlink())
        self.assertIn("private evidence", log_path.read_text(encoding="utf-8"))

    @unittest.skipIf(os.name == "nt", "POSIX symlinks required")
    def test_symlinked_output_directory_does_not_receive_project_log(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.root / "out").symlink_to(outside, target_is_directory=True)

        result = self._failed_check(self.root / "out")

        self.assertNotIn("log_path", result)
        self.assertFalse(result["passed"])
        self.assertFalse((outside / ".codeguard-last.log").exists())

    def test_unavailable_output_directory_preserves_check_verdict(self):
        (self.root / "out").write_text("occupied", encoding="utf-8")

        result = self._failed_check(self.root / "out")

        self.assertNotIn("log_path", result)
        self.assertFalse(result["passed"])
        self.assertEqual("occupied", (self.root / "out").read_text(encoding="utf-8"))

    def test_failed_atomic_swap_preserves_previous_log_and_verdict(self):
        log_dir = self.root / "out"
        log_dir.mkdir()
        log_path = log_dir / ".codeguard-last.log"
        log_path.write_text("previous evidence", encoding="utf-8")

        with patch.object(storage.os, "replace", side_effect=OSError("swap failed")):
            result = self._failed_check(log_dir)

        self.assertNotIn("log_path", result)
        self.assertFalse(result["passed"])
        self.assertEqual("previous evidence", log_path.read_text(encoding="utf-8"))
        self.assertEqual([], list(log_dir.glob(".codeguard-last.log.*.tmp")))

    @unittest.skipIf(os.name == "nt", "POSIX file modes and symlinks required")
    def test_gate_truncated_log_replaces_symlink_privately(self):
        target = self.base / "do-not-overwrite.txt"
        target.write_text("original", encoding="utf-8")
        with patch("tempfile.gettempdir", return_value=str(self.base)):
            log_path = reporting._log_path(self.root, "python")
            log_path.symlink_to(target)
            detail = reporting._truncate_detail("private evidence\n" * 70, self.root, "python")

        self.assertEqual("original", target.read_text(encoding="utf-8"))
        self.assertFalse(log_path.is_symlink())
        self.assertEqual(0o600, stat.S_IMODE(log_path.stat().st_mode))
        self.assertIn("private evidence", log_path.read_text(encoding="utf-8"))
        self.assertIn(str(log_path), detail)

    def _save_log_path(self, directory: Path) -> Path:
        key = hashlib.sha1(str(self.root / "main.py").encode()).hexdigest()[:12]
        return directory / f"codeguard-post-python-{key}.log"

    @unittest.skipIf(os.name == "nt", "POSIX file modes required")
    def test_save_truncated_log_is_private_with_permissive_umask(self):
        previous = os.umask(0o022)
        try:
            with patch("tempfile.gettempdir", return_value=str(self.base)):
                context, _ = save_application._failure_context(
                    str(self.root / "main.py"), "python", {}, "private evidence\n" * 70, "")
        finally:
            os.umask(previous)
        log_path = self._save_log_path(self.base)
        self.assertEqual(0o600, stat.S_IMODE(log_path.stat().st_mode))
        self.assertIn("private evidence", log_path.read_text(encoding="utf-8"))
        self.assertIn(str(log_path), context)

    @unittest.skipIf(os.name == "nt", "POSIX symlinks required")
    def test_save_truncated_log_replaces_symlink_without_overwriting_target(self):
        target = self.base / "do-not-overwrite.txt"
        target.write_text("original", encoding="utf-8")
        log_path = self._save_log_path(self.base)
        log_path.symlink_to(target)
        with patch("tempfile.gettempdir", return_value=str(self.base)):
            context, _ = save_application._failure_context(
                str(self.root / "main.py"), "python", {}, "private evidence\n" * 70, "")
        self.assertEqual("original", target.read_text(encoding="utf-8"))
        self.assertFalse(log_path.is_symlink())
        self.assertEqual(0o600, stat.S_IMODE(log_path.stat().st_mode))
        self.assertIn(str(log_path), context)

    @unittest.skipIf(os.name == "nt", "POSIX symlinks required")
    def test_save_truncated_log_refuses_symlinked_directory(self):
        outside = self.base / "outside"
        outside.mkdir()
        linked = self.base / "linked"
        linked.symlink_to(outside, target_is_directory=True)
        with patch("tempfile.gettempdir", return_value=str(linked)):
            context, _ = save_application._failure_context(
                str(self.root / "main.py"), "python", {}, "private evidence\n" * 70, "")
        self.assertNotIn("完整输出:", context)
        self.assertIn("怎么修", context)
        self.assertFalse(self._save_log_path(outside).exists())

    def test_save_truncated_log_swap_failure_keeps_previous_log_and_feedback(self):
        log_path = self._save_log_path(self.base)
        log_path.write_text("previous evidence", encoding="utf-8")
        with (patch("tempfile.gettempdir", return_value=str(self.base)),
              patch.object(storage.os, "replace", side_effect=OSError("swap failed"))):
            context, _ = save_application._failure_context(
                str(self.root / "main.py"), "python", {}, "private evidence\n" * 70, "")
        self.assertNotIn("完整输出:", context)
        self.assertIn("怎么修", context)
        self.assertEqual("previous evidence", log_path.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.base.glob(log_path.name + ".*.tmp")))

    def test_save_application_keeps_failure_feedback_and_private_log_path(self):
        file_path = self.root / "main.py"
        file_path.write_text("print(1)\n", encoding="utf-8")
        with (patch("tempfile.gettempdir", return_value=str(self.base)),
              patch.object(save_application, "detect_language", return_value="python"),
              patch.object(save_application, "project_uses_linter", return_value=True),
              patch.object(save_application, "check_identity", return_value=None),
              patch.object(save_application, "run", return_value=(1, "private evidence\n" * 70, "")),
              patch.dict(save_application.LANG_COMMANDS,
                         {"python": {"lint": ["ruff", "check", "{file}"], "append_files": True}})):
            result = save_application.evaluate_save(str(file_path), self.root,
                                                    {"auto_fix_on_save": False})
        log_path = self._save_log_path(self.base)
        self.assertIn("检查未通过", result.additional_context)
        self.assertIn(str(log_path), result.additional_context)
        self.assertIn("private evidence", log_path.read_text(encoding="utf-8"))
        if os.name == "posix":
            self.assertEqual(0o600, stat.S_IMODE(log_path.stat().st_mode))


if __name__ == "__main__":
    unittest.main()
