"""P0 三项硬化回归测试（2026-09-22 增补）：覆盖会话级反馈修复的可锁定行为。

对应 OpenSpec change 2026-09-22-p0-routing-openspec-skipgate：
- P0#1 `gate_lib._run_one` 把 timeout=124 与 subprocess exit 124 都路由为不可证伪
  （而不是 false failure），并把 `lint_timeout_seconds` 默认提到 300。
- P0#2 `gate_lib._run_gate_uncached` 在语言 lint 聚合后跑一次
  `openspec validate --all --strict`（当 openspec/config.yaml 存在）。
- P0#3 `pre_tool_git_guard.resolve_project_roots` 返回空时：
  - cwd 一层子目录有 git 仓 → 兜底用 monorepo 模式；
  - 无 git 仓 → exit 2 + stderr 明确错误信息（不再静默放过）。

每个用例针对一个真实场景，断言触发后 P0 修复生效（不依赖端到端多仓物理环境）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(PLUGIN / "hooks"))

import gate_lib
import pre_tool_git_guard as guard
import user_config


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def _fresh_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="cg-p0-"))
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "README.md").write_text("init\n")
    _git(root, "add", "README.md")
    _git(root, "commit", "-q", "-m", "init")
    return root


# ============================================================
# P0#1 timeout 路由：subprocess.run 抛 TimeoutExpired 与自身返回 124
# 都应被路由为不可证伪（"skipped" 而非 "failure"）。
# ============================================================
class TimeoutRoutingTests(unittest.TestCase):

    def test_timeout_expired_is_routed_as_skipped_not_failure(self):
        """_run_one 捕获 TimeoutExpired → 返回 (124, "", "timeout after Ns")。

        上游 run_gate 把 124 视为 SKIPPED；本测锁定"超时不阻塞硬门禁"的契约。
        """
        # 通过反射检查：try 块有 TimeoutExpired 分支且 return 含 124。
        import ast
        import inspect
        src = Path(inspect.getfile(gate_lib)).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_one":
                body_src = ast.unparse(node.body)
                self.assertIn("TimeoutExpired", body_src)
                # 必须是 tuple 形式（return (124, ...)），不是裸 124
                self.assertRegex(body_src, r"return\s*\(124\b")
                # 必须同时处理 subprocess exit 124（避免 TimeoutExpired + 子进程 124 二者漏一种）
                self.assertIn("proc.returncode == 124", body_src)
                return
        self.fail("_run_one not found in gate_lib.py")

    def test_default_timeout_bumped_to_300s(self):
        """user_config 默认 lint_timeout_seconds 从 120 提到 300——Maven install 冷缓存普遍超时 2 分钟。

        不提默认会把 Maven install -DskipTests 的真实失败误报为 timeout 失败。
        """
        cfg = user_config.load_user_config()
        self.assertEqual(cfg["lint_timeout_seconds"], 300)


# ============================================================
# P0#2 OpenSpec validate 集成：仓有 openspec/config.yaml 时
# 跑 `openspec validate --all --strict`；无 openspec 仓不调用；
# CLI 缺失路由为 skipped。
# ============================================================
class OpenSpecIntegrationTests(unittest.TestCase):

    def test_no_openspec_config_returns_empty_skipped(self):
        """无 openspec/config.yaml 的仓不应触发 validate（影响最小原则）。"""
        from gate_lib import _openspec_validate
        result = _openspec_validate(Path(tempfile.mkdtemp(prefix="cg-os-")))
        self.assertEqual(result["failures"], [])
        self.assertIsNone(result["skipped"])

    def test_openspec_cli_missing_returns_skipped_not_failure(self):
        """openspec/config.yaml 存在但 CLI 缺失 → skipped（非 failures，非阻塞）。

        这是 monorepo 与 easy4j 系列仓的典型状态（仓用 OpenSpec 写计划，
        但当前容器工作区没装 openspec CLI）。
        """
        root = Path(tempfile.mkdtemp(prefix="cg-os-"))
        (root / "openspec").mkdir()
        (root / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
        # openspec CLI 在 PATH 中没有（shutil.which 返回 None）
        from gate_lib import _openspec_validate
        result = _openspec_validate(root)
        if shutil.which("openspec") is None:
            self.assertEqual(result["failures"], [])
            self.assertIn("openspec CLI 未安装", result["skipped"] or "")
        else:
            # 容器偶然装了 openspec：只要不崩即可（spec 验证可能 pass 也可能 fail）。
            self.assertIsInstance(result["failures"], list)


# ============================================================
# P0#3 静默跳过修复：roots=[] 时不再静默放过——
# cwd 一层子目录有 git 仓则兜底，否则 stderr + exit 2。
# ============================================================
class SilentSkipFixTests(unittest.TestCase):

    def test_fallback_root_returns_git_subdirs(self):
        """_fallback_roots：cwd 子目录里的 git 仓被收集（去重、保序、不含 cwd 自身）。"""
        root = Path(tempfile.mkdtemp(prefix="cg-fb-"))
        for name in ["aaa-repo", "bbb-repo", "ccc-repo"]:
            sub = root / name
            sub.mkdir()
            _git(sub, "init", "-q")
        (root / "not-a-repo").mkdir()  # 非 git 仓（无 .git/HEAD）
        found = guard._fallback_roots(root)
        names = [p.name for p in found]
        self.assertEqual(set(names), {"aaa-repo", "bbb-repo", "ccc-repo"})
        self.assertNotIn("not-a-repo", names)
        # cwd 自身不计入
        self.assertNotIn(root.resolve(), found)

    def test_fallback_skipped_when_no_git_subdirs(self):
        """cwd 子目录无 git 仓 → fallback 返回空列表（让上游 exit 2 + stderr）。"""
        root = Path(tempfile.mkdtemp(prefix="cg-fb-empty-"))
        (root / "regular-dir").mkdir()
        (root / "another-dir").mkdir()
        self.assertEqual(guard._fallback_roots(root), [])

    def test_root_is_git_no_fallback_needed(self):
        """cwd 本身就是 git 仓 → fallback 返回空（按主流程已有的 roots 处理）。"""
        root = _fresh_repo()
        self.assertEqual(guard._fallback_roots(root), [])

    def test_pushed_from_workspace_root_with_subdir_repos_is_covered(self):
        """模拟 push-all-branches.sh：从 workspace 根目录跑 `git push`。

        修复前 `resolve_project_roots` 在 cwd 是 git 仓时也能收集（这条路径仍能
        工作——cwd 自身就是仓时主流程能拦截）；修复后兜底路径（_fallback_roots）
        在 cwd 不是仓时兜底扫子目录。本测验证兜底路径在 cwd 不是仓时正确触发。

        关键：测试在临时 workspace 下运行（cwd 不是 git 仓），应触发兜底扫描。
        """
        workspace = Path(tempfile.mkdtemp(prefix="cg-mr-"))
        repo = workspace / "sdk-A"
        repo.mkdir()
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "t@t")
        _git(repo, "config", "user.name", "t")

        old_cwd = os.getcwd()
        try:
            os.chdir(workspace)
            # workspace 不是 git 仓；cd 链中没有仓：主流程 resolve_project_roots 返回空
            roots = guard.resolve_project_roots("git push origin main")
            self.assertEqual(roots, [])
            # 兜底：cwd = workspace，子目录 sdk-A 是 git 仓
            fallback = guard._fallback_roots(Path.cwd())
            self.assertEqual([p.name for p in fallback], ["sdk-A"])
            # 反向：cwd 是 git 仓时兜底返回空（主流程已通过 resolve_project_roots 处理）
            os.chdir(repo)
            self.assertEqual(guard._fallback_roots(Path.cwd()), [])
        finally:
            os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main(verbosity=2)