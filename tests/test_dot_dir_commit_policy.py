"""点前缀目录入库策略测试（2026-09-23）。

需求来源：用户指令「codeguard 要默认忽略 . 开头的目录和文件」。实测背景：
插件仓发版时 .agents/plugins/marketplace.json 与 .codex-plugin/plugin.json
被提交内容安全检查判成"依赖/产物目录不应入库"，阻断 codegraph-plugin 发版
——它们是宿主插件清单（第一方配置），必须可入库。

锁定三件事：
1. 点前缀**目录**段不再触发"不应入库"目录拦截（.agents/.codex-plugin/.github/...）；
2. 非点目录（build/dist/target/vendor/node_modules...）维持原拦截；
3. 密钥类**文件**模式不受点规则影响（.env、*.pem、.DS_Store 仍拦截），
   vendor 嵌套特例与 fixture db 特例维持不变。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

from codeguard.path_policy import check_paths  # noqa: E402


def flagged(paths: list[str]) -> set[str]:
    return {v[0] for v in check_paths(paths)}


class DotDirCommitPolicyTests(unittest.TestCase):
    def test_dot_dirs_are_default_ignored(self) -> None:
        """点前缀目录 = 宿主插件清单/第一方配置，允许入库。"""
        paths = [
            ".agents/plugins/marketplace.json",
            ".codex-plugin/plugin.json",
            ".zcode-plugin/plugin.json",
            ".github/workflows/ci.yml",
            ".claude/settings.json",
            ".kimi-code/state.json",
        ]
        self.assertEqual(flagged(paths), set(), f"点目录不应被拦截: {flagged(paths)}")

    def test_non_dot_dirs_still_flagged(self) -> None:
        """非点产物/依赖目录维持原拦截。"""
        paths = [
            "build/out.js",
            "dist/bundle.js",
            "target/site/a.html",
            "node_modules/p/index.js",
            "coverage/lcov.info",
            "vendor/pkg/x.py",
        ]
        self.assertEqual(flagged(paths), set(paths))

    def test_secret_dot_files_still_flagged(self) -> None:
        """点规则只放开目录；密钥/垃圾**文件**模式照拦。"""
        paths = [".env", "src/secret.pem", "keys/server.key", ".DS_Store"]
        self.assertEqual(flagged(paths), set(paths))

    def test_root_dotfile_without_secret_pattern_allowed(self) -> None:
        """无敏感模式的普通点文件（.gitignore/.npmrc）本来就不拦。"""
        self.assertEqual(flagged([".gitignore", ".npmrc", ".markdownlint-cli2.jsonc"]), set())

    def test_vendor_and_fixture_exceptions_unchanged(self) -> None:
        """vendor 嵌套特例与 fixture db 特例维持原行为。"""
        self.assertEqual(
            flagged(["scripts/vendor/skill_vendor.py", "tests/fixtures/sample.db"]),
            set(),
        )
        self.assertEqual(flagged(["sample.db"]), {"sample.db"})


if __name__ == "__main__":
    unittest.main()
