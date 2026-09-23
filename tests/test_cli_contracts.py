"""通过真实 Bash CLI 入口保护初始化、发现与修复结果汇总合同。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
CLI = PLUGIN / "bin" / "codeguard"


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "requires Bash and Git")
class CliContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-cli-contract-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                    "CODEGUARD_HOME": str(self.root / "state")}

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(CLI), *args], cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=30, check=False)

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, env=self.env,
                       capture_output=True, text=True, timeout=10, check=True)

    def test_init_only_prints_guidance_without_writing_project(self):
        completed = self.cli("init")

        self.assertEqual(0, completed.returncode)
        self.assertIn("项目初始化引导", completed.stderr)
        self.assertEqual([], list(self.root.iterdir()))

    def test_detect_returns_python_from_project_without_writing(self):
        source = self.root / "demo.py"
        marker = self.root / "pyproject.toml"
        source.write_text("print('ready')\n", encoding="utf-8")
        marker.write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8")

        completed = self.cli("detect", str(self.root))

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("python", json.loads(completed.stdout))
        self.assertEqual({source, marker}, set(self.root.iterdir()))

    def test_fix_reports_formatter_failure_after_same_language_skip(self):
        self.git("init", "--quiet")
        shell = self.root / "clean.sh"
        zsh = self.root / "skip.zsh"
        shell.write_text("echo first\n", encoding="utf-8")
        zsh.write_text("echo first\n", encoding="utf-8")
        self.git("add", "clean.sh", "skip.zsh")
        self.git("-c", "user.name=CodeGuard Test", "-c", "user.email=test@example.com",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "baseline")
        shell.write_text("echo second\n", encoding="utf-8")
        zsh.write_text("echo second\n", encoding="utf-8")

        tool_dir = self.root / "tool-bin"
        tool_dir.mkdir()
        formatter = tool_dir / "shfmt"
        formatter.write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            "from pathlib import Path\n"
            "Path('formatter-argv.json').write_text(json.dumps(sys.argv[1:]))\n"
            "print('formatter failed', file=sys.stderr)\n"
            "raise SystemExit(2)\n", encoding="utf-8")
        formatter.chmod(0o755)
        self.env["PATH"] = str(tool_dir) + os.pathsep + self.env["PATH"]

        completed = self.cli("fix", "--lang", "shell", str(self.root))

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("zsh 文件跳过 formatter", completed.stdout)
        self.assertIn("failed: exit=2", completed.stdout)
        argv = json.loads((self.root / "formatter-argv.json").read_text(encoding="utf-8"))
        self.assertIn("clean.sh", argv)
        self.assertNotIn("skip.zsh", argv)


if __name__ == "__main__":
    unittest.main()
