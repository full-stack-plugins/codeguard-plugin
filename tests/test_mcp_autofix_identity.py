"""MCP 自动修复只能在有界、仓内、可复核的文件面执行。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from codeguard import check_application, language_check


class McpAutoFixIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-autofix-identity-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.root = base / "repo"
        self.root.mkdir()
        self.external = base / "external"
        self.external.mkdir()

    def test_parent_symlink_escape_is_rejected_before_read_or_fix(self):
        (self.external / "secret.py").write_text("SECRET_FIXTURE\n", encoding="utf-8")
        (self.root / "linked").symlink_to(self.external, target_is_directory=True)
        with (patch.object(check_application, "changed_files", return_value=["linked/secret.py"]),
              patch.object(check_application, "run_fix") as fix,
              patch.object(check_application, "run_check") as check,
              patch.object(Path, "read_bytes", side_effect=AssertionError("read outside repository"))):
            payload = check_application.mcp_tool_payload(
                "auto_fix", {"path": str(self.root), "languages": ["python"]}, self.root)
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        self.assertNotIn("SECRET_FIXTURE", str(payload))
        fix.assert_not_called()
        check.assert_not_called()

    def test_oversize_input_does_not_start_formatter(self):
        (self.root / "large.py").write_bytes(b"0123456789abcdef")
        with (patch.object(check_application, "changed_files", return_value=["large.py"]),
              patch.object(check_application, "MAX_BYTES", 8, create=True),
              patch.object(check_application, "run_fix") as fix,
              patch.object(check_application, "run_check") as check):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        fix.assert_not_called()
        check.assert_not_called()

    def test_symlink_loop_is_unverified_without_fix(self):
        (self.root / "loop").symlink_to("loop", target_is_directory=True)
        with (patch.object(check_application, "changed_files", return_value=["loop/file.py"]),
              patch.object(check_application, "run_fix") as fix):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        fix.assert_not_called()

    def test_post_fix_identity_failure_preserves_execution_but_not_fixed_claim(self):
        (self.root / "changed.py").write_text("value = 1\n", encoding="utf-8")
        observed = iter([("before", 10), ValueError("file changed during read")])

        def observe(_path, _budget):
            value = next(observed)
            if isinstance(value, Exception):
                raise value
            return value

        checks = [{"language": "python", "passed": True, "status": "PASS", "exit_code": 0}]
        repairs = [{"language": "python", "fixed": True, "exit_code": 0}]
        with (patch.object(check_application, "changed_files", return_value=["changed.py"]),
              patch.object(check_application, "file_content", side_effect=observe, create=True),
              patch.object(check_application, "run_fix", return_value=repairs) as fix,
              patch.object(check_application, "run_check", return_value=checks) as check):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        self.assertEqual(True, payload["fix_results"][0]["fixed"])
        self.assertEqual("PASS", payload["check"][0]["status"])
        fix.assert_called_once()
        check.assert_called_once()

    def test_checker_side_effect_does_not_count_as_formatter_fix(self):
        target = self.root / "changed.py"
        target.write_text("value = 1\n", encoding="utf-8")

        def check_mutates(*_args, **_kwargs):
            target.write_text("value = 2\n", encoding="utf-8")
            return [{"language": "python", "passed": True, "status": "PASS", "exit_code": 0}]

        with (patch.object(check_application, "changed_files", return_value=["changed.py"]),
              patch.object(check_application, "run_fix", return_value=[
                  {"language": "python", "fixed": True, "exit_code": 0}]),
              patch.object(check_application, "run_check", side_effect=check_mutates)):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        self.assertEqual("PASS", payload["check"][0]["status"])

    def test_formatter_change_survives_read_only_checker(self):
        target = self.root / "changed.py"
        target.write_text("value = 1\n", encoding="utf-8")

        def formatter(*_args, **_kwargs):
            target.write_text("value = 2\n", encoding="utf-8")
            return [{"language": "python", "fixed": True, "exit_code": 0}]

        with (patch.object(check_application, "changed_files", return_value=["changed.py"]),
              patch.object(check_application, "run_fix", side_effect=formatter),
              patch.object(check_application, "run_check", return_value=[
                  {"language": "python", "passed": True, "status": "PASS", "exit_code": 0}])):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertTrue(payload["fixed"])
        self.assertNotIn("status", payload)

    def test_real_checker_process_mutation_is_not_verified_as_repair(self):
        target = self.root / "changed.py"
        target.write_text("value = 1\n", encoding="utf-8")
        checker = self.root / "checker.py"
        checker.write_text(
            "from pathlib import Path\nPath('changed.py').write_text('value = 2\\n')\n",
            encoding="utf-8",
        )
        command = {"lint": [sys.executable, str(checker)], "append_files": True}
        with (patch.object(check_application, "changed_files", return_value=["changed.py"]),
              patch.object(check_application, "run_fix", return_value=[
                  {"language": "python", "fixed": False, "exit_code": 0}]),
              patch.dict(language_check.LANG_COMMANDS, {"python": command}),
              patch.object(language_check, "project_uses_linter", return_value=True)):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        self.assertEqual("PASS", payload["check"][0]["status"])
        self.assertEqual("value = 2\n", target.read_text(encoding="utf-8"))

    def test_checker_reverts_formatter_change_is_unverified(self):
        target = self.root / "changed.py"
        target.write_text("value = 1\n", encoding="utf-8")

        def formatter(*_args, **_kwargs):
            target.write_text("value = 2\n", encoding="utf-8")
            return [{"language": "python", "fixed": True, "exit_code": 0}]

        def check_reverts(*_args, **_kwargs):
            target.write_text("value = 1\n", encoding="utf-8")
            return [{"language": "python", "passed": True, "status": "PASS", "exit_code": 0}]

        with (patch.object(check_application, "changed_files", return_value=["changed.py"]),
              patch.object(check_application, "run_fix", side_effect=formatter),
              patch.object(check_application, "run_check", side_effect=check_reverts)):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        self.assertEqual("value = 1\n", target.read_text(encoding="utf-8"))

    def test_post_check_identity_failure_preserves_execution(self):
        (self.root / "changed.py").write_text("value = 1\n", encoding="utf-8")
        observed = iter([("before", 10), ("after-fix", 10), ValueError("file changed")])

        def observe(_path, _budget):
            value = next(observed)
            if isinstance(value, Exception):
                raise value
            return value

        with (patch.object(check_application, "changed_files", return_value=["changed.py"]),
              patch.object(check_application, "file_content", side_effect=observe),
              patch.object(check_application, "run_fix", return_value=[
                  {"language": "python", "fixed": True, "exit_code": 0}]),
              patch.object(check_application, "run_check", return_value=[
                  {"language": "python", "passed": True, "status": "PASS", "exit_code": 0}])):
            payload = check_application.auto_fix(self.root, ["python"])
        self.assertEqual("UNVERIFIED", payload["status"])
        self.assertFalse(payload["fixed"])
        self.assertEqual("PASS", payload["check"][0]["status"])


if __name__ == "__main__":
    unittest.main()
