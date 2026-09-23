"""文档可执行断言的行为互证（2026-09-23 doc-behavior-parity）。

「文档与行为矛盾」家族累计 7 例靠人工考古发现；本模块把可机器判定的文档断言
钉在行为测试上——断言**双向取值**（读文档文本 + 读实现），文档更新与行为脱节即红。
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

from codeguard.path_policy import is_dot_prefixed
from codeguard.repository_policy import env_skip_gate


class BypassValueParityTests(unittest.TestCase):
    def test_directive_value_vocabulary_matches_parser(self) -> None:
        from codeguard import reporting
        text = reporting.gate_directive([("shell", "SC2086: x", "shfmt -w .", "brew")])
        # 文案声明的值词表与解析器接受的词表互证
        self.assertRegex(text, r"1/true/yes")
        for value, want in (("1", True), ("true", True), ("yes", True),
                            ("0", False), ("false", False), ("", False)):
            with unittest.mock.patch.dict("os.environ",
                                          {"CODEGUARD_SKIP_GATE": value}, clear=False):
                self.assertEqual(env_skip_gate(), want, value)
        self.assertIn("内联赋值不会传入", text)  # 行为：宿主内联赋值不到钩子进程环境

    def test_parser_matches_config_value_vocabulary(self) -> None:
        # 与 config 豁免同词表：true/1/yes（大小写不敏感），其余不豁免
        for value, want in (("TRUE", True), ("Yes", True), ("no", False), ("off", False)):
            with unittest.mock.patch.dict("os.environ",
                                          {"CODEGUARD_SKIP_GATE": value}, clear=False):
                self.assertEqual(env_skip_gate(), want, value)


class EcosystemAliasParityTests(unittest.TestCase):
    def test_bin_usage_ecosystems_match_canonical_set(self) -> None:
        from codeguard.cve import ECOSYSTEM_SCANNERS, canonical_ecosystem
        usage = (PLUGIN / "bin" / "codeguard").read_text(encoding="utf-8")
        m = re.search(r"生态: ([^\n]+)", usage)
        self.assertIsNotNone(m)
        named = set(re.findall(r"[a-z]+", m.group(1)))
        for canonical in ECOSYSTEM_SCANNERS:
            self.assertIn(canonical, named, f"bin 用法未列 {canonical}")
        for word in named:
            if len(word) > 2:
                self.assertIsNotNone(canonical_ecosystem(word), f"bin 用法列了未声明标识 {word}")


class DotPrefixParityTests(unittest.TestCase):
    def test_agents_md_claim_matches_predicate(self) -> None:
        text = (PLUGIN / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("默认忽略", text)  # AGENTS.md 硬性禁令声明
        tmp = Path(tempfile.mkdtemp())
        self.assertTrue(is_dot_prefixed(tmp / ".eslintrc.js", tmp))
        self.assertFalse(is_dot_prefixed(tmp / "src" / "a.py", tmp))


class MarkdownProbeParityTests(unittest.TestCase):
    def test_documented_probe_form_matches_registry(self) -> None:
        registry = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        md = next(l for l in registry["languages"] if l["id"] == "markdown")
        # 文档记载唯一可用探活形态为 --format（--version 不被识别、会被当 glob）
        self.assertIn("--format", md.get("probe", []))
        self.assertNotIn("--version", md.get("probe", []))


class CveExitCodeParityTests(unittest.TestCase):
    def test_readme_and_bin_claims_match_exit_constants(self) -> None:
        from codeguard import cve_policy
        self.assertEqual(
            (cve_policy.EXIT_PASS, cve_policy.EXIT_UNVERIFIED,
             cve_policy.EXIT_FINDINGS, cve_policy.EXIT_USAGE),
            (0, 1, 2, 3))
        for doc in (PLUGIN / "README.md", PLUGIN / "README.zh-CN.md",
                    PLUGIN / "bin" / "codeguard"):
            text = doc.read_text(encoding="utf-8")
            # 钉码集合 0/1/2/3 的声明存在（措辞允许差异，语义由上方常量钉住）
            self.assertRegex(text, r"[`\s：:]0.{0,60}3", doc.name)
            self.assertRegex(text, r"[`\s：:]1.{0,60}[`\s：:]2", doc.name)


if __name__ == "__main__":
    unittest.main()
