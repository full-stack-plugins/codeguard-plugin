"""第二批会话实测回归：误拦治理深化 + 可审计性（2026-09-22）。

主题：判定不许"一刀切掩盖"——SC1071 剥离后重判同批真问题；豁免与门禁决策
必须可回溯（结构化日志）；存量问题的豁免**必须有基线证据**（同工具同命令跑
改动前内容），无证据绝不豁免（verdict-integrity 既有原则，本批首次落地）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PLUGIN / "scripts"), str(PLUGIN / "hooks")]

import gate_lib
import pre_tool_git_guard
import scope
from verdict import FAIL, UNVERIFIED, finding_signatures, lint_verdict


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          check=True, text=True).stdout


class GitRepoCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="cg-b2-")
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name) / "repo"
        self.root.mkdir()
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "t@t")
        _git(self.root, "config", "user.name", "t")

    def put(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p


class DialectMaskingTests(unittest.TestCase):
    """SC1071 不得掩盖同批其余诊断；剥离后无剩余才算 UNVERIFIED。"""

    def test_sc1071_plus_real_issue_judges_on_real_issue(self):
        output = (
            "In run.zsh line 1:\n#!/bin/zsh\n^-- SC1071 (error): ShellCheck only supports sh\n\n"
            "In lib.sh line 3:\n  x=$y  ^-- SC2086 (info): Double quote to prevent globbing\n"
        )
        status, _why = lint_verdict(1, ["shellcheck", "run.zsh", "lib.sh"], output)
        self.assertEqual(FAIL, status, "剥离 SC1071 后 lib.sh 的真问题必须仍判 FAIL")

    def test_sc1071_alone_is_unverified(self):
        output = "In run.zsh line 1:\n#!/bin/zsh\n^-- SC1071 (error): ShellCheck only supports sh\n"
        status, _why = lint_verdict(1, ["shellcheck", "run.zsh"], output)
        self.assertEqual(UNVERIFIED, status)

    def test_finding_signatures_extract_codes(self):
        sigs = finding_signatures("a.py:1:1: F401 unused\nIn b.sh line 2:\n^-- SC2086 (info): quote")
        self.assertIn("F401", sigs)
        self.assertIn("SC2086", sigs)

    def test_finding_signatures_normalize_without_codes(self):
        sigs = finding_signatures("old.py:1:1: something went wrong here")
        self.assertTrue(sigs, "无规则码时也要产出可比较的签名")
        self.assertEqual(sigs, finding_signatures("other.py:9:3: something went wrong here"),
                         "路径与行号变化不影响同一发现的签名")


class BaselineStalenessTests(GitRepoCase):
    """存量问题豁免必须有基线证据：同工具跑 HEAD 版本得到相同发现才豁免。

    用假 linter（确定性输出 CODE1）而非真 shellcheck——SC2086 是 info 级，
    会被 --severity=warning 过滤掉，基线输出为空就永远比不出存量（实测踩过）。
    """

    def checker(self):
        return [sys.executable, "-c",
                ("import sys,pathlib;t=pathlib.Path(sys.argv[1]).read_text();"
                 "sys.stdout.write('CODE1 bad\\n') if 'BAD' in t else None"),
                "{file}"]

    def test_pre_existing_finding_is_stale_with_baseline(self):
        self.put("lib.sh", "#!/bin/bash\nBAD\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        self.put("lib.sh", "#!/bin/bash\nBAD\necho new\n")   # 改动未触碰问题行
        stale = gate_lib.baseline_stale_finding(
            self.root, "lib.sh", self.checker(), "CODE1 bad",
        )
        self.assertEqual(stale, "存量问题（基线同命令同工具已存在）",
                         "HEAD 版本就有同一发现 → 存量，豁免")

    def test_new_finding_is_not_stale(self):
        self.put("lib.sh", "#!/bin/bash\necho ok\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        self.put("lib.sh", "#!/bin/bash\necho ok\nBAD\n")   # 本次新增问题
        stale = gate_lib.baseline_stale_finding(
            self.root, "lib.sh", self.checker(), "CODE1 bad",
        )
        self.assertIsNone(stale, "基线没有的发现是新增违规，必须 FAIL")

    def test_no_baseline_refuses_excusal(self):
        self.put("new.sh", "#!/bin/bash\nBAD\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        self.put("untracked.sh", "#!/bin/bash\nBAD\n")      # 从未入库 → 无基线
        stale = gate_lib.baseline_stale_finding(
            self.root, "untracked.sh", self.checker(), "CODE1 bad",
        )
        self.assertIsNone(stale, "无基线证据绝不豁免（verdict-integrity 既有原则）")


class GateDecisionLogTests(GitRepoCase):
    """门禁决策必须落盘可回溯（哪个语言、什么命令、rc、结论）。"""

    def test_decision_log_records_language_command_and_status(self):
        home = Path(self._td.name) / "home"
        os.environ["CODEGUARD_HOME"] = str(home)
        try:
            gate_lib.record_gate_decision(
                self.root, "shell", ["shellcheck", "x.sh"], 1, "FAIL", "检查发现违规")
            gate_lib.record_gate_decision(
                self.root, "java", ["mvn", "-B", "verify"], 1, "UNVERIFIED", "工具链执行异常")
            log = (home / "gate-decisions.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(2, len(log))
            first = json.loads(log[0])
            self.assertEqual("shell", first["lang"])
            self.assertEqual(["shellcheck", "x.sh"], first["cmd"])
            self.assertEqual(1, first["rc"])
            self.assertEqual("FAIL", first["status"])
            self.assertEqual(self.root.name, first["repo"])
            self.assertIn("ts", first)
        finally:
            os.environ.pop("CODEGUARD_HOME", None)


class PathspecResolutionTests(GitRepoCase):
    """git add 的 pathspec 必须用 git 自己的解析（glob/目录/等价语法）。

    实现已让位：pre_tool_git_guard.py 正被并行会话活跃修改（其 chain_skip_gate
    与本批 inline_skip_gate 互补），避免竞争写入；待其稳定后把 match_pathspec
    接进 staging_intent 再解除跳过。
    """

    @unittest.skip("pending: pre_tool_git_guard.py 并行修改中，match_pathspec 待接线")
    def test_glob_pathspec_expands_to_real_files(self):
        self.put("a.py", "print(1)\n")
        self.put("pkg/b.py", "print(2)\n")
        matched = pre_tool_git_guard.match_pathspec(self.root, self.root, "*.py")
        self.assertCountEqual(["a.py", "pkg/b.py"], matched, "basename glob 命中任意层级")
        matched = pre_tool_git_guard.match_pathspec(self.root, self.root, "pkg/*.py")
        self.assertEqual(["pkg/b.py"], matched)

    @unittest.skip("pending: pre_tool_git_guard.py 并行修改中，match_pathspec 待接线")
    def test_directory_pathspec_expands(self):
        self.put("pkg/a.py", "x=1\n")
        self.put("pkg/sub/b.py", "y=2\n")
        matched = pre_tool_git_guard.match_pathspec(self.root, self.root, "pkg")
        self.assertCountEqual(["pkg/a.py", "pkg/sub/b.py"], matched)

    @unittest.skip("pending: pre_tool_git_guard.py 并行修改中，match_pathspec 待接线")
    def test_nonmatching_pathspec_returns_empty(self):
        self.put("a.py", "print(1)\n")
        self.assertEqual([], pre_tool_git_guard.match_pathspec(self.root, self.root, "*.rs"))


class RuffTargetVersionTests(GitRepoCase):
    """ruff 注入配置时按项目声明的 Python 版本自适应 target-version。"""

    def test_requires_python_drives_target_version(self):
        self.put("pyproject.toml", '[project]\nname = "x"\nrequires-python = ">=3.8"\n')
        args = scope.ruff_config_args(["ruff", "check", "."], self.root)
        self.assertIn("--target-version", args)
        self.assertIn("py38", args)

    def test_python_version_file_drives_target_version(self):
        self.put(".python-version", "3.9\n")
        args = scope.ruff_config_args(["ruff", "check", "."], self.root)
        self.assertIn("py39", args)

    def test_no_declaration_keeps_default(self):
        args = scope.ruff_config_args(["ruff", "check", "."], self.root)
        self.assertNotIn("--target-version", args)
        self.assertIn("--config", args)


class EscapeHatchNoticeTests(GitRepoCase):
    """内联豁免放行时必须向用户明示，不得静默绕过。

    同样待 pre_tool_git_guard.py 并行修改稳定后接线（提醒输出在 main() 的
    inline_skip_gate 分支加 hookSpecificOutput）。
    """

    @unittest.skip("pending: pre_tool_git_guard.py 并行修改中，豁免提醒待接线")
    def test_inline_skip_emits_user_visible_notice(self):
        self.put("a.py", "print(1)\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "base")
        self.put("a.py", "print(2)\n")
        _git(self.root, "add", "-A")
        os.environ["CODEGUARD_HOME"] = str(Path(self._td.name) / "home")
        try:
            import contextlib
            import io
            from unittest.mock import patch
            buf = io.StringIO()
            payload = {"tool_input": {
                "command": f"git -C {self.root} -c codeguard.skipGate=true commit -m x"}}
            with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                 patch.object(pre_tool_git_guard, "ensure_user_path"), \
                 contextlib.redirect_stdout(buf):
                rc = pre_tool_git_guard.main()
            self.assertEqual(0, rc)
            out = buf.getvalue()
            self.assertIn("codeguard", out)
            self.assertTrue("豁免" in out or "skip" in out.lower(),
                            "放行必须向用户明示豁免发生")
        finally:
            os.environ.pop("CODEGUARD_HOME", None)


class OpenspecValidateResilienceTests(GitRepoCase):
    """openspec validate 内部异常不得逃逸成 fail-open 静默吞。"""

    def test_unexpected_exception_is_skipped_not_raised(self):
        self.put("openspec/config.yaml", "schema: spec-driven\n")
        from unittest.mock import patch
        with patch.object(gate_lib.shutil, "which", return_value="/usr/bin/fake-openspec"), \
             patch.object(gate_lib.subprocess, "run", side_effect=NameError("boom")):
            result = gate_lib._openspec_validate(self.root)
        self.assertIn("skipped", result)
        self.assertTrue(result["failures"] == [])
        self.assertIn("openspec", (result["skipped"] or ""))


class SkipGateRetryTests(GitRepoCase):
    """git config 读取必须低超时重试，两次失败才按未豁免 + 审计处理。"""

    def test_retry_after_timeout_then_success(self):
        _git(self.root, "config", "codeguard.skipGate", "true")
        calls = {"n": 0}
        real_run = gate_lib.subprocess.run

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise gate_lib.subprocess.TimeoutExpired("git", 3)
            return real_run(*args, **kwargs)

        from unittest.mock import patch
        os.environ["CODEGUARD_HOME"] = str(Path(self._td.name) / "home")
        try:
            with patch.object(gate_lib.subprocess, "run", side_effect=flaky):
                self.assertTrue(gate_lib.skip_gate_via_git_config(self.root),
                                "第一次超时后重试成功必须算豁免")
            state = (Path(self._td.name) / "home" / "session_state.json")
            self.assertFalse(state.exists(), "最终成功不应留 read-error 审计")
        finally:
            os.environ.pop("CODEGUARD_HOME", None)

    def test_two_failures_audited(self):
        from unittest.mock import patch
        home = Path(self._td.name) / "home"
        os.environ["CODEGUARD_HOME"] = str(home)
        try:
            with patch.object(gate_lib.subprocess, "run",
                              side_effect=gate_lib.subprocess.TimeoutExpired("git", 3)):
                self.assertFalse(gate_lib.skip_gate_via_git_config(self.root))
            state = json.loads((home / "session_state.json").read_text(encoding="utf-8"))
            self.assertIn("skipGate-read-error", state["_skip"]["kinds"])
        finally:
            os.environ.pop("CODEGUARD_HOME", None)


if __name__ == "__main__":
    unittest.main()
