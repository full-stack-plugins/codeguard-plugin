#!/usr/bin/env python3
"""Unit tests for scripts/validate_languages_json.py.

These tests intentionally break the schema to verify each rule fires.
A passing validator still needs a passing registry fixture; that baseline
is the current scripts/languages.json (covered by test_clean_registry_passes).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_languages_json import check

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "scripts" / "languages.json"


def _baseline() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _mutate(reg: dict, lang_id: str, **patch) -> dict:
    """Return a deep-enough copy of reg with the matching entry patched."""
    import copy
    reg = copy.deepcopy(reg)
    for l in reg["languages"]:
        if l.get("id") == lang_id:
            for k, v in patch.items():
                l[k] = v
    return reg


class LanguagesJsonValidatorTest(unittest.TestCase):
    def test_clean_registry_passes(self) -> None:
        self.assertEqual([], check(_baseline()))

    def test_duplicate_id_fails(self) -> None:
        reg = _baseline()
        clone = {"id": "java", "name": "Java Clone", "extensions": [".java_clone"],
                 "markers": [], "status": "stable", "since": "V0.1"}
        reg["languages"].append(clone)
        errs = check(reg)
        self.assertTrue(any("duplicate id 'java'" in e for e in errs), errs)

    def test_invalid_status_fails(self) -> None:
        reg = _mutate(_baseline(), "python", status="draft")
        errs = check(reg)
        self.assertTrue(any("python:status" in e and "draft" in e for e in errs), errs)

    def test_extension_collision_fails(self) -> None:
        reg = _baseline()
        # Inject a synthetic stable language claiming .rs
        reg["languages"].append({
            "id": "rustish", "name": "Rustish", "extensions": [".rs"],
            "markers": [], "status": "stable", "since": "V0.1",
        })
        errs = check(reg)
        self.assertTrue(any("extensions" in e and ".rs" in e for e in errs), errs)

    def test_marker_collision_fails(self) -> None:
        reg = _mutate(_baseline(), "go", markers=["pom.xml"])
        errs = check(reg)
        self.assertTrue(any("markers" in e and "pom.xml" in e for e in errs), errs)

    def test_planned_with_lint_fails(self) -> None:
        # cobol is one of the planned entries; adding a lint violates rule
        reg = _mutate(_baseline(), "cobol", lint=["cobol-lint"], format=None)
        errs = check(reg)
        self.assertTrue(any("cobol:commands" in e and "planned" in e for e in errs), errs)

    def test_stable_with_no_lint_or_format_fails(self) -> None:
        reg = _mutate(_baseline(), "python", lint=None, format=None)
        errs = check(reg)
        self.assertTrue(any("python:commands" in e and "stable" in e for e in errs), errs)

    def test_requiresConfig_must_be_list_of_str(self) -> None:
        reg = _mutate(_baseline(), "python", requiresConfig="ruff.toml")
        errs = check(reg)
        self.assertTrue(any("python:requiresConfig" in e for e in errs), errs)

    def test_extensions_must_start_with_dot(self) -> None:
        reg = _mutate(_baseline(), "python", extensions=["py"])
        errs = check(reg)
        self.assertTrue(any("python:extensions" in e and "py" in e for e in errs), errs)

    def test_id_must_be_kebab_case(self) -> None:
        reg = _baseline()
        # Append a bogus id to exercise rule 8
        reg["languages"].append({
            "id": "Ruby_on_Rails", "name": "Rails", "extensions": [".rr"],
            "markers": [], "status": "stable", "since": "V0.1",
        })
        errs = check(reg)
        self.assertTrue(any("Ruby_on_Rails:id" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()

class LinterConfigFilesRuleTest(unittest.TestCase):
    def test_linter_config_files_must_be_list_of_str(self) -> None:
        reg = _mutate(_baseline(), "python", linter_config_files="ruff.toml")
        errs = check(reg)
        self.assertTrue(any("python:linter_config_files" in e for e in errs), errs)

    def test_linter_config_files_can_be_empty(self) -> None:
        reg = _mutate(_baseline(), "rust", linter_config_files=[])
        self.assertEqual([], check(reg))

class LinterConfigCoverageTest(unittest.TestCase):
    def test_linter_config_files_coverage(self) -> None:
        """stable/beta 中至少 25 条填了 linter_config_files（防重构清空）。"""
        reg = _baseline()
        n = sum(1 for l in reg["languages"]
                if l.get("status") in ("stable", "beta") and l.get("linter_config_files"))
        self.assertGreaterEqual(n, 25, f"only {n} stable/beta languages have linter_config_files")
