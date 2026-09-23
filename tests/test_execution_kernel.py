"""跨入口的真实进程契约；防止工具故障被入口异常吞掉。

移除 UTF-8 容错、启动错误归一化或超时输出保留都会使本组失败。
不 mock subprocess；所有输入/输出由独立的短进程产生。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

import cve_check
import dockerfile_security
import post_tool_lint
import run_per_language
from verdict import UNVERIFIED, lint_verdict


class ExecutionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runners = (run_per_language._run, post_tool_lint.run, cve_check.run,
                        dockerfile_security.run)

    def test_nonzero_preserves_both_streams(self):
        argv = [sys.executable, "-c", "import sys; print('finding'); print('detail', file=sys.stderr); sys.exit(1)"]
        for run in self.runners:
            with self.subTest(entry=run.__module__):
                self.assertEqual((1, "finding\n", "detail\n"), run(argv, self.root, 5))

    def test_arguments_are_literal_and_cwd_is_explicit(self):
        literal = "a b; $(touch unexpected)"
        argv = [sys.executable, "-c", "import os,sys; print(sys.argv[1]); print(os.getcwd())", literal]
        for run in self.runners:
            with self.subTest(entry=run.__module__):
                rc, out, err = run(argv, self.root, 5)
                self.assertEqual(0, rc)
                self.assertEqual([literal, str(self.root.resolve())], out.splitlines())
                self.assertEqual("", err)
                self.assertFalse((self.root / "unexpected").exists())

    def test_invalid_utf8_does_not_discard_the_checker_result(self):
        argv = [sys.executable, "-c", "import os; os.write(1,b'detail \\xff'); os.write(2,b'error \\xfe'); raise SystemExit(1)"]
        for run in self.runners:
            with self.subTest(entry=run.__module__):
                rc, out, err = run(argv, self.root, 5)
                self.assertEqual((1, "detail \ufffd", "error \ufffd"), (rc, out, err))

    def test_timeout_keeps_partial_diagnostics(self):
        argv = [sys.executable, "-c", "import sys,time; print('before timeout',flush=True); print('stderr before timeout',file=sys.stderr,flush=True); time.sleep(30)"]
        for run in self.runners:
            with self.subTest(entry=run.__module__):
                rc, out, err = run(argv, self.root, 0.5)
                self.assertEqual(124, rc)
                self.assertIn("before timeout", out)
                self.assertIn("stderr before timeout", err)
                self.assertIn("timeout", err)
                self.assertEqual(UNVERIFIED, lint_verdict(rc, argv, out + err)[0])

    @unittest.skipIf(os.name == "nt", "POSIX executable permission contract")
    def test_non_executable_is_unverified_not_an_uncaught_error(self):
        tool = self.root / "not-executable"
        tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool.chmod(0o600)
        for run in self.runners:
            with self.subTest(entry=run.__module__):
                rc, out, err = run([str(tool)], self.root, 5)
                self.assertEqual(126, rc)
                self.assertTrue(err)
                self.assertEqual(UNVERIFIED, lint_verdict(rc, [str(tool)], out + err)[0])

    def test_missing_tool_is_unverified(self):
        argv = [str(self.root / "missing")]
        for run in self.runners:
            with self.subTest(entry=run.__module__):
                rc, out, err = run(argv, self.root, 5)
                self.assertEqual(127, rc)
                self.assertTrue(err)
                self.assertEqual(UNVERIFIED, lint_verdict(rc, argv, out + err)[0])

    def test_git_gate_preserves_finding_with_invalid_output_bytes(self):
        from unittest.mock import patch

        import gate_lib

        argv = [sys.executable, "-c", "import os; os.write(1,b'finding \\xff'); raise SystemExit(1)"]
        with patch.dict(gate_lib.LANG_COMMANDS, {"python": {"lint": argv}}), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.root / "state")}):
            failures, skipped = gate_lib._run_gate_uncached(self.root, {}, ["python"])
        self.assertEqual([], skipped)
        self.assertEqual(1, len(failures))
        self.assertIn("finding \ufffd", failures[0][1])

    def test_verdict_core_imports_without_host_or_legacy_runtime(self):
        # 隔离解释器只暴露 scripts，不需要 hooks、MCP SDK 或 pip 安装。
        code = (
            "import json,sys; sys.path.insert(0,sys.argv[1]); "
            "from codeguard.verdict import lint_verdict,exit_status,result; "
            "status,reason=lint_verdict(127,['missing']); "
            "print(json.dumps([status,exit_status([result('python',status,reason)]),"
            "any(n in sys.modules for n in ['gate_lib','run_check','detect_lang','mcp'])]))"
        )
        proc = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT / "scripts")],
                              capture_output=True, text=True, check=False, timeout=5)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual('["UNVERIFIED", 1, false]', proc.stdout.strip())

    def test_reporting_does_not_load_gate_or_launch_checks(self):
        code = (
            "import json,sys; sys.path.insert(0,sys.argv[1]); "
            "from codeguard.reporting import gate_directive; "
            "report=gate_directive([('python','F401 unused import','ruff check --fix sample.py','ruff')]); "
            "print(json.dumps([report.startswith('codeguard ❌'), 'F401' in report, "
            "'ruff check --fix sample.py' in report, "
            "any(n in sys.modules for n in ['gate_lib','run_check','detect_lang','subprocess'])]))"
        )
        proc = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT / "scripts")],
                              capture_output=True, text=True, check=False, timeout=5)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual('[true, true, true, false]', proc.stdout.strip())


if __name__ == "__main__":
    unittest.main()
