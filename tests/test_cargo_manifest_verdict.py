"""Cargo manifest parse failures must not start automatic formatting."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from codeguard.verdict import FAIL, UNVERIFIED, lint_verdict
from codeguard.language_check import run_check
from codeguard.models import PlanExecution, ProcessResult

INVALID = 'error: key with no value, expected `=`\n --> Cargo.toml:1:9\n  |\n1 | invalid [\n  |         ^\n'

class CargoManifestVerdict(unittest.TestCase):
    def test_manifest_parse_error_is_unverified(self):
        for output in [INVALID, INVALID.replace('\n', '\r\n'), INVALID.rstrip('\n')]:
            self.assertEqual(lint_verdict(101, ['cargo', 'clippy'], output)[0], UNVERIFIED)

    def test_mixed_diagnostics_remain_fail(self):
        finding = 'error: unneeded return statement\n --> src/main.rs:2:5\n'
        for command in [['cargo', 'clippy'], ['cargo.exe', 'clippy'], ['/opt/rust/bin/cargo', 'clippy']]:
            for output in [finding, INVALID + finding, finding + INVALID]:
                self.assertEqual(lint_verdict(101, command, output)[0], FAIL)

    def test_source_location_or_other_command_is_not_manifest_failure(self):
        self.assertEqual(lint_verdict(101, ['cargo', 'clippy'], INVALID.replace('Cargo.toml', 'src/main.rs'))[0], FAIL)
        self.assertEqual(lint_verdict(101, ['cargo', 'test'], INVALID)[0], FAIL)

    def test_config_failure_does_not_launch_formatter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'Cargo.toml').write_text('invalid [')
            # Replay a captured tool failure at the process boundary; not native-tool coverage.
            with patch('codeguard.language_check.execute_plan') as process:
                process.return_value = PlanExecution((ProcessResult(('cargo', 'clippy'), root, 101, '', INVALID),))
                r = run_check(['rust'], root, fix=True)[0]
            self.assertEqual(r['status'], UNVERIFIED)
            self.assertEqual(r['stderr_tail'], INVALID)
            self.assertEqual([x['phase'] for x in r['execution_trace']], ['check'])
            self.assertEqual((root / 'Cargo.toml').read_text(), 'invalid [')

if __name__ == '__main__':
    unittest.main()
