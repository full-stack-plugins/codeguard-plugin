"""架构规则是可执行门禁：在临时源码树注入反向依赖与循环，必须被拒绝。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_architecture.py"


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-architecture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, path, source):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")

    def check(self, root=None):
        self.assertTrue(CHECKER.is_file(), "需要实际运行的架构门禁，而非文档约定")
        return subprocess.run([sys.executable, str(CHECKER), "--root", str(root or self.root)],
                              capture_output=True, text=True, timeout=10, check=False)

    def test_top_level_scripts_carry_declared_roles(self):
        """顶层脚本角色登记完整：compat-shim 带 Deprecated 通告，adapter 有用途声明。"""
        proc = self.check(ROOT)
        role_errors = [
            line for line in proc.stdout.splitlines()
            if any(tag in line for tag in ("SCRIPT_ROLES", "compat-shim", "ADAPTER_LAYERS", "unclassified top-level"))
        ]
        self.assertEqual([], role_errors, proc.stdout)

    def test_current_repository_obeys_declared_dependencies(self):
        result = self.check(ROOT)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_pure_model_cannot_import_runtime_even_inside_function(self):
        self.put("scripts/codeguard/models.py", "def hidden():\n    import subprocess\n")
        result = self.check()
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn("codeguard/models.py:2", result.stdout)
        self.assertIn("subprocess", result.stdout)

    def test_core_cannot_import_hook_or_optional_host_sdk(self):
        for target in ("gate_lib", "hooks.post_tool_lint", "mcp.server.fastmcp"):
            with self.subTest(target=target):
                self.put("scripts/codeguard/execution.py", f"import {target}\n")
                result = self.check()
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn(target, result.stdout)

    def test_relative_and_from_package_imports_are_resolved(self):
        self.put("scripts/codeguard/models.py", "from . import execution\n")
        self.put("scripts/codeguard/execution.py", "from codeguard import models\n")
        result = self.check()
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn("cycle", result.stdout)
        self.assertIn("codeguard.models", result.stdout)
        self.assertIn("codeguard.execution", result.stdout)

    def test_legacy_cycles_are_rejected_without_importing_project_code(self):
        self.put("scripts/first.py", "import second\nraise RuntimeError('must not execute')\n")
        self.put("scripts/second.py", "from first import value\n")
        result = self.check()
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn("cycle", result.stdout)
        self.assertNotIn("RuntimeError", result.stderr)

    def test_new_core_module_requires_explicit_dependency_policy(self):
        self.put("scripts/codeguard/unclassified.py", "import os\n")
        result = self.check()
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn("unclassified", result.stdout)

    def test_valid_internal_dependencies_and_stdlib_are_allowed(self):
        self.put("scripts/codeguard/models.py", "from dataclasses import dataclass\n")
        self.put("scripts/codeguard/execution.py", "from .models import ProcessResult\nimport subprocess\n")
        self.put("scripts/codeguard/planning.py", "from scope import scope_cmd\nfrom .models import CheckPlan\n")
        self.put("scripts/scope.py", "from pathlib import Path\n")
        self.put("hooks/gate_lib.py", "from codeguard.execution import execute\n")
        result = self.check()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_models_import_without_loading_runtime_or_host_modules(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                 "import codeguard.models;"
                                 "assert not any(m in sys.modules for m in "
                                 "('subprocess','gate_lib','detect_lang','mcp','codeguard.execution'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_language_discovery_import_does_not_load_process_or_host_services(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "from codeguard.discovery import detect_languages;"
                                  "assert not any(m in sys.modules for m in "
                                  "('subprocess','gate_lib','mcp','codeguard.execution','codeguard.toolchain'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_report_version_matches_installed_plugin_manifest(self):
        expected = json.loads((ROOT / ".zcode-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "from codeguard.reporting import CODEGUARD_VERSION;"
                                  "print(CODEGUARD_VERSION)"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected, result.stdout.strip())

    def test_session_application_import_does_not_load_hook_adapter(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "import codeguard.session_application;"
                                  "assert not any(m in sys.modules for m in "
                                  "('stop_summary','gate_lib','mcp'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_startup_application_import_does_not_load_hook_adapter(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "import codeguard.startup_application;"
                                  "assert not any(m in sys.modules for m in "
                                  "('env_check','gate_lib','mcp'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_prompt_application_import_does_not_load_hook_adapter(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "import codeguard.prompt_application;"
                                  "assert not any(m in sys.modules for m in "
                                  "('user_prompt_validator','gate_lib','mcp'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_git_guard_application_import_does_not_load_hook_adapter(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "import codeguard.git_guard_application;"
                                  "assert not any(m in sys.modules for m in "
                                  "('pre_tool_git_guard','gate_lib','mcp'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_save_application_import_does_not_load_hook_adapter(self):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 ("import sys;sys.path.insert(0,sys.argv[1]);"
                                  "import codeguard.save_application;"
                                  "assert not any(m in sys.modules for m in "
                                  "('post_tool_lint','gate_lib','mcp'))"),
                                 str(ROOT / "scripts")], capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
