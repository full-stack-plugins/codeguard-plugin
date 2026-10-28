"""Real Ruff regression: project configuration cannot be masked by defaults."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import scope

RUFF = os.environ.get('CODEGUARD_TEST_RUFF') or shutil.which('ruff')


class RuffConfigDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='codeguard ruff config ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'pyproject.toml'

    def test_valid_nested_and_inline_tables_belong_to_project(self):
        for value in ('[tool.ruff.lint]\nselect=["T201"]\n',
                      '[tool]\nruff = {lint = {select = ["T201"]}}\n',
                      '["tool"."ruff"."lint"]\nselect=["T201"]\n'):
            with self.subTest(value=value):
                self.config.write_text(value, encoding='utf-8')
                self.assertEqual(scope.ruff_config_args(['ruff', 'check', '.'], self.root), [])

    def test_commented_ruff_header_does_not_disable_default(self):
        self.config.write_text('# [tool.ruff]\n[project]\nname="demo"\n', encoding='utf-8')
        self.assertIn('--config', scope.ruff_config_args(['ruff', 'check', '.'], self.root))

    def test_read_failure_never_substitutes_default(self):
        self.config.write_text('[tool.ruff.lint]\nselect=["T201"]\n', encoding='utf-8')
        with patch.object(Path, 'read_text', side_effect=PermissionError('unreadable project config')):
            self.assertEqual(scope.ruff_config_args(['ruff', 'check', '.'], self.root), [])

    @unittest.skipUnless(RUFF, 'requires real Ruff; set CODEGUARD_TEST_RUFF or PATH')
    def test_real_nested_rule_is_enforced(self):
        self.config.write_text('[tool.ruff.lint]\nselect=["T201"]\n', encoding='utf-8')
        result = self.ruff()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('T201', result.stdout)

    @unittest.skipUnless(RUFF, 'requires real Ruff; set CODEGUARD_TEST_RUFF or PATH')
    def test_real_malformed_toml_is_an_error_not_pass(self):
        self.config.write_text('[tool.ruff\n', encoding='utf-8')
        result = self.ruff()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('pyproject.toml', result.stderr)

    @unittest.skipUnless(RUFF, 'requires real Ruff; set CODEGUARD_TEST_RUFF or PATH')
    def test_real_invalid_utf8_is_an_error_not_pass(self):
        self.config.write_bytes(b'[tool.ruff.lint]\nselect=["T201"]\n\xff')
        result = self.ruff()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('pyproject.toml', result.stderr)

    @unittest.skipUnless(RUFF and os.name == 'posix' and os.geteuid() != 0,
                         'requires real Ruff and enforceable POSIX file permissions')
    def test_real_unreadable_project_config_is_an_error_not_pass(self):
        self.config.write_text('[tool.ruff.lint]\nselect=["T201"]\n', encoding='utf-8')
        self.config.chmod(0)
        try:
            result = self.ruff()
        finally:
            self.config.chmod(0o600)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('pyproject.toml', result.stderr)

    def ruff(self):
        (self.root / 'main.py').write_text('print("hello")\n', encoding='utf-8')
        args = scope.ruff_config_args(['ruff', 'check', 'main.py'], self.root)
        return subprocess.run([RUFF, 'check', 'main.py', *args], cwd=self.root,
                              capture_output=True, text=True, encoding='utf-8', timeout=10, check=False)


class MissingTomlParserContractTests(unittest.TestCase):
    """Fault injection verifies error translation, not actual Python 3.10 execution."""
    def setUp(self):
        RuffConfigDiscoveryTests.setUp(self)
        self.config.write_text('[project]\nname="demo"\n', encoding='utf-8')
        (self.root / 'main.py').write_text('print("hello")\n', encoding='utf-8')

    def test_missing_parser_is_configuration_error_not_default(self):
        from codeguard.config import ConfigurationError
        with patch.dict(sys.modules, {'tomllib': None, 'tomli': None}), self.assertRaises(ConfigurationError):
            scope.ruff_config_args(['ruff', 'check', '.'], self.root)

    def test_check_and_fix_translate_missing_parser_without_execution(self):
        from codeguard import language_check
        with patch.dict(sys.modules, {'tomllib': None, 'tomli': None}), \
                patch.object(language_check, 'execute_plan') as execute:
            checked = language_check.run_check(['python'], self.root)[0]
            fixed = language_check.run_fix(['python'], self.root)[0]
        self.assertEqual(checked['status'], 'UNVERIFIED')
        self.assertEqual(fixed['status'], 'UNVERIFIED')
        self.assertNotEqual(checked['exit_code'], 0)
        self.assertNotEqual(fixed['exit_code'], 0)
        execute.assert_not_called()

    def test_gate_translates_missing_parser_without_execution(self):
        from unittest.mock import Mock

        from codeguard import gate_checks
        probe = Mock()
        probe.probe.return_value = (True, '')
        with patch.dict(sys.modules, {'tomllib': None, 'tomli': None}), \
                patch.object(gate_checks, 'execute') as execute:
            outcome = gate_checks.check_language(self.root, {}, 'python', scope='repo',
                                                  changed=None, baseline_ref='HEAD', probe=probe)
        self.assertIn('UNVERIFIED', ' '.join(outcome.notes))
        execute.assert_not_called()

    def test_save_lint_translates_missing_parser_without_execution_or_completion(self):
        from codeguard import save_application
        with patch.dict(sys.modules, {'tomllib': None, 'tomli': None}), \
                patch.object(save_application, 'run') as execute, \
                patch.object(save_application, 'bump_state') as bump:
            result = save_application.evaluate_save(str(self.root / 'main.py'), self.root, {})
            result.acknowledge()
        self.assertIn('UNVERIFIED', result.additional_context)
        execute.assert_not_called()
        bump.assert_not_called()

    def test_save_fix_configuration_failure_never_formats_or_records_completion(self):
        from codeguard import save_application
        from codeguard.config import ConfigurationError
        from codeguard.planning import scoped_plan
        plan = scoped_plan(['ruff', 'check', '{file}'], self.root, scope='save',
                           files=[str(self.root / 'main.py')])
        with patch.object(save_application, 'scoped_plan', side_effect=[plan, ConfigurationError('parser unavailable')]), \
                patch.object(save_application, 'check_identity', return_value=None), \
                patch.object(save_application, '_porcelain', return_value=set()), \
                patch.object(save_application, 'run', return_value=(1, 'T201 print found', '')) as execute, \
                patch.object(save_application, 'bump_state') as bump:
            result = save_application.evaluate_save(str(self.root / 'main.py'), self.root, {'auto_fix_on_save': True})
            result.acknowledge()
        self.assertIn('UNVERIFIED', result.additional_context)
        self.assertEqual(execute.call_count, 1)
        bump.assert_not_called()

    def test_cli_check_and_fix_missing_parser_are_nonzero_without_traceback(self):
        code = ("import runpy,sys; sys.modules['tomllib']=None; sys.modules['tomli']=None; "
                "script=sys.argv[1]; sys.argv=sys.argv[1:]; runpy.run_path(script,run_name='__main__')")
        before = (self.root / 'main.py').read_bytes()
        for script, options in (('run_check.py', ['--quiet']), ('fix.py', ['--all'])):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'scripts' / script),
                                         '--lang', 'python', *options, str(self.root)],
                                        capture_output=True, text=True, encoding='utf-8', timeout=10, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('UNVERIFIED', result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stdout + result.stderr)
                self.assertEqual((self.root / 'main.py').read_bytes(), before)
