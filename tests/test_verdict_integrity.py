"""判定可信度：检查真实内容和外部进程结果，禁止用假绿掩盖未验证。"""
from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PLUGIN / "scripts"), str(PLUGIN / "hooks")]
import cve_check
import gate_lib
import post_tool_lint
import pre_tool_git_guard
import run_check
import run_per_language
from detect_lang import LANG_COMMANDS

# auto_fix 用例需真实 ruff 执行 format/check——工具缺失时断言的修复路径无法覆盖。
RUFF_AVAILABLE = shutil.which("ruff") is not None


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cg-verdict-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", "/dev/null")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, text=True,
                              capture_output=True, check=True).stdout

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def checker(self):
        # 原生子进程只读文件，不依赖开发者是否安装 shellcheck。
        return {"lint": [sys.executable, "-c",
                         ("import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                         "bad='BAD' in p.read_text(); "
                         "print(str(p)+':1:1: bad' if bad else ''); sys.exit(int(bad))"),
                         "{file}"]}


class VerdictTests(RepoCase):
    def test_second_file_failure_is_not_hidden_by_first_pass(self):
        self.put("a.sh", "GOOD")
        self.put("b.sh", "BAD")
        with patch.dict(LANG_COMMANDS, {"shell": self.checker()}):
            failures, _ = gate_lib._run_gate_uncached(
                self.root, {}, ["shell"], scope="delta", changed=["a.sh", "b.sh"])
        self.assertEqual(len(failures), 1)
        self.assertIn("b.sh", failures[0][1])

    def test_tool_config_error_is_not_pass_and_survives_mcp(self):
        with patch.dict(LANG_COMMANDS, {"python": {
            "lint": [sys.executable, "-c", "import sys; sys.exit(2)"]}}):
            results = run_per_language.run_check(["python"], self.root)
        self.assertFalse(results[0]["passed"])
        self.assertEqual(results[0].get("status"), "UNVERIFIED")
        envelope = run_check._mcp_envelope(results)[0]
        self.assertEqual(envelope.get("status"), "UNVERIFIED")
        self.assertTrue(envelope.get("reason"))

    def test_cli_honors_linter_configuration_prerequisite(self):
        commands = {"lint": [sys.executable, "-c", "pass"], "requiresConfig": [".fixture-config"]}
        with patch.dict(LANG_COMMANDS, {"python": commands}):
            result = run_per_language.run_check(["python"], self.root)[0]
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_missing_tool_cli_is_nonzero_without_all_passed(self):
        self.put("sample.py", "x=1\n")
        with patch.dict(LANG_COMMANDS, {"python": {"lint": ["codeguard-no-such-linter"]}}), \
                patch.object(sys, "argv", ["run_check.py", "--quiet", "--lang", "python", str(self.root)]):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = run_check.cli_main()
        self.assertEqual(rc, 1)
        self.assertNotIn("all passed", out.getvalue())

    def test_project_command_flag_survives_registry_loading(self):
        self.assertIs(LANG_COMMANDS["java"].get("append_files"), False)

    def test_repo_check_uses_project_gate_not_empty_file_placeholder(self):
        command = {"lint": [sys.executable, "-c", "import sys;sys.exit(1)", "{file}"],
                   "gate": [sys.executable, "-c", "print('all files checked')"]}
        with patch.dict(LANG_COMMANDS, {"shell": command}):
            results = run_per_language.run_check(["shell"], self.root)
        self.assertTrue(results[0]["passed"])

    def test_partial_fix_does_not_run_project_formatter(self):
        marker = self.root / "formatter-ran"
        cmd = {"append_files": False, "format": [sys.executable, "-c",
                f"from pathlib import Path;Path({str(marker)!r}).touch()"]}
        with patch.dict(LANG_COMMANDS, {"java": cmd}):
            results = run_per_language.run_fix(["java"], self.root, files=["src/A.java"])
        self.assertFalse(marker.exists())
        self.assertFalse(results[0]["fixed"])

    def test_scoped_check_runs_each_placeholder_file(self):
        self.put("a.sh", "GOOD")
        self.put("b.sh", "BAD")
        with patch.dict(LANG_COMMANDS, {"shell": self.checker()}):
            result = run_per_language.run_check(["shell"], self.root, files=["a.sh", "b.sh"])[0]
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("b.sh", result["stdout_tail"])

    @unittest.skipUnless(RUFF_AVAILABLE, "ruff not installed (pip install ruff) — auto_fix 需真实 ruff")
    def test_mcp_auto_fix_never_touches_clean_files(self):
        self.put("clean.py", "import os\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.put("changed.py", "import sys\n")
        self.assertTrue(hasattr(run_check, "_auto_fix"))
        payload = run_check._auto_fix(self.root, ["python"])
        self.assertEqual((self.root / "clean.py").read_text(), "import os\n")
        self.assertTrue(payload["fixed"], payload)
        self.assertTrue(payload["check"][0]["passed"], payload)

    def test_scoped_fix_does_not_follow_symlink_to_clean_file(self):
        self.put("clean.py", "import os\n")
        (self.root / "link.py").symlink_to(self.root / "clean.py")
        outcome = run_per_language.run_fix(["python"], self.root, files=["link.py"])[0]
        self.assertEqual((self.root / "clean.py").read_text(), "import os\n")
        self.assertEqual(outcome.get("status"), "UNVERIFIED")

    def test_no_baseline_means_unchanged_caller_is_not_ignored(self):
        self.put("consumer.py", "removed_api()")
        self.assertIsNone(gate_lib._stale_attribution(
            "consumer.py:1:1: undefined name", self.root, "python", ["api.py"]))

    def test_post_tool_error_does_not_run_formatter(self):
        file = self.put("sample.py", "x=1\n")
        marker = self.root / "formatter-ran"
        commands = {"lint": [sys.executable, "-c", "import sys; sys.exit(2)"],
                    "format": [sys.executable, "-c",
                               f"from pathlib import Path; Path({str(marker)!r}).touch()"]}
        with patch.dict(LANG_COMMANDS, {"python": commands}), \
                patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(file)}), \
                patch.object(post_tool_lint, "find_project_root", return_value=self.root), \
                patch.object(post_tool_lint, "should_suppress_duplicate", return_value=False), \
                patch.object(post_tool_lint, "mac_notify"), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.root / "state")}), \
                contextlib.redirect_stdout(io.StringIO()):
            post_tool_lint.main()
        self.assertFalse(marker.exists())

    def test_post_tool_recheck_error_is_json_unverified_not_failure(self):
        file = self.put("sample.py", "x=1\n")
        out = io.StringIO()
        commands = {"lint": ["fixture-check"], "format": ["fixture-format"]}
        with patch.dict(LANG_COMMANDS, {"python": commands}), \
                patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(file)}), \
                patch.object(post_tool_lint, "find_project_root", return_value=self.root), \
                patch.object(post_tool_lint, "should_suppress_duplicate", return_value=False), \
                patch.object(post_tool_lint, "load_user_config", return_value={"auto_fix_on_save": True}), \
                patch.object(post_tool_lint, "run", side_effect=[(1, "F401", ""), (0, "", ""), (2, "", "config invalid")]), \
                patch.object(post_tool_lint, "bump_state") as bump, \
                patch.object(post_tool_lint, "mac_notify"), contextlib.redirect_stdout(out):
            post_tool_lint.main()
        payload = json.loads(out.getvalue())
        self.assertIn("UNVERIFIED", payload["hookSpecificOutput"]["additionalContext"])
        bump.assert_not_called()


class ContentTests(RepoCase):
    def test_add_update_does_not_include_untracked_files(self):
        lanes, _ = pre_tool_git_guard.staging_intent("git add -u && git commit -m t")
        self.assertNotIn("untracked", lanes)

    def test_scoped_add_all_keeps_directory_scope(self):
        with patch.object(Path, "cwd", return_value=self.root):
            lanes, extra = pre_tool_git_guard.staging_intent("git add -A src && git commit -m t")
        self.assertNotIn("untracked", lanes)
        self.assertIn("src", extra)

    def exact_gate(self, mode="commit", lanes=("staged",), extra=None):
        self.assertIn("exact", inspect.signature(gate_lib.run_gate).parameters,
                      "硬门禁必须能选择准确内容快照")
        with patch.dict(LANG_COMMANDS, {"shell": self.checker()}):
            return gate_lib.run_gate(self.root, {}, ["shell"], mode=mode,
                                     lanes=lanes, extra=extra, exact=True)

    def test_staged_bad_worktree_clean_checks_index_and_preserves_both(self):
        self.put("a.sh", "BAD")
        self.git("add", "a.sh")
        self.put("a.sh", "GOOD")
        before = self.git("diff", "--cached")
        failures, _ = self.exact_gate()
        self.assertTrue(failures)
        self.assertEqual(self.git("diff", "--cached"), before)
        self.assertEqual((self.root / "a.sh").read_text(), "GOOD")

    def test_predicted_add_uses_worktree_and_expands_directory(self):
        self.put("scripts/a.sh", "GOOD")
        self.git("add", ".")
        self.put("scripts/a.sh", "BAD")
        failures, _ = self.exact_gate(extra=["scripts"])
        self.assertTrue(failures)
        self.assertEqual(self.git("show", ":scripts/a.sh"), "GOOD")

    def test_push_uses_head_not_unstaged_repair(self):
        self.put("a.sh", "GOOD")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.put("a.sh", "BAD")
        self.git("add", ".")
        self.git("commit", "-qm", "bad")
        self.put("a.sh", "GOOD")
        failures, _ = self.exact_gate(mode="push")
        self.assertTrue(failures)

    def test_safety_sees_predicted_add_and_allows_removal(self):
        self.put(".env", "FAKE_DIAGNOSTIC=not-a-secret\n")
        self.assertIn("extra", inspect.signature(gate_lib.check_commit_safety).parameters)
        violations = gate_lib.check_commit_safety(self.root, "commit", extra=[".env"])
        self.assertEqual(violations[0][0], ".env")
        self.git("add", ".env")
        self.git("commit", "-qm", "fixture")
        self.git("rm", ".env")
        self.assertEqual(gate_lib.check_commit_safety(self.root, "commit"), [])

    def test_deleted_file_is_retained_for_impact_but_not_safety(self):
        from git_snapshot import validation_tree
        self.put("src/A.java", "class A {}")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("rm", "src/A.java")
        with validation_tree(self.root) as (snapshot, changed):
            self.assertIn("src/A.java", changed)
            self.assertFalse((snapshot / "src/A.java").exists())


class CveEvidenceTests(RepoCase):
    def test_bad_severity_is_usage_not_vulnerability(self):
        with patch.object(sys, "argv", ["cve_check.py", "--severity", "invalid"]), \
                contextlib.redirect_stderr(io.StringIO()), patch.object(cve_check, "run") as runner:
            try:
                code = cve_check.main()
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, 3)
        runner.assert_not_called()

    def invoke(self, rc, stdout, stderr, severity="HIGH"):
        self.put("package.json", "{}")
        with patch.object(cve_check, "run", return_value=(rc, stdout, stderr)), \
                patch.object(sys, "argv", ["cve_check.py", "--ecosystem", "node",
                                           "--severity", severity, str(self.root)]):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cve_check.main()
        return code, out.getvalue()

    def test_timeout_is_unverified_not_a_vulnerability(self):
        rc, out = self.invoke(124, "", "network timeout")
        self.assertEqual(rc, 1)
        self.assertNotIn("有漏洞需修复", out)

    def test_low_only_does_not_fail_high_threshold(self):
        rc, _ = self.invoke(1, json.dumps({"metadata": {"vulnerabilities": {
            "low": 1, "moderate": 0, "high": 0, "critical": 0}}}), "")
        self.assertEqual(rc, 0)

    def test_malformed_zero_exit_is_not_pass(self):
        rc, _ = self.invoke(0, "not JSON", "")
        self.assertEqual(rc, 1)

    def test_moderate_is_medium_threshold(self):
        rc, _ = self.invoke(1, json.dumps({"metadata": {"vulnerabilities": {
            "low": 0, "moderate": 1, "high": 0, "critical": 0}}}), "", "MEDIUM")
        self.assertEqual(rc, 2)

    def test_json_output_is_one_machine_readable_document(self):
        self.put("package.json", "{}")
        report = json.dumps({"metadata": {"vulnerabilities": {"high": 0}}})
        with patch.object(cve_check, "run", return_value=(0, report, "")), \
                patch.object(sys, "argv", ["cve_check.py", "--json", "--ecosystem", "node", str(self.root)]):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cve_check.main()
        self.assertEqual(rc, 0)
        try:
            data = json.loads(out.getvalue())
        except ValueError:
            self.fail("--json 输出混入普通日志")
        self.assertEqual(data["status"], "PASS")

    def test_maven_json_evidence_distinguishes_findings_and_network_errors(self):
        def fake(cmd, **kwargs):
            self.assertIn("org.owasp:dependency-check-maven:aggregate", cmd)
            output = Path(next(a.split("=", 1)[1] for a in cmd if a.startswith("-Dodc.outputDirectory=")))
            (output / "dependency-check-report.json").write_text(json.dumps({"dependencies": [
                {"vulnerabilities": [{"name": "CVE-2026-0000", "cvssv3": {"baseScore": 9.1}}]}]}))
            return 1, "threshold exceeded", ""
        # 只有具备结构化输出配置后才启动 fake，缺特性作为断言失败。
        with patch.object(cve_check, "run", return_value=(1, "network timeout", "")):
            unavailable = cve_check.scan_maven(self.root, 7)
        self.assertEqual(unavailable.get("status"), "UNVERIFIED")
        with patch.object(cve_check, "run", side_effect=fake):
            found = cve_check.scan_maven(self.root, 7)
        self.assertEqual(found["status"], "FAIL")

    def test_pip_report_is_scoped_to_project_requirements(self):
        self.put("requirements.txt", "example==1\n")
        report = json.dumps({"dependencies": [{"name": "example", "version": "1", "vulns": [{"id": "TEST-0001"}]}]})
        seen = []
        def scan(cmd, **kwargs):
            seen.append(cmd)
            return 1, report, ""
        with patch.object(cve_check, "run", side_effect=scan):
            result = cve_check.scan_pip(self.root)
        self.assertEqual(result.get("status"), "FAIL")
        self.assertIn("--requirement", seen[0])

    def test_cargo_json_failure_without_advisories_is_unverified(self):
        with patch.object(cve_check, "run", side_effect=[(0, "cargo-audit", ""), (1, "", "network error")]):
            result = cve_check.scan_cargo(self.root)
        self.assertEqual(result.get("status"), "UNVERIFIED")

    def test_cargo_json_advisory_is_not_lost(self):
        report = json.dumps({"vulnerabilities": {"found": True, "count": 1,
                            "list": [{"advisory": {"id": "RUSTSEC-TEST-0001"}}]}})
        with patch.object(cve_check, "run", side_effect=[(0, "cargo-audit", ""), (1, report, "")]):
            result = cve_check.scan_cargo(self.root)
        self.assertEqual(result.get("status"), "FAIL")


if __name__ == "__main__":
    unittest.main()
