"""离线真实进程：Dockerfile 检查不能吞掉失败或扩大单文件范围。"""
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
sys.path.insert(0, str(ROOT / "scripts"))
import dockerfile_security

TOOL = '''import json, sys
from pathlib import Path
root = Path.cwd()
name = Path(sys.argv[0]).name
config = json.loads((root / "fixture.json").read_text())[name]
result = config.get("by_file", {}).get(Path(sys.argv[-1]).name, config)
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps({"tool": name, "argv": sys.argv[1:]}) + "\\n")
print(result.get("text", json.dumps(result.get("report"))))
print(result.get("stderr", ""), file=sys.stderr)
sys.exit(result.get("rc", 0))
'''


def clean_trivy():
    return {"Results": [{"Target": "Dockerfile", "Class": "config", "Type": "dockerfile",
                         "MisconfSummary": {"Successes": 1, "Failures": 0, "Exceptions": 0}}]}


def hadolint_finding():
    return {"file": "Dockerfile", "line": 1, "column": 1, "level": "warning",
            "code": "DL3007", "message": "pin image version"}


def trivy_finding():
    return {"ID": "DS002", "Title": "root user", "Severity": "HIGH", "Status": "FAIL",
            "Message": "root user", "Resolution": "use non-root user"}


class DockerfileBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-dockerfile-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.file = self.root / "Dockerfile"
        self.file.write_text("FROM scratch\n")
        tools = self.root / "bin"
        tools.mkdir()
        for name in ("hadolint", "trivy"):
            tool = tools / name
            tool.write_text(f"#!{sys.executable}\n" + TOOL)
            tool.chmod(0o755)
        env = patch.dict(os.environ, {"PATH": str(tools) + os.pathsep + os.environ["PATH"]})
        env.start()
        self.addCleanup(env.stop)
        self.configure()

    def configure(self, hadolint=None, trivy=None):
        data = {"hadolint": {"report": [], "rc": 0} if hadolint is None else hadolint,
                "trivy": {"report": clean_trivy(), "rc": 0} if trivy is None else trivy}
        (self.root / "fixture.json").write_text(json.dumps(data))

    def invoke(self, path=None, as_json=True):
        return subprocess.run([sys.executable, str(ROOT / "scripts/dockerfile_security.py"),
                               *(["--json"] if as_json else []), str(path or self.root)],
                              cwd=self.root, capture_output=True, text=True, timeout=10, check=False)

    def assert_verdict(self, expected, code):
        machine = self.invoke()
        text = self.invoke(as_json=False)
        self.assertEqual(code, machine.returncode, machine.stdout + machine.stderr)
        self.assertEqual(code, text.returncode, text.stdout + text.stderr)
        self.assertEqual(expected, json.loads(machine.stdout).get("status"))
        if expected != "PASS":
            self.assertNotIn("安全检查通过", text.stdout)

    def test_tool_failures_are_not_pass_or_findings(self):
        for tool in ("hadolint", "trivy"):
            for rc in (124, 126, 127, 3):
                with self.subTest(tool=tool, rc=rc):
                    self.configure(**{tool: {"rc": rc, "text": "", "stderr": "tool failed"}})
                    self.assert_verdict("UNVERIFIED", 1)

    def test_malformed_trivy_report_never_becomes_zero_findings(self):
        for report in ({}, [], None, {"Results": {}}, {"Results": [None]}, {"Results": []}):
            with self.subTest(report=report):
                self.configure(trivy={"report": report})
                self.assert_verdict("UNVERIFIED", 1)

    def test_hadolint_requires_valid_report_even_at_exit_zero(self):
        for text in ("", "network failure", "{}", '[{"message":"incomplete"}]'):
            with self.subTest(text=text):
                self.configure(hadolint={"text": text})
                self.assert_verdict("UNVERIFIED", 1)

    def test_clean_reports_pass_both_modes(self):
        self.assert_verdict("PASS", 0)

    def test_hadolint_json_findings_keep_legacy_text_and_process_exit(self):
        self.configure(hadolint={"rc": 1, "report": [hadolint_finding()]})
        self.assert_verdict("FAIL", 2)
        data = json.loads(self.invoke().stdout)["hadolint"]
        self.assertIsInstance(data["findings"][0], str)
        self.assertIn("DL3007", data["findings"][0])
        self.assertEqual(1, data["attempts"][0]["exit"])

    def test_trivy_findings_are_distinct_from_process_error(self):
        report = clean_trivy()
        report["Results"][0]["MisconfSummary"] = {"Successes": 0, "Failures": 1, "Exceptions": 0}
        report["Results"][0]["Misconfigurations"] = [trivy_finding()]
        self.configure(trivy={"rc": 2, "report": report})
        self.assert_verdict("FAIL", 2)
        data = json.loads(self.invoke().stdout)["trivy"]
        self.assertEqual("DS002", data["findings"][0]["id"])
        self.assertEqual(2, data["attempts"][0]["exit"])
        self.configure(trivy={"rc": 124, "report": report})
        self.assert_verdict("UNVERIFIED", 1)

    def test_trivy_invalid_finding_or_summary_cannot_pass(self):
        for finding in ({"Status": "FAIL"}, {"ID": "DS002", "Status": "BOGUS"}):
            with self.subTest(finding=finding):
                report = clean_trivy()
                report["Results"][0]["Misconfigurations"] = [finding]
                self.configure(trivy={"rc": 0, "report": report})
                self.assert_verdict("UNVERIFIED", 1)
        report = clean_trivy()
        report["Results"][0]["MisconfSummary"]["Failures"] = 2
        self.configure(trivy={"rc": 0, "report": report})
        self.assert_verdict("UNVERIFIED", 1)

    def test_nonzero_without_finding_is_unverified(self):
        self.configure(hadolint={"rc": 1, "report": []})
        self.assert_verdict("UNVERIFIED", 1)
        self.configure(trivy={"rc": 2, "report": clean_trivy()})
        self.assert_verdict("UNVERIFIED", 1)

    def test_missing_tool_keeps_existing_findings_visible(self):
        self.configure(hadolint={"rc": 1, "report": [hadolint_finding()]}, trivy={"rc": 127, "text": ""})
        self.assert_verdict("UNVERIFIED", 1)
        self.assertTrue(json.loads(self.invoke().stdout)["hadolint"]["findings"])

    def test_explicit_file_does_not_scan_siblings(self):
        (self.root / "other.dockerfile").write_text("FROM scratch\n")
        self.invoke(self.file)
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertEqual(2, len(calls))
        self.assertTrue(all(Path(call["argv"][-1]) == self.file for call in calls))

    def test_missing_explicit_path_does_not_scan_parent(self):
        result = self.invoke(self.root / "missing.dockerfile")
        self.assertEqual(1, result.returncode)
        self.assertEqual("UNVERIFIED", json.loads(result.stdout)["status"])
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_no_dockerfile_is_machine_readable_unverified(self):
        self.file.unlink()
        result = self.invoke()
        self.assertEqual(1, result.returncode)
        self.assertEqual("UNVERIFIED", json.loads(result.stdout)["status"])
        self.assertFalse((self.root / "calls.jsonl").exists())

    def test_discovery_does_not_silently_truncate_large_root(self):
        for number in range(21):
            (self.root / f"{number}.dockerfile").write_text("FROM scratch\n")
        nested = self.root / "nested" / "Dockerfile"
        nested.parent.mkdir()
        nested.write_text("FROM scratch\n")
        self.assertIn(nested, dockerfile_security.find_dockerfiles(self.root))

    def test_late_tool_failure_retains_earlier_diagnostics(self):
        other = self.root / "other.dockerfile"
        other.write_text("FROM scratch\n")
        self.configure(hadolint={"by_file": {"Dockerfile": {"rc": 1, "report": [hadolint_finding()]},
                                            "other.dockerfile": {"rc": 127, "stderr": "disappeared"}}})
        report = dockerfile_security.hadolint_scan([self.file, other], self.root)
        self.assertTrue(report["findings"])
        self.assertEqual("UNVERIFIED", report.get("status"))


if __name__ == "__main__":
    unittest.main()
