"""点前缀默认忽略硬约束测试（2026-09-23 用户指令，scan-scope-policy spec）。

锁定五件事：
1. 检查/保存/发现/全量扫描四类面默认忽略点前缀目录与文件；
2. 入库安全面不受影响（密钥照拦、点目录照常可入库，固化 0f284ee）；
3. 配置发现不受影响（requiresConfig 点文件照常判已接入）；
4. 提示词面（SessionStart 项目记忆 + AGENTS.md 硬性禁令）声明该约束；
5. 项目根本身位于点前缀父目录下不误伤。
"""
from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(PLUGIN / "hooks"))

import scope
from codeguard.discovery import detect_languages, project_uses_linter
from codeguard.path_policy import check_paths, is_dot_prefixed
from codeguard.save_application import should_skip

REGISTRY = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
SHELL_GATE = next(l for l in REGISTRY["languages"] if l["id"] == "shell")["gate"]


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


class PredicateTests(unittest.TestCase):
    def test_dot_segments_relative_to_root(self) -> None:
        self.assertTrue(is_dot_prefixed(".cursor/a.py", "."))
        self.assertTrue(is_dot_prefixed("src/.hidden/x.py", "."))
        self.assertTrue(is_dot_prefixed(".eslintrc.js", "."))
        self.assertFalse(is_dot_prefixed("src/a.py", "."))

    def test_root_and_parent_segments_exempt(self) -> None:
        # `./src/a.py` 的 `.` 段、`../x` 的 `..` 段不算命中（lstrip("./") 踩点）
        self.assertFalse(is_dot_prefixed("./src/a.py", "."))
        self.assertFalse(is_dot_prefixed("../proj/a.py", "."))

    def test_project_under_dot_parent_not_skipped(self) -> None:
        # 实测陷阱：项目根 ~/.config/proj/ 的父段点前缀不得让全项目被忽略
        tmp = Path(tempfile.mkdtemp())
        proj = tmp / ".config" / "proj"
        proj.mkdir(parents=True)
        (proj / "main.py").write_text("x=1\n")
        self.assertFalse(is_dot_prefixed(proj / "main.py", proj))
        self.assertTrue(is_dot_prefixed(proj / ".eslintrc.js", proj))


class CheckFaceTests(unittest.TestCase):
    def test_should_skip_dot_file(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        (tmp / "src").mkdir()
        (tmp / ".cursor").mkdir()
        (tmp / "src" / "a.py").write_text("x=1\n")
        (tmp / ".cursor" / "b.py").write_text("x=1\n")
        self.assertEqual(should_skip(str(tmp / ".cursor" / "b.py"), ["python"]), (True, ""))
        self.assertEqual(should_skip(str(tmp / "src" / "a.py"), ["python"]), (False, "python"))

    def test_changed_files_filters_dot_paths(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        _git(tmp, "init", "-q")
        _git(tmp, "config", "user.email", "t@t")
        _git(tmp, "config", "user.name", "t")
        (tmp / ".cursor").mkdir()
        (tmp / ".cursor" / "rules.py").write_text("x=1\n")
        (tmp / "main.py").write_text("x=1\n")
        _git(tmp, "add", "-A")
        changed = scope.changed_files(tmp, mode="commit")
        self.assertIn("main.py", changed)
        self.assertNotIn(".cursor/rules.py", changed)

    def test_detect_languages_ignores_dot_files(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        (tmp / ".eslintrc.js").write_text("module.exports = {}\n")
        (tmp / "main.py").write_text("x=1\n")
        (tmp / "src").mkdir()
        (tmp / "src" / ".hidden").mkdir()
        (tmp / "src" / ".hidden" / "x.js").write_text("x=1\n")
        langs = detect_languages(tmp)
        self.assertIn("python", langs)
        self.assertNotIn("typescript", langs)  # .eslintrc.js 与 .hidden/x.js 不计入

    def test_full_scan_find_injects_dot_exclude(self) -> None:
        once = scope.scope_cmd(SHELL_GATE, ".", full_excludes=True)
        expr = once[-1]
        self.assertIn("-not -path */.*", expr.replace(chr(39), ""))
        self.assertLess(expr.index("*/.*"), expr.index("-print0"))
        twice = scope.scope_cmd(once, ".", full_excludes=True)
        self.assertEqual(once, twice)  # 幂等

    def test_full_scan_ruff_gains_dot_excludes(self) -> None:
        out = scope.scope_cmd(["ruff", "check", "."], ".", full_excludes=True)
        pairs = list(itertools.pairwise(out))
        self.assertIn(("--exclude", ".*"), pairs)
        self.assertIn(("--exclude", "**/.*"), pairs)


class ExceptionFaceTests(unittest.TestCase):
    def test_secret_files_still_blocked(self) -> None:
        violations = check_paths([".env", "id_rsa", "x/id_ed25519"])
        self.assertEqual(len(violations), 3)

    def test_dot_dirs_remain_committable(self) -> None:
        self.assertEqual(check_paths([".agents/plugins/marketplace.json"]), [])
        self.assertEqual(check_paths([".codex-plugin/plugin.json"]), [])

    def test_requires_config_matches_dot_files(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.assertFalse(project_uses_linter({"requiresConfig": [".markdownlint-cli2.jsonc"]}, tmp))
        (tmp / ".markdownlint-cli2.jsonc").write_text("{}")
        self.assertTrue(project_uses_linter({"requiresConfig": [".markdownlint-cli2.jsonc"]}, tmp))


class PromptFaceTests(unittest.TestCase):
    def test_startup_context_states_rule(self) -> None:
        from codeguard.startup_application import build_startup_report
        tmp = Path(tempfile.mkdtemp())
        (tmp / "main.py").write_text("x=1\n")
        report = build_startup_report(tmp)
        self.assertIn("默认忽略", report.text)
        self.assertIn("入库安全检查照拦密钥模式", report.text)
        self.assertIn("配置发现照常匹配点文件", report.text)

    def test_agents_md_states_rule(self) -> None:
        text = (PLUGIN / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("默认忽略", text)
        self.assertIn("硬性禁令", text)
        self.assertIn("requiresConfig", text)


if __name__ == "__main__":
    unittest.main()
