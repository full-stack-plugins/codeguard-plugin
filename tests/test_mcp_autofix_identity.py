"""MCP 自动修复只能在有界、仓内、可复核的文件面执行。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from codeguard import check_application


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


if __name__ == "__main__":
    unittest.main()
