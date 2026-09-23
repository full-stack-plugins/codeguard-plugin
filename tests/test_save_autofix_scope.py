"""save 面 auto-fix 范围锁定（2026-09-23 save-scope-lock-and-doc-parity）。

P0「全仓 format 静默重写无关文件」的机制面已修（scoped_plan + touched_others），
本模块把三态行为钉死防回退：scan token 收束单文件 / {file} 替换 / 裸命令追加，
以及越界触碰的显式告警。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

from codeguard.planning import scoped_plan


class SaveScopePlanTests(unittest.TestCase):
    def test_scan_token_collapses_to_edited_file(self) -> None:
        plan = scoped_plan(["ruff", "check", ".", "--fix"], Path("."),
                           scope="save", files=["src/a.py"])
        argv = list(plan.commands[0].argv)
        self.assertIn("src/a.py", argv)
        self.assertNotIn(".", argv)

    def test_file_placeholder_substituted(self) -> None:
        plan = scoped_plan(["clang-format", "-i", "{file}"], Path("."),
                           scope="save", files=["src/a.c"])
        argv = list(plan.commands[0].argv)
        self.assertIn("src/a.c", argv)
        self.assertNotIn("{file}", argv)

    def test_bare_command_appends_file(self) -> None:
        plan = scoped_plan(["cargo", "fmt"], Path("."), scope="save", files=["src/a.rs"])
        argv = list(plan.commands[0].argv)
        self.assertEqual(argv[-1], "src/a.rs")


class TouchedOthersTests(unittest.TestCase):
    def test_formatter_touching_other_file_is_reported(self) -> None:
        from codeguard.save_application import evaluate_save

        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True, check=False)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "--allow-empty", "-m", "init"],
                       cwd=root, capture_output=True, check=False)
        target = root / "a.py"
        target.write_text("x = 1\n", encoding="utf-8")
        # lint 先失败（FIXED_MARKER 缺席）→ format 修复并越界建 OTHER_MARKER → 复检通过
        with patch.dict("codeguard.save_application.LANG_COMMANDS", {
            "python": {
                "lint": ["sh", "-c", "test -f FIXED_MARKER"],
                "format": ["sh", "-c", "touch FIXED_MARKER OTHER_MARKER"],
                "probe": ["true"],
            }
        }, clear=False), patch("codeguard.save_application.detect_language",
                               return_value="python"):
            result = evaluate_save(str(target), root, {"auto_fix_on_save": True})
        self.assertIn("本文件之外", result.additional_context)
        self.assertTrue((root / "OTHER_MARKER").exists())


if __name__ == "__main__":
    unittest.main()
