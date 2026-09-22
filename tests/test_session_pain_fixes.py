"""2026-09-23 opencli/codex 双 SDK 发布会话实测痛点的修复回归。

锚定四个实测坑：
- POM 4.1.0 + mvnw 仓库：gate_lib 的 mvnw 感知读取的 `executable` 键
  生产者（java_project）从不产出 → 感知死代码，门禁退回裸 mvn 必失败；
- 门禁目标仓库不显式：cwd 漂移后 AI 以为改的是 A 仓，实际门禁扫的是 B 仓；
- ruff [*] 可自动修复项藏在长输出尾部，AI 修完才发现有捷径；
- 仓库级 skipGate 对该克隆所有分支生效且跨会话残留，提示里没有作用域警告。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "hooks"))
sys.path.insert(0, str(PLUGIN / "scripts"))

import gate_lib
import scope
from java_project import analyze


class JavaExecutableContractTest(unittest.TestCase):
    """生产者-消费者契约：java_project 必须产出顶层 executable 键。

    68c8a37 曾让 mvnw 感知成为死代码——消费者读的键生产者从不写，
    两侧各自的测试都绿，合在一起门禁照旧退回裸 mvn（实测）。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "pom.xml").write_text(
            '<project xmlns="http://maven.apache.org/POM/4.1.0">'
            "<modelVersion>4.1.0</modelVersion>"
            "<groupId>test</groupId><artifactId>test</artifactId>"
            "<version>1.0</version>"
            "<packaging>jar</packaging></project>", encoding="utf-8")

    def test_executable_wrapper_present_and_executable(self):
        mvnw = self.root / "mvnw"
        mvnw.write_text("#!/bin/sh\nexit 0\n")
        mvnw.chmod(0o755)
        plan = analyze(str(self.root))
        self.assertEqual(plan["status"], "PLANNED",
                         "reasons=" + "; ".join(plan["reasons"]))
        self.assertEqual(plan.get("executable"), "./mvnw",
                         "生产者必须产出顶层 executable 键；reasons="
                         + "; ".join(plan["reasons"]))

    def test_executable_wrapper_missing_falls_back_to_mvn(self):
        plan = analyze(str(self.root))
        self.assertEqual(plan.get("executable"), "mvn")

    def test_executable_wrapper_not_executable_is_unverified(self):
        mvnw = self.root / "mvnw"
        mvnw.write_text("#!/bin/sh\nexit 0\n")
        mvnw.chmod(0o644)
        plan = analyze(str(self.root))
        self.assertEqual(plan["status"], "UNVERIFIED")
        self.assertTrue(any("不可执行" in r for r in plan["reasons"]))


class JavaExecutableFromPlanTest(unittest.TestCase):
    """消费者纯函数：两条来源优先级 + 非包装器不参与。"""

    def test_prefers_top_level_key(self):
        plan = {"executable": "./mvnw",
                "commands": [{"argv": ["mvn", "verify"]}]}
        self.assertEqual(gate_lib._java_executable_from_plan(plan), "./mvnw")

    def test_falls_back_to_wrapper_in_command_argv(self):
        plan = {"commands": [{"argv": ["./mvnw", "-B", "verify"]}]}
        self.assertEqual(gate_lib._java_executable_from_plan(plan), "./mvnw")

    def test_ignores_non_wrapper_command_heads(self):
        plan = {"commands": [{"argv": ["mvn", "verify"]}]}
        self.assertIsNone(gate_lib._java_executable_from_plan(plan))

    def test_empty_plan_returns_none(self):
        self.assertIsNone(gate_lib._java_executable_from_plan({}))


class DirectiveRepoLabelTest(unittest.TestCase):
    """目标仓库首行：cwd 漂移扫到非目标仓时，AI 第一眼就能发现。"""

    def test_directive_names_target_repo_when_root_given(self):
        report = gate_lib.gate_directive(
            [("shell", "EXE001 detail", "fix cmd", "hint")],
            project_root="/tmp/some-repo")
        self.assertIn("本次门禁目标仓库", report)
        self.assertIn("/tmp/some-repo", report)

    def test_directive_without_root_omits_label(self):
        report = gate_lib.gate_directive(
            [("shell", "detail", "fix", "hint")])
        self.assertNotIn("本次门禁目标仓库", report)

    def test_directive_warns_clone_wide_scope_of_repo_level_skip(self):
        report = gate_lib.gate_directive(
            [("shell", "detail", "fix", "hint")],
            project_root="/tmp/some-repo")
        self.assertIn("所有分支", report)


class PythonFixableHintTest(unittest.TestCase):
    """ruff [*] 可自动修复项：提示必须显式给出 ruff check --fix。"""

    def test_fixable_hint_appended_for_python(self):
        blocks = gate_lib._failure_detail_blocks(
            [("python", "UP009 [*] UTF-8 encoding declaration is unnecessary",
              "remove comment", "hint")])
        joined = "\n".join(blocks)
        self.assertIn("ruff check --fix", joined)

    def test_no_fixable_hint_for_shell(self):
        blocks = gate_lib._failure_detail_blocks(
            [("shell", "SC2086 detail", "quote it", "hint")])
        self.assertNotIn("ruff check --fix", "\n".join(blocks))


class RuleSummaryTest(unittest.TestCase):
    """规则聚合计数：whack-a-mole 的治理——AI 一次看到问题全集。"""

    def test_aggregates_rule_codes(self):
        full = ("scripts/x.py:1:1 EXE001 Shebang\n"
                "scripts/y.py:2:1 EXE001 Shebang\n"
                "scripts/z.py:28:27 DTZ011 date.today() used")
        self.assertEqual(
            gate_lib._rule_summary(full),
            "规则汇总: DTZ011×1 EXE001×2")

    def test_empty_for_non_linter_output(self):
        self.assertEqual(gate_lib._rule_summary("plain text\nno codes"), "")


class ScopeChildGitRepoTest(unittest.TestCase):
    """非 git 根（会话工作区）的全量扫描：子 git 仓必须排除。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "sub-repo").mkdir()
        (self.root / "sub-repo" / ".git").mkdir()
        (self.root / "loose.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    def test_child_git_repos_detected(self):
        self.assertFalse(scope.is_git_repo(self.root))
        self.assertEqual(scope.child_git_repo_names(self.root), ["sub-repo"])

    def test_find_gate_excludes_child_repos(self):
        cmd = ["bash", "-c",
               ("find . \\( -name '*.sh' \\) -type f " "-not -path '*/node_modules/*' -print0 | " "xargs -0 -r shellcheck --severity=warning")]
        out = scope.scope_cmd(cmd, str(self.root), full_excludes=True)
        joined = " ".join(out)
        self.assertIn("-not -path '*/sub-repo/*'", joined)
        self.assertIn("-not -path '*/target/*'", joined)

    def test_git_repo_root_gets_no_child_excludes(self):
        (self.root / ".git").mkdir()
        cmd = ["bash", "-c",
               "find . -name '*.sh' -type f -print0 | xargs -0 -r true"]
        out = scope.scope_cmd(cmd, str(self.root), full_excludes=True)
        self.assertNotIn("-not -path '*/sub-repo/*'", " ".join(out))


if __name__ == "__main__":
    unittest.main()
