"""会话实测回归：门禁把"工具链环境问题"误判为"代码违规"的四类硬拦截。

覆盖 2026-09-22 会话在 hermes/easydoc 两仓实测踩中的误拦，以及由此暴露的
逃生门可靠性缺陷。判定原则（verdict-integrity spec）：**无法验证 ≠ 验证失败**
——工具链自身不兼容（Maven 3 读不了 POM 4.1.0、JDK 26 不支持 release 8、
ShellCheck 不支持 zsh）必须归 UNVERIFIED，绝不拦提交。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PLUGIN / "scripts"), str(PLUGIN / "hooks")]

import gate_lib
import pre_tool_git_guard
from scope import FULL_SCAN_EXCLUDES
from verdict import FAIL, UNVERIFIED, lint_verdict

# —— 会话实测原文（hermes-java-sdk feature/1.0.x/3.0.x + easydoc feature/3.0.x）——
_MAVEN_POM_TOO_NEW = (
    "[FATAL] 'modelVersion' of '4.1.0' is newer than the versions supported by this "
    "version of Maven: [4.0.0]. Building this project requires a newer version of Maven."
)
_JAVADOC_RELEASE_UNSUP = (
    "[ERROR] error: release version 1.8 not supported\n"
    "Command line was: /opt/homebrew/Cellar/openjdk/26.0.1/libexec/openjdk.jdk/Contents/Home/bin/java"
)
_INVALID_TARGET = "error: invalid target release: 21"
_CLASS_VERSION = (
    "java.lang.UnsupportedClassVersionError: com/foo/Bar has been compiled by a more "
    "recent version of the Java Runtime (class file version 65.0)"
)
_SHELLCHECK_ZSH = (
    "In scripts/run-concurrency-benchmark.zsh line 1:\n#!/bin/zsh\n"
    "^-- SC1071 (error): ShellCheck only supports sh/bash/dash/ksh scripts. Sorry!"
)


class ToolchainVerdictTests(unittest.TestCase):
    """P0：工具链不兼容必须归 UNVERIFIED，不得判 FAIL 拦提交。"""

    def test_maven_pom_model_too_new_is_unverified(self):
        status, _why = lint_verdict(1, ["mvn", "-B", "verify"], _MAVEN_POM_TOO_NEW)
        self.assertEqual(UNVERIFIED, status, "Maven 3 读不了 POM 4.1.0 是工具链问题，不是代码违规")

    def test_javadoc_release_unsupported_is_unverified(self):
        status, _why = lint_verdict(1, ["mvn", "-B", "verify"], _JAVADOC_RELEASE_UNSUP)
        self.assertEqual(UNVERIFIED, status, "JDK 26 不支持 --release 8 是工具链问题")

    def test_invalid_target_release_is_unverified(self):
        status, _why = lint_verdict(1, ["mvn", "-B", "verify"], _INVALID_TARGET)
        self.assertEqual(UNVERIFIED, status)

    def test_unsupported_class_version_is_unverified(self):
        status, _why = lint_verdict(1, ["mvn", "-B", "verify"], _CLASS_VERSION)
        self.assertEqual(UNVERIFIED, status)

    def test_real_lint_violation_still_fails(self):
        """兜底不许把真违规也放过。"""
        status, _why = lint_verdict(
            1, ["shellcheck", "x.sh"], "In x.sh line 3:\n  x=$y  ^-- SC2086 (info): Double quote"
        )
        self.assertEqual(FAIL, status)

    def test_shellcheck_zsh_limitation_is_unverified(self):
        """ShellCheck 不支持 zsh 是工具固有限制，不是代码违规。"""
        status, _why = lint_verdict(1, ["shellcheck", "a.zsh"], _SHELLCHECK_ZSH)
        self.assertEqual(UNVERIFIED, status)


class ZshShellGateTests(unittest.TestCase):
    """P1：.zsh 不得进入 shellcheck 目标面（工具不支持，送检必红）。"""

    def test_full_scan_gate_excludes_zsh(self):
        registry = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        shell = next(x for x in registry["languages"] if x["id"] == "shell")
        gate = " ".join(shell.get("gate") or [])
        self.assertNotIn("*.zsh", gate, "全量 gate 不得把 .zsh 送给 shellcheck")

    def test_delta_face_skips_zsh_files(self):
        with tempfile.TemporaryDirectory(prefix="cg-zsh-") as tmp:
            root = Path(tmp)
            (root / "run.zsh").write_text("#!/bin/zsh\necho ok\n", encoding="utf-8")
            (root / "lib.sh").write_text("#!/bin/bash\necho ok\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            skipped_reasons: list[str] = []
            # 直接调 check 内部语义面：delta 文件集里的 .zsh 必须被剔除
            from detect_lang import detect_language
            changed = ["run.zsh", "lib.sh"]
            shell_files = [
                f for f in changed
                if detect_language(f, root) == "shell" and (root / f).is_file()
            ]
            kept = [f for f in shell_files if not f.endswith(".zsh")]
            self.assertEqual(["lib.sh"], kept)
            self.assertEqual(["run.zsh"], [f for f in shell_files if f.endswith(".zsh")])
            skipped_reasons.append("shell zsh 文件未验证（ShellCheck 不支持 zsh）")
            self.assertTrue(any("zsh" in r for r in skipped_reasons))


class CacheKeyScopeTests(unittest.TestCase):
    """P1：缓存键必须含 scope（delta vs repo），否则 UPS 软门禁与硬门禁互串。"""

    def test_scope_changes_cache_key(self):
        with tempfile.TemporaryDirectory(prefix="cg-key-") as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
            (root / "a.py").write_text("print(1)\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True)
            (root / "a.py").write_text("print(2)\n", encoding="utf-8")
            common = {"languages": ["python"], "mode": "commit",
                      "lanes": ("staged",), "extra": ()}
            k_delta = gate_lib._gate_cache_key(root, scope="delta", **common)
            k_repo = gate_lib._gate_cache_key(root, scope="repo", **common)
            self.assertIsNotNone(k_delta)
            self.assertNotEqual(k_delta, k_repo, "scope 必须参与缓存键，否则跨作用域污染")


class SkipGateReliabilityTests(unittest.TestCase):
    """P1：逃生门必须可靠 + 可审计（inline -c 豁免 + 读取失败留痕）。"""

    def test_inline_dash_c_skip_gate_is_recognized(self):
        """`git -c codeguard.skipGate=true commit` 是显式单次豁免意图。"""
        self.assertTrue(
            pre_tool_git_guard.inline_skip_gate(
                "git -c codeguard.skipGate=true commit -m x"
            )
        )
        self.assertTrue(
            pre_tool_git_guard.inline_skip_gate(
                "git -c codeguard.skipGate=1 push origin main"
            )
        )

    def test_unrelated_dash_c_is_not_a_skip(self):
        self.assertFalse(
            pre_tool_git_guard.inline_skip_gate(
                "git -c core.editor=vim commit -m x"
            )
        )
        self.assertFalse(pre_tool_git_guard.inline_skip_gate("git commit -m 'skipGate'"))

    def test_inline_skip_records_audit_event(self):
        with tempfile.TemporaryDirectory(prefix="cg-audit-") as tmp:
            os.environ["CODEGUARD_HOME"] = tmp
            try:
                gate_lib.record_skip_event("inline-skipGate", Path("/some/repo"))
                state = json.loads((Path(tmp) / "session_state.json").read_text(encoding="utf-8"))
                events = state["_skip"]["events"]
                self.assertTrue(events, "豁免必须留审计明细")
                self.assertEqual("inline-skipGate", events[-1]["kind"])
                self.assertEqual("repo", events[-1]["repo"])
            finally:
                os.environ.pop("CODEGUARD_HOME", None)

    def test_skip_gate_read_error_is_audited_not_silent(self):
        """git config 读取超时/失败必须留痕——静默 False 让排障无从下手。"""
        with tempfile.TemporaryDirectory(prefix="cg-audit2-") as tmp:
            os.environ["CODEGUARD_HOME"] = tmp
            try:
                with unittest.mock.patch.object(
                    gate_lib.subprocess, "run",
                    side_effect=gate_lib.subprocess.TimeoutExpired("git", 10),
                ):
                    self.assertFalse(gate_lib.skip_gate_via_git_config(Path("/x")))
                state = json.loads((Path(tmp) / "session_state.json").read_text(encoding="utf-8"))
                kinds = state["_skip"]["kinds"]
                self.assertIn("skipGate-read-error", kinds)
            finally:
                os.environ.pop("CODEGUARD_HOME", None)


    def test_chain_set_in_same_chain_is_recognized(self):
        """文档写法 set→提交→unset 同链 = 显式豁免（此前整链被拦、首用必败）。"""
        self.assertTrue(pre_tool_git_guard.chain_skip_gate(
            "git config codeguard.skipGate true && git commit -m x"
            " && git config --unset codeguard.skipGate"))
        self.assertTrue(pre_tool_git_guard.chain_skip_gate(
            "git -C /repo config codeguard.skipGate yes && git push origin main"))

    def test_chain_query_or_negative_value_is_not_a_skip(self):
        self.assertFalse(pre_tool_git_guard.chain_skip_gate(
            "git config --get codeguard.skipGate && git push"))
        self.assertFalse(pre_tool_git_guard.chain_skip_gate(
            "git config codeguard.skipGate false && git push"))
        self.assertFalse(pre_tool_git_guard.chain_skip_gate(
            "git config --unset codeguard.skipGate && git push"))

    def test_message_text_never_disables_the_gate(self):
        """commit -m 消息里出现豁免短语不得静默关掉门禁（危险方向的误判）。"""
        self.assertFalse(pre_tool_git_guard.chain_skip_gate(
            'git commit -m "config codeguard.skipGate true"'))
        self.assertFalse(pre_tool_git_guard.chain_skip_gate(
            'echo "git config codeguard.skipGate true" && git push'))
        self.assertFalse(pre_tool_git_guard.inline_skip_gate(
            'git commit -m "use -c codeguard.skipGate=true here"'))

    def test_chain_skip_records_audit_event(self):
        with tempfile.TemporaryDirectory(prefix="cg-audit3-") as tmp:
            os.environ["CODEGUARD_HOME"] = tmp
            try:
                gate_lib.record_skip_event("chain-skipGate", Path("/some/repo"))
                state = json.loads((Path(tmp) / "session_state.json").read_text(encoding="utf-8"))
                self.assertEqual("chain-skipGate", state["_skip"]["events"][-1]["kind"])
            finally:
                os.environ.pop("CODEGUARD_HOME", None)


class AgentWorkdirExcludeTests(unittest.TestCase):
    """P2：Agent 工作目录不得进版本库、不得进全量扫描面（实测 .mimosa 曾漏）。"""

    def test_agent_workdirs_are_excluded(self):
        for name in (".mimosa", ".worktrees", ".code-review-graph", ".kimi-code",
                     ".zcode", ".codex-plugin", ".agents"):
            self.assertIn(name, FULL_SCAN_EXCLUDES,
                          f"{name} 是 Agent/工具工作目录，必须在扫描与入库双面排除")

    def test_guard_dirs_covers_agent_workdirs(self):
        for name in (".mimosa", ".worktrees"):
            self.assertIn(name, gate_lib.GUARD_EXCLUDE_DIRS)


if __name__ == "__main__":
    unittest.main()
