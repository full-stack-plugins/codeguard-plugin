"""2026-09-23 缺口补齐回归（claude-manifest / go cve / pathsep / strict_mode 摘除）。

OpenSpec change 2026-09-23-claude-manifest-and-go-cve。每条断言对应一个实测挂账项：
Claude 安装面缺件、go 生态映射为空、PATH 硬编码分隔符、零消费的假配置旋钮。
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "codeguard"))


class ClaudeManifestTests(unittest.TestCase):
    """Claude 宿主市场清单：存在、形态、版本链、发版工具覆盖。"""

    def test_manifest_exists_and_matches_canvas_shape(self) -> None:
        path = ROOT / ".claude-plugin" / "marketplace.json"
        self.assertTrue(path.is_file(), "Claude 宿主安装面缺 .claude-plugin/marketplace.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "codeguard-plugin")
        self.assertEqual(data["owner"], {"name": "full-stack-plugins"})
        entry = data["plugins"][0]
        self.assertEqual(entry["name"], "codeguard")
        self.assertEqual(entry["source"], "./")
        self.assertGreater(len(entry["description"]), 32)
        self.assertNotIn("mcpServers", data)

    def test_version_tracks_the_release_chain(self) -> None:
        claude = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        kimi = json.loads((ROOT / "kimi.plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(
            claude["plugins"][0]["version"], kimi["version"],
            "Claude 清单版本必须与其余 manifest 同链，否则安装面拿到错版本",
        )

    def test_bump_tool_covers_the_claude_manifest(self) -> None:
        source = (ROOT / "scripts" / "bump-plugin.mjs").read_text(encoding="utf-8")
        self.assertIn(".claude-plugin/marketplace.json", source,
                      "发版工具必须把 Claude 清单纳入版本链，否则下次发版必漂移")


class GoCveEcosystemTests(unittest.TestCase):
    """go 生态：规范映射独立条目，解析复用 trivy 格式，身份不与 universal 混同。"""

    def test_go_entry_in_the_canonical_map(self) -> None:
        from codeguard.cve import ECOSYSTEM_SCANNERS, language_ecosystem_map

        spec = ECOSYSTEM_SCANNERS["go"]
        self.assertEqual(spec["aliases"], ("golang", "gomod"))
        self.assertEqual(spec["languages"], ("go",))
        self.assertEqual(spec["markers"], ("go.mod", "go.sum"))
        self.assertEqual(language_ecosystem_map().get("go"), "go",
                         "go 语言此前映射到空——自动选择永远选不出可扫描生态")

    def test_report_identity_is_go_not_universal(self) -> None:
        from codeguard.cve_reports import parse_report

        sample = json.dumps({
            "Results": [{"Target": "go.mod", "Vulnerabilities": [
                {"VulnerabilityID": "GO-2026-0001", "Severity": "HIGH"},
                {"VulnerabilityID": "GO-2026-0002", "Severity": "CRITICAL"}]}]
        })
        report = parse_report("go", sample, "HIGH")
        self.assertGreater(report.observed, 0)
        self.assertTrue(report.exceeded)
        # 同一份 trivy 格式在 universal 下逐字段同判定（格式复用语义）
        other = parse_report("universal", sample, "HIGH")
        self.assertEqual(report.observed, other.observed)
        self.assertEqual(report.exceeded, other.exceeded)

    def test_missing_severity_is_not_prefiltered(self) -> None:
        """缺严重度发现不得被预过滤成假 PASS（与 universal 同语义）。"""
        from codeguard.cve_reports import parse_report

        sample = json.dumps({"Results": [{"Target": "go.sum", "Vulnerabilities": [
            {"VulnerabilityID": "GO-2026-0003"}]}]})
        report = parse_report("go", sample, "HIGH")
        self.assertTrue(report.unknown, "缺严重度发现必须进入报告而非被滤掉")

    def test_precheck_requires_go_markers(self) -> None:
        from codeguard.cve import precheck

        bare = Path(tempfile.mkdtemp(prefix="cg-nogo-"))
        ok, reason = precheck(bare, "go")
        self.assertFalse(ok)
        self.assertIn("go.mod", reason)
        (bare / "go.mod").write_text("module x\n", encoding="utf-8")
        ok, reason = precheck(bare, "go")
        self.assertTrue(ok, reason)


class PathsepAndDeadKnobTests(unittest.TestCase):
    def test_paths_uses_os_pathsep(self) -> None:
        text = (ROOT / "scripts" / "paths.py").read_text(encoding="utf-8")
        self.assertIn("os.pathsep", text)
        self.assertNotIn('":".join', text, "PATH 拼接必须用 os.pathsep，Windows 上 \":\" 是错的")
        self.assertNotIn('split(":")', text)

    def test_strict_mode_is_gone_everywhere_it_misled(self) -> None:
        from codeguard.config import load_user_config

        self.assertNotIn("strict_mode", load_user_config())
        for name in ("README.md", "README.zh-CN.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("strict_mode", text, f"{name} 不得再描述假旋钮")


if __name__ == "__main__":
    unittest.main()
