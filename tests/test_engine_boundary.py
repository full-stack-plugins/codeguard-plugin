"""引擎边界契约：Rust 内核存在时也不得签发质量结论。"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

import engine_report
from codeguard.engine import (
    ENGINES,
    LEGACY,
    LEGACY_EXIT,
    RUST,
    RUST_EXIT,
    category_authority,
    resolve_authoritative,
    translate,
)


class EngineRegistryTests(unittest.TestCase):
    def test_both_engines_are_registered(self):
        self.assertEqual({"legacy", "rust"}, set(ENGINES))

    def test_rust_is_not_authoritative_while_it_returns_incomplete(self):
        """Rust 对所有质量路径固定返回 3，因此它不能是签发方。"""
        self.assertFalse(RUST.authoritative)
        self.assertTrue(LEGACY.authoritative)

    def test_rust_incomplete_exit_still_blocks(self):
        outcome = translate("rust", 3)
        self.assertEqual("INCOMPLETE", outcome.verdict)
        self.assertTrue(outcome.blocks)
        self.assertFalse(outcome.verdict == "PASS")


class ExitTranslationTests(unittest.TestCase):
    def test_legacy_two_is_a_failing_verdict(self):
        outcome = translate("legacy", 2)
        self.assertEqual("FAIL", outcome.verdict)
        self.assertTrue(outcome.blocks)

    def test_legacy_one_is_unverified_not_pass(self):
        outcome = translate("legacy", 1)
        self.assertEqual("UNVERIFIED", outcome.verdict)
        self.assertTrue(outcome.blocks)

    def test_rust_and_legacy_do_not_share_exit_code_meaning(self):
        """同一个退出码在两个引擎下含义不同，不能互相套用。"""
        self.assertNotEqual(LEGACY_EXIT[3], RUST_EXIT[3])
        self.assertEqual("UNVERIFIED", translate("legacy", 3).verdict)
        self.assertEqual("INCOMPLETE", translate("rust", 3).verdict)

    def test_unknown_exit_code_fails_closed(self):
        for engine in ("legacy", "rust"):
            outcome = translate(engine, 99)
            self.assertEqual("UNVERIFIED", outcome.verdict, engine)
            self.assertTrue(outcome.blocks, engine)

    def test_only_exit_zero_passes(self):
        for engine in ("legacy", "rust"):
            passing = [code for code, (verdict, _) in
                       (LEGACY_EXIT if engine == "legacy" else RUST_EXIT).items()
                       if verdict == "PASS" and not _blocks(engine, code)]
            self.assertEqual([0], passing, engine)


def _blocks(engine: str, code: int) -> bool:
    return translate(engine, code).blocks  # type: ignore[arg-type]


class AuthoritativeSelectionTests(unittest.TestCase):
    def test_rust_availability_does_not_change_the_signing_engine(self):
        self.assertIs(resolve_authoritative(rust_available=False), LEGACY)
        self.assertIs(resolve_authoritative(rust_available=True), LEGACY)

    def test_rust_presence_is_still_reported_for_operator_awareness(self):
        """存在性要能被调用方感知，但只作为提示，不改变权威性。"""
        self.assertTrue(RUST.authoritative is False)
        # 说明文字必须指向「内核自报」这一事实来源，而不是复述某个会过期的状态。
        self.assertIn("capability_inventory", RUST.note)


class EngineReportProbeTests(unittest.TestCase):
    """engine_report 必须在探测到 Rust 后仍把签发方留在 Legacy。"""

    RUST_VERSION_JSON = json.dumps({
        "schema_version": "0.1.0", "report_type": "version",
        "cli_version": "0.1.0", "target": "darwin-arm64",
        "build_identity": None, "check_protocol_major": 1,
        "rulepack_compatibility": "unverified",
    })

    def _stub(self, directory: Path, body: str) -> Path:
        stub = directory / "codeguard"
        stub.write_text(body, encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return stub

    def _with_path(self, directory: Path):
        original = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{directory}{os.pathsep}{original}"
        self.addCleanup(lambda: os.environ.__setitem__("PATH", original))

    def test_rust_stub_is_detected_but_does_not_take_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self._stub(directory, (
                "#!/usr/bin/env bash\n"
                f"cat <<'JSON'\n{self.RUST_VERSION_JSON}\nJSON\n"
                "exit 0\n"
            ))
            self._with_path(directory)
            report = engine_report.build_report()
        self.assertTrue(report["rust_component"]["available"])
        self.assertEqual("0.1.0", report["rust_component"]["cli_version"])
        self.assertEqual("legacy", report["authoritative_engine"])

    def test_legacy_shaped_codeguard_is_not_mistaken_for_rust(self):
        """Legacy 没有 --version（未知子命令退出 1），不能被判成 Rust。"""
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self._stub(directory, "#!/usr/bin/env bash\necho '未知子命令' >&2\nexit 1\n")
            self._with_path(directory)
            report = engine_report.build_report()
        self.assertFalse(report["rust_component"]["available"])
        self.assertEqual("legacy", report["authoritative_engine"])

    def test_json_output_reports_engines_and_rust_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self._stub(directory, (
                "#!/usr/bin/env bash\n"
                f"cat <<'JSON'\n{self.RUST_VERSION_JSON}\nJSON\n"
                "exit 0\n"
            ))
            self._with_path(directory)
            report = engine_report.build_report()
        payload = json.loads(json.dumps(report, ensure_ascii=False))
        self.assertEqual("engine", payload["report_type"])
        self.assertEqual({"legacy", "rust"},
                         {entry["id"] for entry in payload["engines"]})
        # 显式断言：Rust 存在但非签发方，这是本模块存在的唯一理由。
        rust = next(e for e in payload["engines"] if e["id"] == "rust")
        self.assertFalse(rust["authoritative"])
        self.assertEqual("legacy", payload["authoritative_engine"])


if __name__ == "__main__":
    unittest.main()


class CapabilityDerivedAuthorityTests(unittest.TestCase):
    """权威性必须由内核自报状态推导，而不是插件写死。"""

    def _inventory(self, status: str) -> dict:
        return {
            "schema_version": "0.2.0",
            "report_type": "capability_inventory",
            "release_version": "0.1.0",
            "languages": [
                {
                    "language": "java",
                    "legacy_status": "stable",
                    "legacy_lint_declared": True,
                    "legacy_formatter_declared": False,
                    "platforms": {
                        "linux_x86_64": {
                            "lint": {"status": status, "reason": "observed"},
                        }
                    },
                }
            ],
        }

    def _auth(self, inventory, **kw):
        args = {"language": "java", "platform": "linux_x86_64", "category": "lint"}
        args.update(kw)
        return category_authority(inventory, **args)

    def test_gap_keeps_legacy_as_signing_engine(self):
        result = self._auth(self._inventory("gap"))
        self.assertEqual("legacy", result.engine)
        self.assertEqual("gap", result.status)

    def test_implemented_hands_over_that_category_to_rust(self):
        result = self._auth(self._inventory("implemented"))
        self.assertEqual("rust", result.engine)
        self.assertEqual("implemented", result.status)

    def test_not_applicable_does_not_hand_over(self):
        result = self._auth(self._inventory("not_applicable"))
        self.assertEqual("legacy", result.engine)

    def test_unreadable_inventory_fails_closed_to_legacy(self):
        for bad in (None, {}, {"report_type": "something_else"}, [], "nonsense"):
            result = self._auth(bad)
            self.assertEqual("legacy", result.engine, repr(bad))
            self.assertIsNone(result.status, repr(bad))

    def test_missing_cell_is_treated_as_unproven(self):
        inventory = self._inventory("implemented")
        result = self._auth(inventory, category="cve")
        self.assertEqual("legacy", result.engine)
        self.assertIn("无该单元", result.reason)

    def test_flat_cells_shape_is_also_understood(self):
        """带 --platform/--category 过滤时内核输出扁平 cells，需同样解析。"""
        inventory = {
            "schema_version": "0.2.0",
            "report_type": "capability_inventory",
            "release_version": "0.1.0",
            "cells": [
                {"language": "java", "platform": "linux_x86_64",
                 "category": "lint", "status": "implemented", "reason": "observed"},
                {"language": "java", "platform": "linux_x86_64",
                 "category": "cve", "status": "gap", "reason": "not implemented"},
            ],
        }
        self.assertEqual("rust", self._auth(inventory, category="lint").engine)
        self.assertEqual("legacy", self._auth(inventory, category="cve").engine)

    def test_summary_counts_implemented_and_gap(self):
        inventory = {
            "schema_version": "0.2.0",
            "report_type": "capability_inventory",
            "release_version": "0.1.0",
            "cells": [
                {"language": "java", "platform": "p", "category": "lint", "status": "implemented"},
                {"language": "java", "platform": "p", "category": "cve", "status": "gap"},
                {"language": "go", "platform": "p", "category": "lint", "status": "gap"},
            ],
        }
        summary = engine_report.summarize_inventory(inventory)
        self.assertTrue(summary["readable"])
        self.assertEqual(1, summary["implemented"])
        self.assertEqual(2, summary["gap"])

    def test_zero_implemented_keeps_global_signing_engine_on_legacy(self):
        """即使检测到内核，只要没有类别自报实现，全局兜底仍是 Legacy。"""
        self.assertIs(resolve_authoritative(rust_available=True), LEGACY)
