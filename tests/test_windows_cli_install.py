"""File-safety contracts are simulated; cmd.exe execution requires real Windows."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
import install_cli


class WindowsInstallFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-win-install-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin_dir = self.root / "user bin"
        self.target = self.bin_dir / "codeguard.cmd"

    def invoke(self, command, *args):
        output = io.StringIO()
        with patch.object(install_cli.sys, "platform", "win32"), contextlib.redirect_stdout(output):
            code = install_cli.main([command, "--bin-dir", str(self.bin_dir), *args])
        return code, json.loads(output.getvalue())

    def test_windows_install_never_requires_symlink_and_is_repeatable(self):
        with patch.object(install_cli.os, "symlink", side_effect=AssertionError("symlink privilege required")):
            code, response = self.invoke("install")
            self.assertEqual(0, code, response)
            self.assertTrue(self.target.is_file())
            self.assertFalse(self.target.is_symlink())
            before = self.target.read_bytes()
            code, response = self.invoke("install")
            self.assertEqual(0, code, response)
            self.assertEqual(before, self.target.read_bytes())

    def test_windows_dry_runs_and_owned_uninstall(self):
        code, response = self.invoke("install", "--dry-run")
        self.assertEqual(0, code, response)
        self.assertEqual([], list(self.root.iterdir()))
        self.assertEqual(0, self.invoke("install")[0])
        self.assertTrue(self.target.is_file())
        before = self.target.read_bytes()
        code, response = self.invoke("uninstall", "--dry-run")
        self.assertEqual(0, code, response)
        self.assertEqual(before, self.target.read_bytes())
        self.assertEqual(0, self.invoke("uninstall")[0])
        self.assertFalse(self.target.exists())

    def test_foreign_and_modified_launchers_are_preserved(self):
        self.bin_dir.mkdir()
        for content in (b"user-owned script", b"@echo off\nrem codeguard-managed\n"):
            self.target.write_bytes(content)
            for command in ("install", "upgrade", "uninstall"):
                code, response = self.invoke(command)
                self.assertEqual(1, code, response)
                self.assertEqual(content, self.target.read_bytes())

    def test_batch_metacharacter_paths_fail_before_writes(self):
        for special in ('%', '!', '&', '^', '\n', '\r', '"', '<', '>', '|', '(', ')'):
            with self.subTest(special=special):
                self.bin_dir = self.root / ("unsafe" + special + "bin")
                code, response = self.invoke("install")
                self.assertEqual(2, code, response)
                self.assertEqual("error", response["decision"])
                self.assertEqual([], list(self.root.iterdir()))

    def test_unsafe_interpreter_path_fails_before_writes(self):
        with patch.object(install_cli.sys, "executable", str(self.root / "python%PATH%.exe")):
            code, response = self.invoke("install")
        self.assertEqual(2, code, response)
        self.assertEqual([], list(self.root.iterdir()))

    def test_non_ascii_batch_paths_are_explicitly_unsupported(self):
        self.bin_dir = self.root / "用户目录"
        code, response = self.invoke("install")
        self.assertEqual(2, code, response)
        self.assertEqual([], list(self.root.iterdir()))


class PythonLauncherTests(unittest.TestCase):
    def test_python_entry_preserves_version_and_unknown_command_exit(self):
        for args, expected in [(["version", "--json"], 0), (["unknown-command"], 1)]:
            result = subprocess.run([sys.executable, str(PLUGIN / "scripts/cli_entry.py"), *args],
                                    capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(expected, result.returncode, result.stderr)
            if expected == 0:
                self.assertEqual("codeguard.version", json.loads(result.stdout)["command"])

    def test_all_legacy_routes_preserve_arguments_and_exit_status(self):
        # Real subprocesses run the dispatcher with recording stand-ins for its
        # script callees; these assert routing only, not checker qualification.
        routes = {
            "java-plan": "java_project.py", "check": "run_check.py", "fix": "fix.py",
            "cve": "cve_check.py", "dockerfile": "dockerfile_security.py",
            "engine": "engine_report.py", "explain": "explain_cli.py",
        }
        lifecycle = ("init", "version", "discover", "doctor", "status", "report",
                     "hooks", "impact", "install", "uninstall", "upgrade", "completion")
        with tempfile.TemporaryDirectory(prefix="cg-dispatch-") as temporary:
            root = Path(temporary)
            entry = root / "cli_entry.py"
            entry.write_bytes((PLUGIN / "scripts/cli_entry.py").read_bytes())
            fixture = ("import json, sys\nfrom pathlib import Path\n"
                       "print(json.dumps([Path(__file__).name, sys.argv[1:]]))\n"
                       "raise SystemExit(7)\n")
            for name in {*routes.values(), "guard_cli.py", "detect_lang.py"}:
                (root / name).write_text(fixture)
            literal = ["--json", "space argument", "% ! & ^", "--unknown"]
            cases = [(command, literal, script, literal) for command, script in routes.items()]
            cases.extend((command, literal, "guard_cli.py", [command, *literal]) for command in lifecycle)
            cases.extend([("detect", [], "detect_lang.py", ["."]),
                          ("detect", [""], "detect_lang.py", ["."]),
                          ("detect", ["a b", "ignored"], "detect_lang.py", ["a b"])])
            for command, args, script, expected in cases:
                with self.subTest(command=command, args=args):
                    result = subprocess.run([sys.executable, str(entry), command, *args],
                                            capture_output=True, text=True, timeout=15, check=False)
                    self.assertEqual(7, result.returncode, result.stderr)
                    self.assertEqual([script, expected], json.loads(result.stdout))
            default = subprocess.run([sys.executable, str(entry)], capture_output=True,
                                     text=True, timeout=15, check=False)
            self.assertEqual(7, default.returncode, default.stderr)
            self.assertEqual(["run_check.py", []], json.loads(default.stdout))


@unittest.skipUnless(os.name == "nt", "requires actual Windows cmd.exe")
class WindowsCommandExecutionTests(unittest.TestCase):
    def test_installed_cmd_executes_without_bash(self):
        with tempfile.TemporaryDirectory(prefix="cg cmd actual ") as temporary:
            args = [sys.executable, str(PLUGIN / "scripts/cli_entry.py"), "install", "--bin-dir", temporary]
            installed = subprocess.run(args, text=True, capture_output=True, timeout=15, check=False)
            self.assertEqual(0, installed.returncode, installed.stderr)
            command = str(Path(temporary) / "codeguard.cmd")
            for suffix, expected in [(["version", "--json"], 0), (["unknown-command"], 1)]:
                result = subprocess.run([command, *suffix], text=True, capture_output=True,
                                        timeout=15, check=False)
                self.assertEqual(expected, result.returncode, result.stderr)
                if expected == 0:
                    self.assertEqual("codeguard.version", json.loads(result.stdout)["command"])
            project = Path(temporary) / "project space % ! & ^"
            project.mkdir()
            result = subprocess.run([command, "report", "--json", str(project)], text=True,
                                    capture_output=True, timeout=15, check=False)
            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertEqual(str(project.resolve()), json.loads(result.stdout)["project"]["root"])
