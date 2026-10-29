"""Classify the exact observed rustup failure without masking real diagnostics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from codeguard.verdict import FAIL, UNVERIFIED, lint_verdict

MISSING = ("error: 'cargo-clippy' is not installed for the toolchain "
           "'1.99.0-x86_64-unknown-linux-gnu'.\n"
           "help: run `rustup component add clippy` to install it\n")

class MissingClippyVerdict(unittest.TestCase):
    def test_observed_missing_component_is_unverified(self):
        self.assertEqual(lint_verdict(1, ['cargo', 'clippy'], MISSING)[0], UNVERIFIED)

    def test_absolute_cargo_path_crlf_and_final_newline(self):
        for text in [MISSING.replace('\n', '\r\n'), MISSING.rstrip('\n')]:
            with self.subTest(text=text):
                self.assertEqual(lint_verdict(1, ['/opt/rust/bin/cargo', 'clippy'], text)[0], UNVERIFIED)

    def test_real_clippy_finding_still_fails(self):
        self.assertEqual(lint_verdict(101, ['cargo', 'clippy'],
            'error: unneeded `return` statement\n --> src/main.rs:2:5\n')[0], FAIL)

    def test_mixed_diagnostics_are_not_masked(self):
        self.assertEqual(lint_verdict(1, ['cargo', 'clippy'],
            MISSING + 'error: real finding at src/main.rs:2:5\n')[0], FAIL)

    def test_other_tool_and_subcommand_are_not_reclassified(self):
        for cmd in [['ruff', 'check'], ['cargo', 'test']]:
            with self.subTest(cmd=cmd):
                self.assertEqual(lint_verdict(1, cmd, MISSING)[0], FAIL)

if __name__ == '__main__':
    unittest.main()
