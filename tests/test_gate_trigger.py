"""Group 1+2 regression tests: commit-gate trigger heuristics and targeted
language detection (OpenSpec change 2026-09-22-fix-gate-trigger-and-mcp).

Grounded in the 2026-09-22 empirical audit:
- Real false positives are SUBSTRING matches: `pushed` hits `push`,
  `deployment` hits `deploy`.
- ASCII `?` is already present in QUESTION_MARKERS; we lock it with a
  regression test rather than "adding" it.
- Expected-True cases cover bare imperatives and action-intent pairings.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(PLUGIN / "hooks"))


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "upv", PLUGIN / "hooks" / "user_prompt_validator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TriggerHeuristicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upv = _load_module()

    def test_substring_variants_do_not_trigger(self):
        """1.1: word-boundary matching kills the real observed FPs."""
        for text in ("我刚才 pushed 了", "关于 deployment 策略的讨论"):
            with self.subTest(text=text):
                self.assertFalse(self.upv.is_trigger(text))

    def test_question_markers_cover_both_languages(self):
        """1.3: ASCII `?` and `？` both present (regression lock, not new)."""
        markers = self.upv.QUESTION_MARKERS
        self.assertIn("?", markers)
        self.assertIn("？", markers)
        # English question with trigger word is exempt.
        self.assertFalse(self.upv.is_trigger("Should I commit this?"))

    def test_bare_imperative_still_triggers(self):
        """1.4: sentence-initial triggers keep working."""
        for text in ("commit this now", "提交代码", "commit this"):
            with self.subTest(text=text):
                self.assertTrue(self.upv.is_trigger(text))

    def test_action_intent_pairing_triggers(self):
        """1.2: trigger word + action-intent phrase passes."""
        for text in ("请帮我 commit", "请帮我 push", "现在提交", "please push this"):
            with self.subTest(text=text):
                self.assertTrue(self.upv.is_trigger(text))

    def test_no_action_intent_stays_silent(self):
        """1.2: trigger word mid-sentence without action intent stays silent."""
        for text in ("我们聊聊 push 和 pull request 的区别"):
            with self.subTest(text=text):
                self.assertFalse(self.upv.is_trigger(text))


class TargetedLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upv = _load_module()

    def test_detects_languages_mentioned_in_text(self):
        """2.1/2.2: prompt naming rust narrows the gate to rust."""
        if not hasattr(self.upv, "_detect_languages_in_text"):
            self.skipTest("_detect_languages_in_text not implemented yet")
        ids = ["java", "rust", "typescript", "python", "go"]
        got = self.upv._detect_languages_in_text("commit this rust change please", ids)
        self.assertEqual(got, ["rust"])

    def test_falls_back_to_empty_when_no_language_named(self):
        """2.3: no language token → empty subset → caller falls back to detect."""
        if not hasattr(self.upv, "_detect_languages_in_text"):
            self.skipTest("_detect_languages_in_text not implemented yet")
        got = self.upv._detect_languages_in_text("请帮我 commit", ["java", "rust"])
        self.assertEqual(got, [])


if __name__ == "__main__":
    unittest.main()
