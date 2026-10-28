"""Exercise real launcher installation only inside disposable directories."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


PLUGIN = Path(__file__).resolve().parents[1]
CLI = PLUGIN / "bin" / "codeguard"


@unittest.skipUnless(shutil.which("bash") and os.name == "posix", "requires Bash and symlinks")
class InstallSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg install safety ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin_dir = self.root / "user bin"
        self.target = self.bin_dir / "codeguard"
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    def run_cli(self, *args, executable=CLI):
        return subprocess.run(["bash", str(executable), *args], cwd=self.root,
                              env=self.env, text=True, capture_output=True, timeout=15)

    def install(self, *args):
        result = self.run_cli("install", "--bin-dir", str(self.bin_dir), *args)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def assert_version(self, executable):
        result = self.run_cli("version", "--json", executable=executable)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual("codeguard.version", data["command"])
        self.assertEqual("allow", data["decision"])
        self.assertTrue(data["version"])

    def test_installed_launcher_works_after_repeated_install(self):
        self.install()
        self.assert_version(self.target)
        self.install()
        self.assert_version(self.target)

    def test_relative_link_chain_resolves_from_another_directory(self):
        self.install()
        links = self.root / "link directory"
        links.mkdir()
        first = links / "first"
        first.symlink_to(Path("..") / "user bin" / "codeguard")
        second = self.root / "second"
        second.symlink_to(Path("link directory") / "first")
        self.assert_version(second)

    def test_installed_command_runs_directly_from_path(self):
        self.install()
        result = subprocess.run(
            ["codeguard", "version", "--json"], cwd=self.root,
            env={**self.env, "PATH": str(self.bin_dir) + os.pathsep + self.env["PATH"]},
            text=True, capture_output=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("codeguard.version", json.loads(result.stdout)["command"])

    def test_install_dry_run_creates_nothing(self):
        data = self.install("--dry-run")
        self.assertTrue(data["dryRun"])
        self.assertEqual([], list(self.root.iterdir()))

    def test_uninstall_dry_run_preserves_link_then_real_uninstall_removes_only_link(self):
        self.install()
        before = os.readlink(self.target)
        result = self.run_cli("uninstall", "--bin-dir", str(self.bin_dir), "--dry-run")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(self.target.is_symlink(), result.stdout)
        self.assertEqual(before, os.readlink(self.target))
        self.assertTrue(json.loads(result.stdout)["dryRun"])
        result = self.run_cli("uninstall", "--bin-dir", str(self.bin_dir))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(self.target.is_symlink())
        self.assertTrue(CLI.is_file())

    def test_existing_file_is_preserved_by_install_and_uninstall(self):
        self.bin_dir.mkdir()
        self.target.write_text("user-owned content")
        for command in ("install", "uninstall"):
            result = self.run_cli(command, "--bin-dir", str(self.bin_dir))
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertEqual("deny", json.loads(result.stdout)["decision"])
            self.assertEqual("user-owned content", self.target.read_text())

    def test_foreign_and_dangling_symlinks_are_not_replaced_or_removed(self):
        self.bin_dir.mkdir()
        other = self.root / "other"
        other.write_text("owned elsewhere")
        for destination in (other, self.root / "missing"):
            self.target.symlink_to(destination)
            for command in ("install", "uninstall"):
                result = self.run_cli(command, "--bin-dir", str(self.bin_dir))
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertEqual(str(destination), os.readlink(self.target))
            self.target.unlink()
        self.assertEqual("owned elsewhere", other.read_text())

    def test_uninstall_missing_target_is_denied_without_creating_directories(self):
        result = self.run_cli("uninstall", "--bin-dir", str(self.bin_dir))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual("not_managed", json.loads(result.stdout)["error"])
        self.assertEqual([], list(self.root.iterdir()))
