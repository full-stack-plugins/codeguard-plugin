"""硬化修复回归测试（2026-09-22 批次）：覆盖 14 项审计发现中可离线锁定的行为。

对应 OpenSpec change 2026-09-22-harden-commit-gate（hook-protocol /
gate-trigger-policy / language-gate-commands delta）。每个用例锚定一个实测踩过的坑：
整调用拦截语义、脚本间接绕过、缓存键陈旧、delta 作用域、非 git 工作区回退、
skipGate 双门一致性、全仓 format 漂移、exit 2 误判、双副本重复、bypass 记账。
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
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(PLUGIN / "hooks"))

import gate_lib  # noqa: E402
import pre_tool_git_guard as guard  # noqa: E402
import scope  # noqa: E402


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def _fresh_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="cg-hard-"))
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    return root


def _run_hook(script: str, payload: dict | None, cwd: Path,
              env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(PLUGIN / "hooks" / script)],
        input=json.dumps(payload) if payload is not None else "",
        capture_output=True, text=True, cwd=cwd, env=env, timeout=120,
    )


class IndirectGuardTests(unittest.TestCase):
    """P0-2：脚本间接执行曾完整绕过硬门禁（实测 /tmp runner 连推 4 次漏网）。"""

    def test_direct_git_still_guarded(self) -> None:
        self.assertTrue(guard.is_guarded("git commit -m x"))
        self.assertTrue(guard.is_guarded("cd r && git push origin main"))

    def test_echo_with_git_text_is_not_guarded(self) -> None:
        self.assertFalse(guard.is_guarded('echo "git push 是危险命令"'))
        self.assertFalse(guard.is_guarded("git status && ls"))

    def test_script_file_indirection_is_guarded(self) -> None:
        script = Path(tempfile.mkdtemp(prefix="cg-ind-")) / "runner.sh"
        script.write_text('set -e\ncd /tmp\ngit commit -m "from script"\n', encoding="utf-8")
        self.assertTrue(guard.is_guarded(f"bash {script}"))

    def test_inline_dash_c_is_guarded(self) -> None:
        self.assertTrue(guard.is_guarded('bash -c "git commit -m inline"'))

    def test_harmless_script_is_not_guarded(self) -> None:
        script = Path(tempfile.mkdtemp(prefix="cg-ind-")) / "harmless.sh"
        script.write_text("echo hi\n", encoding="utf-8")
        self.assertFalse(guard.is_guarded(f"bash {script}"))

    def test_documented_boundary_subprocess_construction(self) -> None:
        """静态扫描的能力边界（docstring 已声明）：拼接式 subprocess 不在承诺内。"""
        script = Path(tempfile.mkdtemp(prefix="cg-ind-")) / "crafted.py"
        script.write_text('import subprocess\nsubprocess.run(["git", "push"])\n', encoding="utf-8")
        self.assertFalse(guard.is_guarded(f"python3 {script}"))
        # 但直接命令词形态仍然命中
        script.write_text("git push origin main\n", encoding="utf-8")
        self.assertTrue(guard.is_guarded(f"python3 {script}"))


class WholeCallNoticeTests(unittest.TestCase):
    """P0-1：整调用被拒时必须声明"前序步骤也没执行"（实测编辑被吞假象 ×3）。"""

    def test_directive_mentions_whole_call(self) -> None:
        text = gate_lib.gate_directive([("shell", "SC2086: x", "shfmt -w .", "brew")])
        self.assertIn("整个工具调用没有执行", text)
        self.assertIn("拆成两次独立的工具调用", text)
        # 首行契约保持：综述在最前
        self.assertTrue(text.splitlines()[0].startswith("codeguard ❌ 提交门禁未通过："))


class CacheKeyTests(unittest.TestCase):
    """P0-3：修完未暂存的文件必须让缓存键变化（retry-timing 陷阱）。"""

    def setUp(self) -> None:
        self.repo = _fresh_repo()
        (self.repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "i")

    def test_tracked_unstaged_edit_changes_key(self) -> None:
        k1 = gate_lib._gate_cache_key(self.repo, ["python"])
        (self.repo / "a.py").write_text("x = 2\n", encoding="utf-8")
        k2 = gate_lib._gate_cache_key(self.repo, ["python"])
        self.assertNotEqual(k1, k2)

    def test_untracked_content_edit_changes_key(self) -> None:
        (self.repo / "u.py").write_text("x = 1\n", encoding="utf-8")
        k1 = gate_lib._gate_cache_key(self.repo, ["python"])
        (self.repo / "u.py").write_text("x = 2\n", encoding="utf-8")
        k2 = gate_lib._gate_cache_key(self.repo, ["python"])
        self.assertNotEqual(k1, k2)


class DeltaScopeTests(unittest.TestCase):
    """P0-4：delta 默认作用域 + changed_files 三路并集。"""

    def test_changed_files_covers_three_lanes(self) -> None:
        repo = _fresh_repo()
        (repo / "base.py").write_text("x = 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "i")
        self.assertEqual(scope.changed_files(repo), [])
        (repo / "base.py").write_text("x = 2\n", encoding="utf-8")          # 未暂存
        (repo / "staged.py").write_text("y = 1\n", encoding="utf-8")        # staged
        _git(repo, "add", "staged.py")
        (repo / "fresh.py").write_text("z = 1\n", encoding="utf-8")         # 未跟踪
        got = scope.changed_files(repo)
        self.assertEqual(got, ["base.py", "fresh.py", "staged.py"])

    def test_non_git_returns_none(self) -> None:
        self.assertIsNone(scope.changed_files(Path(tempfile.mkdtemp(prefix="cg-nogit-"))))

    def test_scope_default_is_delta_for_git_repo(self) -> None:
        repo = _fresh_repo()
        self.assertEqual(scope.changed_files(repo), [])
        (repo / "bad.py").write_text("import os,sys\n", encoding="utf-8")
        # 未跟踪坏文件存在 → delta 会把它纳入检查（此处只验证并集非空）
        self.assertEqual(scope.changed_files(repo), ["bad.py"])


class ScopeCmdTests(unittest.TestCase):
    """P1-6/P1-8：命令物化——ruff 默认配置注入、扫描 token 收敛、裸命令追加。"""

    def test_dot_token_replaced_by_files(self) -> None:
        cmd = scope.scope_cmd(["ruff", "check", "."], "/tmp/no-such-proj", files=["a.py", "b.py"])
        self.assertIn("a.py", cmd)
        self.assertIn("b.py", cmd)
        self.assertNotIn(".", [tok for tok in cmd if tok == "."])

    def test_ruff_config_injected_only_without_own_config(self) -> None:
        bare = Path(tempfile.mkdtemp(prefix="cg-cfg-"))
        cmd = scope.scope_cmd(["ruff", "check", "."], bare, files=["a.py"])
        self.assertIn("--config", cmd)
        self.assertTrue(Path(cmd[cmd.index("--config") + 1]).is_file())
        (bare / "ruff.toml").write_text('line-length = 88\n', encoding="utf-8")
        cmd2 = scope.scope_cmd(["ruff", "check", "."], bare, files=["a.py"])
        self.assertNotIn("--config", cmd2)

    def test_glob_token_and_excludes_dropped_in_delta(self) -> None:
        cmd = scope.scope_cmd(
            ["npx", "--no-install", "markdownlint-cli2", "**/*.md", "#node_modules"],
            "/tmp/x", files=["R.md"],
        )
        self.assertIn("R.md", cmd)
        self.assertNotIn("**/*.md", cmd)
        self.assertNotIn("#node_modules", cmd)

    def test_bare_command_appends_files(self) -> None:
        cmd = scope.scope_cmd(["yamllint", "."], "/tmp/x", files=["a.yaml"])
        self.assertEqual(cmd, ["yamllint", "a.yaml"])

    def test_file_placeholder_single_file(self) -> None:
        cmd = scope.scope_cmd(["shellcheck", "{file}"], "/tmp/x", single_file="s.sh")
        self.assertEqual(cmd, ["shellcheck", "s.sh"])

    def test_full_mode_adds_ruff_excludes(self) -> None:
        cmd = scope.scope_cmd(["ruff", "check", "."], "/tmp/no-such-proj", full_excludes=True)
        self.assertIn("--exclude", cmd)
        self.assertIn("vendor", cmd)


class ExitTwoTests(unittest.TestCase):
    """P1-9：exit 2 = 工具链异常，不是 lint 结论——归未验证，绝不拦提交。"""

    def test_gate_rc2_is_skipped_not_failed(self) -> None:
        repo = _fresh_repo()
        (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        _git(repo, "add", "-A")

        class _Fake:
            returncode = 2
            stdout = "npm warn junk\n"
            stderr = "Error: cannot find module\n"

        original_run = gate_lib.subprocess.run
        original_probe = gate_lib.probe_toolchain
        original_uses = gate_lib.project_uses_linter
        gate_lib.subprocess.run = lambda *a, **k: _Fake()
        gate_lib.probe_toolchain = lambda *a, **k: (True, "")
        gate_lib.project_uses_linter = lambda *a, **k: True
        try:
            failures, skipped = gate_lib._run_gate_uncached(
                repo, {"lint_timeout_seconds": 5}, ["python"], scope="repo", changed=None,
            )
        finally:
            gate_lib.subprocess.run = original_run
            gate_lib.probe_toolchain = original_probe
            gate_lib.project_uses_linter = original_uses
        self.assertEqual(failures, [])
        self.assertTrue(any("工具链异常未验证" in s and "exit 2" in s for s in skipped), skipped)


class TriggerNegationTests(unittest.TestCase):
    """P1-10：否定语境（未提交/别提交）不得触发；祈使与行动意图仍触发。"""

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "upv", PLUGIN / "hooks" / "user_prompt_validator.py"
        )
        cls.upv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.upv)

    def test_negated_statements_do_not_trigger(self) -> None:
        for text in ("未提交任何东西", "还没提交呢", "别提交这些文件"):
            with self.subTest(text=text):
                self.assertFalse(self.upv.is_trigger(text))

    def test_imperatives_still_trigger(self) -> None:
        for text in ("提交代码", "commit this now", "请帮我 push"):
            with self.subTest(text=text):
                self.assertTrue(self.upv.is_trigger(text))


class UserPromptSubmitScopeTests(unittest.TestCase):
    """P0-5/P2-12：非 git 目录显式跳过（不回退扫描）；skipGate 双门一致；bypass 记账。"""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="cg-home-"))
        self.env = {"CODEGUARD_HOME": str(self.home)}

    def test_non_git_dir_is_skipped_with_note(self) -> None:
        bare = Path(tempfile.mkdtemp(prefix="cg-nogit-"))
        r = _run_hook(
            "user_prompt_validator.py", {"user_prompt": "提交代码"}, bare,
            env_extra=self.env,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("不是 git 仓库", r.stdout)
        self.assertNotIn("强制指令", r.stdout)

    def test_skipgate_suppresses_soft_gate_too(self) -> None:
        repo = _fresh_repo()
        (repo / "bad.py").write_text("import os,sys\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "config", "codeguard.skipGate", "true")
        r = _run_hook(
            "user_prompt_validator.py", {"user_prompt": "提交代码"}, repo,
            env_extra=self.env,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "", "skipGate 时软门禁必须静默")
        state = json.loads((self.home / "session_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["_skip"]["kinds"].get("skipGate"), 1)
        _git(repo, "config", "--unset", "codeguard.skipGate")

    def test_env_bypass_is_counted(self) -> None:
        repo = _fresh_repo()
        r = _run_hook(
            "user_prompt_validator.py", {"user_prompt": "提交代码"}, repo,
            env_extra={**self.env, "CODEGUARD_SKIP_GATE": "1"},
        )
        self.assertEqual(r.returncode, 0)
        state = json.loads((self.home / "session_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["_skip"]["kinds"].get("env"), 1)


class StopSummaryTests(unittest.TestCase):
    """P2-12/P2-13：状态目录迁移 + 绕过可见 + skipGate 遗留提醒。"""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="cg-home-"))
        self.env = {"CODEGUARD_HOME": str(self.home)}

    def test_skip_count_rendered(self) -> None:
        gate_lib.session_state_path  # noqa: B018 — 确保符号存在
        os.environ["CODEGUARD_HOME"] = str(self.home)
        try:
            gate_lib.record_skip_event("skipGate")
        finally:
            os.environ.pop("CODEGUARD_HOME", None)
        repo = _fresh_repo()
        r = _run_hook("stop_summary.py", None, repo, env_extra=self.env)
        self.assertIn("绕过门禁 1 次", r.stdout)

    def test_left_enabled_skipgate_is_flagged(self) -> None:
        repo = _fresh_repo()
        _git(repo, "config", "codeguard.skipGate", "true")
        r = _run_hook("stop_summary.py", None, repo, env_extra=self.env)
        self.assertIn("仍为 true", r.stdout)
        _git(repo, "config", "--unset", "codeguard.skipGate")

    def test_state_path_honors_home_override(self) -> None:
        os.environ["CODEGUARD_HOME"] = str(self.home)
        try:
            self.assertEqual(gate_lib.session_state_path(), self.home / "session_state.json")
        finally:
            os.environ.pop("CODEGUARD_HOME", None)


class EventDedupTests(unittest.TestCase):
    """P2-11：同 key 窗口内二次触发被抑制（双副本场景），且 key 空间互不干扰。"""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="cg-home-"))
        os.environ["CODEGUARD_HOME"] = str(self.home)

    def tearDown(self) -> None:
        os.environ.pop("CODEGUARD_HOME", None)

    def test_same_key_within_window_suppressed(self) -> None:
        self.assertFalse(gate_lib.should_suppress_event("pre:abc123"))
        self.assertTrue(gate_lib.should_suppress_event("pre:abc123"))

    def test_different_key_not_suppressed(self) -> None:
        gate_lib.should_suppress_event("pre:one")
        self.assertFalse(gate_lib.should_suppress_event("pre:two"))


if __name__ == "__main__":
    unittest.main()


# ══════════ 2026-09-22 push-face batch（2026-09-22-push-face-delta）══════════

class GuardedModeTests(unittest.TestCase):
    """面判定与命中判定同源：直接与一层间接都必须选出正确的面。"""

    def test_direct_faces(self) -> None:
        self.assertEqual(guard._guarded_mode("git commit -m x"), "commit")
        self.assertEqual(guard._guarded_mode("cd r && git push"), "push")

    def test_chained_takes_push_face(self) -> None:
        self.assertEqual(
            guard._guarded_mode("git add -A && git commit -m x && git push"), "push"
        )

    def test_not_guarded_returns_none(self) -> None:
        self.assertIsNone(guard._guarded_mode('echo "git push"'))
        self.assertIsNone(guard._guarded_mode("git status"))

    def test_indirect_script_face(self) -> None:
        script = Path(tempfile.mkdtemp(prefix="cg-face-")) / "release.sh"
        script.write_text("set -e\ngit push origin main\n", encoding="utf-8")
        self.assertEqual(guard._guarded_mode(f"bash {script}"), "push")


def _pushable_repo() -> Path:
    """bare 远端 + 工作克隆 + 一个绕过门禁的坏提交（工作树干净）。"""
    import shutil
    bare = Path(tempfile.mkdtemp(prefix="cg-bare-"))
    work = Path(tempfile.mkdtemp(prefix="cg-work-"))
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], capture_output=True)
    _git(work, "config", "user.email", "t@t")
    _git(work, "config", "user.name", "t")
    (work / "good.txt").write_text("ok\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "init")
    r = subprocess.run(
        ["git", "push", "-q", "-u", "origin", "HEAD"], cwd=work,
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    # 绕过门禁（模拟用户手动提交/装插件前的提交）：坏 shell 文件入库
    (work / "bad.sh").write_text("#!/bin/bash\nif [ $x = y ]; then true; fi\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "bad commit outside the gate")
    shutil.rmtree(bare, ignore_errors=True)  # 远端留否无所谓：upstream 已建立
    return work


class PushFaceTests(unittest.TestCase):
    """0.8.0 引入的空洞：坏提交入史后工作树干净，push 门禁曾得到空集。"""

    def test_changed_files_faces(self) -> None:
        work = _pushable_repo()
        self.assertEqual(scope.changed_files(work, mode="commit"), [])
        self.assertEqual(scope.changed_files(work, mode="push"), ["bad.sh"])

    @unittest.skipUnless(
        __import__("shutil").which("shellcheck"), "shellcheck 未安装"
    )
    def test_push_is_blocked_and_commit_is_not(self) -> None:
        import shutil
        work = _pushable_repo()
        env_extra = {"CODEGUARD_HOME": str(Path(tempfile.mkdtemp(prefix="cg-home-")))}
        r_push = _run_hook(
            "pre_tool_git_guard.py",
            {"tool_name": "Bash", "tool_input": {"command": "git push"}},
            work, env_extra=env_extra,
        )
        self.assertEqual(r_push.returncode, 2, r_push.stderr[:400])
        self.assertIn("shell", r_push.stderr)
        r_commit = _run_hook(
            "pre_tool_git_guard.py",
            {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}},
            work, env_extra=env_extra,
        )
        # commit 面空集：历史里已入库的东西不该拦"下一次干净提交"
        self.assertEqual(r_commit.returncode, 0, r_commit.stderr[:400])
        shutil.rmtree(work, ignore_errors=True)

    def test_ups_uses_push_face_for_push_intent(self) -> None:
        import shutil
        work = _pushable_repo()
        env_extra = {"CODEGUARD_HOME": str(Path(tempfile.mkdtemp(prefix="cg-home-")))}
        r_push = _run_hook(
            "user_prompt_validator.py", {"user_prompt": "请帮我 push"}, work,
            env_extra=env_extra,
        )
        self.assertEqual(r_push.returncode, 0)
        self.assertIn("codeguard ❌", r_push.stdout, "push 意图必须走 push 面并报出问题")
        r_commit = _run_hook(
            "user_prompt_validator.py", {"user_prompt": "提交代码"}, work,
            env_extra=env_extra,
        )
        self.assertIn("✅", r_commit.stdout, "commit 意图走空的 commit 面应通过")
        shutil.rmtree(work, ignore_errors=True)


class UnverifiedParityTests(unittest.TestCase):
    """CLI exit 127 与钩子 skipped 口径对齐（此前 CLI 报失败）。"""

    def test_rc_127_is_unverified_in_run_per_language(self) -> None:
        import run_per_language as rpl

        class _Fake:
            returncode = 127
            stdout = ""
            stderr = "command not found"

        original = rpl.subprocess.run
        rpl.subprocess.run = lambda *a, **k: _Fake()
        try:
            results = rpl.run_check(["python"], Path(tempfile.mkdtemp(prefix="cg-127-")))
        finally:
            rpl.subprocess.run = original
        self.assertTrue(results[0]["passed"])
        self.assertIn("exit 127", results[0].get("unverified", ""))


class FourHookDedupTests(unittest.TestCase):
    """SessionStart/Stop 也按 session_id 去重（四钩子同一规则）。"""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="cg-home-"))
        self.env = {"CODEGUARD_HOME": str(self.home)}

    def test_session_start_second_copy_silent(self) -> None:
        repo = _fresh_repo()
        (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        payload = {"session_id": "s-dedup-1"}
        first = _run_hook("env_check.py", payload, repo, env_extra=self.env)
        second = _run_hook("env_check.py", payload, repo, env_extra=self.env)
        self.assertEqual(first.returncode, 0)
        self.assertTrue(first.stdout.strip(), "第一份必须正常输出")
        self.assertEqual(second.returncode, 0)
        self.assertEqual(second.stdout.strip(), "", "同会话第二份必须静默")

    def test_stop_second_copy_silent(self) -> None:
        repo = _fresh_repo()
        payload = {"session_id": "s-dedup-2"}
        first = _run_hook("stop_summary.py", payload, repo, env_extra=self.env)
        second = _run_hook("stop_summary.py", payload, repo, env_extra=self.env)
        self.assertTrue(first.stdout.strip())
        self.assertEqual(second.stdout.strip(), "", "同会话第二份必须静默")

    def test_different_sessions_not_deduped(self) -> None:
        repo = _fresh_repo()
        a = _run_hook("stop_summary.py", {"session_id": "s-a"}, repo, env_extra=self.env)
        b = _run_hook("stop_summary.py", {"session_id": "s-b"}, repo, env_extra=self.env)
        self.assertTrue(a.stdout.strip())
        self.assertTrue(b.stdout.strip())
