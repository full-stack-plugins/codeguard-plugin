"""语言服务行为：配置不能静默失效，探活不能跨检查轮次复用旧结论。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import detect_lang
from user_config import load_project_overrides
from validate_languages_json import check


class LanguageServicesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_python(self, body: str, *, stdin: str = ""):
        return subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(SCRIPTS)!r})\n" + body],
            cwd=self.root, input=stdin, text=True, capture_output=True, timeout=15, check=False,
        )

    def test_failed_probe_is_retried_after_tool_recovers(self):
        probe = [sys.executable, "-c", ("from pathlib import Path; import sys; "
                 f"sys.exit(0 if Path({str(self.root / 'ready')!r}).exists() else 1)")]
        self.assertFalse(detect_lang.probe_toolchain({"probe": probe})[0])
        (self.root / "ready").touch()
        self.assertEqual((True, ""), detect_lang.probe_toolchain({"probe": probe}))

    def test_successful_probe_is_not_reused_in_later_check(self):
        marker = self.root / "ready"
        marker.touch()
        probe = [sys.executable, "-c", ("from pathlib import Path; import sys; "
                 f"sys.exit(0 if Path({str(marker)!r}).exists() else 1)")]
        self.assertTrue(detect_lang.probe_toolchain({"probe": probe})[0])
        marker.unlink()
        self.assertFalse(detect_lang.probe_toolchain({"probe": probe})[0])

    def test_probe_uses_each_callers_working_directory(self):
        other = self.root / "other"
        other.mkdir()
        (self.root / "ready").touch()
        result = self.run_python(
            "import os, detect_lang\n"
            "definition = {'probe': [sys.executable, '-c', "
            "\"from pathlib import Path; import sys; sys.exit(0 if Path('ready').exists() else 1)\"]}\n"
            "assert detect_lang.probe_toolchain(definition)[0]\n"
            "os.chdir('other')\n"
            "assert not detect_lang.probe_toolchain(definition)[0]\n"
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_invalid_probe_encoding_is_reported_without_crashing(self):
        result = self.run_python(
            "import detect_lang\n"
            "ok, reason = detect_lang.probe_toolchain({'probe': [sys.executable, '-c', "
            "\"import os; os.write(2, b'broken ' + bytes([255])); raise SystemExit(2)\"]})\n"
            "assert not ok and '2' in reason and 'broken' in reason, (ok, reason)\n"
        )
        self.assertEqual(0, result.returncode, result.stderr)

    @unittest.skipIf(os.name == "nt", "本夹具通过 POSIX shebang 启动；Windows 需独立运行验收")
    def test_implicit_binary_probe_does_not_consume_host_input(self):
        tool = self.root / "stdin-probe"
        tool.write_text(f"#!{sys.executable}\nimport sys\nassert sys.stdin.read() == ''\n")
        tool.chmod(0o755)
        result = self.run_python(
            "import detect_lang\n"
            f"ok, reason = detect_lang.probe_toolchain({{'lint': [{str(tool)!r}]}})\n"
            "assert ok, reason\nassert sys.stdin.read() == 'host payload'\n", stdin="host payload",
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_nested_markers_do_not_override_explicit_project_config(self):
        (self.root / "codeguard.json").write_text(json.dumps({"extensions": {".custom": "lua"}}))
        nested = self.root / "src" / "nested"
        nested.mkdir(parents=True)
        (nested / "pom.xml").touch()
        (nested / "demo.custom").touch()
        self.assertEqual(["lua"], detect_lang.detect_languages(self.root))

    def test_root_discovery_is_not_limited_to_ten_parents(self):
        (self.root / ".git").mkdir()
        nested = self.root.joinpath(*[f"d{n}" for n in range(15)])
        nested.mkdir(parents=True)
        self.assertEqual(self.root.resolve(), detect_lang.find_project_root(nested))

    def test_invalid_configuration_is_not_treated_as_defaults(self):
        for raw in ("{", "[]", '{"exclude": "vendor"}', '{"exclude": ["["]}',
                    '{"extensions": []}', '{"extensions": {".custom": "unknown-language"}}',
                    '{"gate_scope": "rep0"}'):
            with self.subTest(raw=raw):
                (self.root / "codeguard.json").write_text(raw)
                with self.assertRaisesRegex(ValueError, "codeguard.json"):
                    load_project_overrides(self.root)

    def test_invalid_configuration_cli_is_unverified_not_no_language(self):
        (self.root / ".git").mkdir()
        (self.root / "codeguard.json").write_text("{")
        result = subprocess.run([sys.executable, str(SCRIPTS / "run_check.py"), str(self.root)],
                                text=True, capture_output=True, timeout=15, check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("UNVERIFIED", result.stderr)
        self.assertIn("codeguard.json", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_registry_bad_shapes_return_diagnostics(self):
        base = json.loads((SCRIPTS / "languages.json").read_text())
        for bad in ([], {**base, "languages": {}},
                    {**base, "languages": [{"id": [], "status": []}]},
                    {**base, "languages": [None]}):
            with self.subTest(bad=bad):
                try:
                    errors = check(bad)
                except (AttributeError, TypeError) as exc:
                    self.fail(f"注册表非法形状必须产生诊断，而非崩溃: {exc}")
                self.assertTrue(errors)

    def test_batch_shares_probe_in_target_root_but_next_batch_rechecks(self):
        from codeguard.gate import run_batch

        # 探活与 lint 都在夹具根执行；计数文件证明真实进程运行次数。
        (self.root / "ready").touch()
        definition = {
            "probe": [sys.executable, "-c", ("from pathlib import Path; "
                      "assert Path('ready').exists(); "
                      "p=Path('probes'); p.write_text(p.read_text()+'x' if p.exists() else 'x')")],
            "lint": [sys.executable, "-c", "from pathlib import Path; assert Path('ready').exists()"],
            "append_files": False,
        }
        with patch.dict(detect_lang.LANG_COMMANDS, {"typescript": definition, "vue": definition}):
            self.assertEqual(([], []), run_batch(self.root, {}, ["typescript", "vue"]))
            self.assertEqual("x", (self.root / "probes").read_text())
            self.assertEqual(([], []), run_batch(self.root, {}, ["typescript", "vue"]))
            self.assertEqual("xx", (self.root / "probes").read_text())

    def test_bad_config_cannot_be_bypassed_by_explicit_language_or_fix(self):
        from run_per_language import run_check, run_fix

        (self.root / "codeguard.json").write_text("{")
        marker = self.root / "should-not-run"
        command = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"]
        with patch.dict(detect_lang.LANG_COMMANDS, {"python": {"lint": command, "format": command}}):
            for output in (run_check(["python"], self.root), run_fix(["python"], self.root)):
                self.assertEqual("UNVERIFIED", output[0]["status"])
                self.assertFalse(marker.exists())

    def test_soft_gate_reports_config_error_without_exception_or_pass(self):
        from codeguard.gate import run_gate

        (self.root / "codeguard.json").write_text("{")
        failures, notes = run_gate(self.root, {}, ["python"])
        self.assertFalse(failures)
        self.assertTrue(any("UNVERIFIED" in note and "codeguard.json" in note for note in notes))

    def test_runtime_registry_rejects_duplicates_before_building_maps(self):
        from codeguard.registry import load_registry

        data = json.loads((SCRIPTS / "languages.json").read_text())
        data["languages"].append(dict(data["languages"][0]))
        registry = self.root / "languages.json"
        registry.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            load_registry(registry)

    def test_explicit_probe_directory_does_not_change_host_cwd(self):
        before = Path.cwd()
        (self.root / "ready").touch()
        result = detect_lang.probe_toolchain({"probe": [sys.executable, "-c",
                    "from pathlib import Path; assert Path('ready').exists()"]}, project_root=self.root)
        self.assertEqual((True, ""), result)
        self.assertEqual(before, Path.cwd())

    def test_same_batch_failure_can_recover(self):
        from codeguard.toolchain import ToolchainProbe

        service = ToolchainProbe(self.root)
        definition = {"probe": [sys.executable, "-c", "from pathlib import Path; assert Path('ready').exists()"]}
        self.assertFalse(service.probe(definition)[0])
        (self.root / "ready").touch()
        self.assertTrue(service.probe(definition)[0])

    def test_different_tools_are_probed_concurrently(self):
        from concurrent.futures import ThreadPoolExecutor

        from codeguard.toolchain import ToolchainProbe

        service = ToolchainProbe(self.root)
        commands = []
        for own, other in (("a", "b"), ("b", "a")):
            body = ("from pathlib import Path\nimport time\n"
                    f"Path({own!r}).touch()\nlimit=time.monotonic()+2\n"
                    f"while not Path({other!r}).exists() and time.monotonic()<limit:\n    time.sleep(.01)\n"
                    f"assert Path({other!r}).exists(), 'other probe was serialized'\n")
            commands.append({"probe": [sys.executable, "-c", body]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(service.probe, commands))
        self.assertEqual([(True, ""), (True, "")], outcomes)

    def test_configuration_mapping_exclusions_and_reload_remain_supported(self):
        config = self.root / "codeguard.json"
        (self.root / "script.CUSTOM").touch()
        (self.root / "hidden.py").touch()
        config.write_text(json.dumps({"extensions": {".CUSTOM": "lua"}, "exclude": ["hidden[.]py$"],
                                      "java": {"commands": [["mvn", "test"]]}}))
        self.assertEqual(["lua"], detect_lang.detect_languages(self.root))
        config.write_text(json.dumps({"extensions": {".CUSTOM": "ruby"}}))
        self.assertEqual(["python", "ruby"], detect_lang.detect_languages(self.root))

    def test_malformed_registry_cli_reports_diagnostic_without_traceback(self):
        target = self.root / "languages.json"
        target.write_text('{"languages": [{"status": []}]}')
        result = subprocess.run([sys.executable, str(SCRIPTS / "validate_languages_json.py"),
                                 "--path", str(target)], check=False, capture_output=True, text=True, timeout=10)
        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR:", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
