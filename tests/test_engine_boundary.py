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
        self.assertIn("gap", RUST.note)


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
