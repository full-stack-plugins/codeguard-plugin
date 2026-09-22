"""2026-09-23 会话反馈批次回归：zsh 剥离三面覆盖 + 兜底面收窄。

来自一次真实多 SDK 发布会话（codeguard 连拦 4 次：zsh SC1071 三连、且
openclaw 提交被 workspace 根散脚本与无关仓存量连带误拦）：
1. zsh 剥离只在 delta 面生效——全量/UPS/monorepo 回退面 .zsh 照送
   shellcheck → SC1071 误拦（根散脚本 + 子仓 zsh 双双中招）。
2. 部分剥离静默丢弃——提交方不知道有一部分文件压根没被检查。
3. monorepo 兜底把 workspace 下所有子仓连同根上散落脚本一起纳入拦路面——
   无关仓的存量违规也 block（越权误拦）。
4. skip 话术没有可执行的修复指令——AI/用户要自行猜测"怎么才能送检"。
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

from run_per_language import run_fix


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def _fresh_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="cg-sess2-"))
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    return root


def _run_guard(command: str, cwd: Path) -> subprocess.CompletedProcess:
    home = Path(tempfile.mkdtemp(prefix="cg-home-"))
    env = {**os.environ, "CODEGUARD_HOME": str(home), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(PLUGIN / "hooks" / "pre_tool_git_guard.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True, cwd=cwd, env=env, timeout=120, check=False,
    )


@unittest.skipUnless(__import__("shutil").which("shellcheck"), "shellcheck 未安装")
class ZshStripGateTests(unittest.TestCase):
    """#1/#2/#4：zsh 剥离的 skipped 话术必须带可执行修复指令，且不拦提交。"""

    def test_zsh_only_commit_passes_with_fix_hint(self) -> None:
        """纯 zsh 提交：剥离后放行（非 block），skip 话术带可执行修复。"""
        repo = _fresh_repo()
        (repo / "tool.zsh").write_text("setopt no_beep\n", encoding="utf-8")
        _git(repo, "add", "-A")
        r = _run_guard("git commit -m t", repo)
        self.assertEqual(r.returncode, 0,
                         f"纯 zsh 提交不得被拦: {r.stderr[:400]}")
        self.assertIn("shellcheck shell=bash", r.stdout,
                      "skip 话术必须给出可执行的修复指令")

    def test_zsh_partial_still_lints_remaining_sh(self) -> None:
        """zsh + sh 混合：zsh 剥离后余下 .sh 照常送检并拦真实违规。"""
        repo = _fresh_repo()
        (repo / "tool.zsh").write_text("setopt no_beep\n", encoding="utf-8")
        (repo / "bad.sh").write_text("#!/bin/bash\nif [ $x = y ]; then true; fi\n",
                                     encoding="utf-8")
        _git(repo, "add", "-A")
        r = _run_guard("git commit -m t", repo)
        self.assertEqual(r.returncode, 2, r.stderr[:400])
        self.assertIn("bad.sh", r.stderr, "余下 .sh 的真实违规必须拦")


@unittest.skipUnless(__import__("shutil").which("shellcheck"), "shellcheck 未安装")
class FallbackNarrowTests(unittest.TestCase):
    """#3：monorepo 兜底面收窄——无提交面的仓不得进拦路面。"""

    def _workspace(self) -> tuple[Path, Path, Path]:
        """workspace 根（非 git 仓）+ 两个子仓：dirty（staged 违规）/ stale
        （已提交违规但无提交面——模拟无关仓存量）。"""
        ws = Path(tempfile.mkdtemp(prefix="cg-fallback-ws-"))
        dirty = ws / "dirty-repo"
        dirty.mkdir()
        _git(dirty, "init", "-q")
        _git(dirty, "config", "user.email", "t@t")
        _git(dirty, "config", "user.name", "t")
        (dirty / "bad.sh").write_text("#!/bin/bash\nif [ $x = y ]; then true; fi\n",
                                      encoding="utf-8")
        _git(dirty, "add", "-A")

        stale = ws / "stale-repo"
        stale.mkdir()
        _git(stale, "init", "-q")
        _git(stale, "config", "user.email", "t@t")
        _git(stale, "config", "user.name", "t")
        (stale / "legacy.sh").write_text("#!/bin/bash\nif [ $x = y ]; then true; fi\n",
                                         encoding="utf-8")
        _git(stale, "add", "-A")
        _git(stale, "commit", "-q", "-m", "i")
        return ws, dirty, stale

    def test_fallback_blocks_only_dirty_repo(self) -> None:
        ws, _dirty, _stale = self._workspace()
        home = Path(tempfile.mkdtemp(prefix="cg-home-"))
        env = {**os.environ, "CODEGUARD_HOME": str(home), "PYTHONIOENCODING": "utf-8"}
        import subprocess
        r = subprocess.run(
            [sys.executable, str(PLUGIN / "hooks" / "pre_tool_git_guard.py")],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}),
            capture_output=True, text=True, cwd=ws, env=env, timeout=120, check=False,
        )
        self.assertEqual(r.returncode, 2, r.stderr[:400])
        self.assertIn("dirty-repo", r.stderr, "有提交面违规的仓必须拦")
        self.assertNotIn("stale-repo", r.stderr,
                         "无提交面的仓（存量违规）不得进拦路面")

    def test_fallback_all_clean_passes_audited(self) -> None:
        ws = Path(tempfile.mkdtemp(prefix="cg-fallback-clean-"))
        clean = ws / "clean-repo"
        clean.mkdir()
        _git(clean, "init", "-q")
        _git(clean, "config", "user.email", "t@t")
        _git(clean, "config", "user.name", "t")
        (clean / "good.sh").write_text('#!/bin/bash\nx="ok"\necho "$x"\n', encoding="utf-8")
        _git(clean, "add", "-A")
        _git(clean, "commit", "-q", "-m", "i")
        import subprocess
        home = Path(tempfile.mkdtemp(prefix="cg-home-"))
        env = {**os.environ, "CODEGUARD_HOME": str(home), "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run(
            [sys.executable, str(PLUGIN / "hooks" / "pre_tool_git_guard.py")],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}),
            capture_output=True, text=True, cwd=ws, env=env, timeout=120, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr[:400])
        state = json.loads((home / "session_state.json").read_text(encoding="utf-8"))
        kinds = state.get("_skip", {}).get("kinds", {})
        self.assertEqual(kinds.get("monorepo-fallback-empty"), 1,
                         "全空兜底必须留审计事件（monorepo-fallback-empty）")


class RunFixZshStripTests(unittest.TestCase):
    """#1（fix 面）：run_fix 与门禁共用 zsh 剥离认知——shfmt 不支持 zsh，
    -w 会重排方言语法造成损坏，必须跳过并给出可执行的门禁修复指令。"""

    def test_run_fix_skips_zsh_with_hint(self) -> None:
        root = _fresh_repo()
        (root / "tool.zsh").write_text("setopt no_beep\n", encoding="utf-8")
        results = run_fix(["shell"], root, files=["tool.zsh"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("status"), "SKIPPED")
        self.assertIn("zsh", results[0].get("note", ""))
        self.assertIn("shell=bash", results[0].get("note", ""))

    def test_run_fix_mixed_keeps_sh_and_skips_zsh(self) -> None:
        root = _fresh_repo()
        (root / "tool.zsh").write_text("setopt no_beep\n", encoding="utf-8")
        (root / "t.sh").write_text("echo ok\n", encoding="utf-8")
        results = run_fix(["shell"], root, files=["tool.zsh", "t.sh"])
        # shfmt 未安装时 b.sh 归"未执行"，但 zsh 的 SKIPPED 备注必须仍在
        skipped = [r for r in results if r.get("skipped")]
        self.assertTrue(any("zsh" in r.get("note", "") for r in skipped),
                        "zsh 跳过必须有明示备注")


if __name__ == "__main__":
    unittest.main()
