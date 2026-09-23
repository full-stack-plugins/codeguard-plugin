"""离线扫描器进程夹具：报告、退出码与修复副作用必须共同决定结论。"""
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
import cve_check

# 真正执行 argv/cwd/输出协议；不调用漏洞服务或安装扫描器。
TOOL = '''import json, sys
from pathlib import Path
root = Path.cwd()
args = sys.argv[1:]
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps(args) + "\\n")
config = json.loads((root / "fixture.json").read_text())
if config.get("read_stdin"):
    (root / "scanner-input").write_text(sys.stdin.read())
if "--version" in args:
    result = config.get("probe", {"rc": 0, "report": {}})
elif args == ["audit", "fix"]:
    (root / "fixed").write_text("requested")
    result = config.get("fix", {"rc": 0, "report": {}})
else:
    counter = root / "counter"
    index = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(index + 1))
    result = config["scans"][min(index, len(config["scans"]) - 1)]
body = result.get("text", json.dumps(result.get("report", {})))
for arg in args:
    if arg.startswith("-Dodc.outputDirectory=") and not result.get("no_file"):
        (Path(arg.split("=", 1)[1]) / "dependency-check-report.json").write_text(body)
print(body)
print(result.get("stderr", ""), file=sys.stderr)
sys.exit(result.get("rc", 0))
'''


def npm_report(**counts):
    buckets = {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0}
    buckets.update(counts)
    return {"auditReportVersion": 2, "metadata": {
        "vulnerabilities": {**buckets, "total": sum(buckets.values())}}}


class CveBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-cve-boundary-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        tools = self.root / "bin"
        tools.mkdir()
        for name in ("npm", "mvn", "cargo", "pip-audit", "trivy"):
            tool = tools / name
            tool.write_text(f"#!{sys.executable}\n" + TOOL)
            tool.chmod(0o755)
        environment = patch.dict(os.environ, {"PATH": str(tools) + os.pathsep + os.environ["PATH"]})
        environment.start()
        self.addCleanup(environment.stop)
        (self.root / "package.json").write_text("{}")
        (self.root / "requirements.txt").write_text("example==1\n")

    def configure(self, report=None, rc=0, **options):
        data = {"scans": [{"report": report, "rc": rc}], **options}
        (self.root / "fixture.json").write_text(json.dumps(data))
        (self.root / "counter").unlink(missing_ok=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/cve_check.py"),
                               *args, str(self.root)], capture_output=True, text=True,
                              cwd=self.root, timeout=15, check=False)

    def test_trivy_invalid_results_are_not_empty_success(self):
        for results in ({}, "", None, [False]):
            with self.subTest(results=results):
                self.configure({"Results": results})
                self.assertEqual("UNVERIFIED", cve_check.scan_trivy(self.root, "HIGH")["status"])

    def test_trivy_unknown_severity_retains_finding(self):
        finding = {"VulnerabilityID": "CVE-TEST-1", "Severity": "UNKNOWN"}
        self.configure({"Results": [{"Target": "lock", "Vulnerabilities": [finding]}]}, 2)
        result = cve_check.scan_trivy(self.root, "HIGH")
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertEqual([finding], result["findings"])
        calls = [json.loads(line) for line in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertIn("UNKNOWN", calls[0][calls[0].index("--severity") + 1].split(","))

    def test_trivy_nonzero_without_findings_is_not_pass(self):
        self.configure({"Results": []}, 2)
        self.assertEqual("UNVERIFIED", cve_check.scan_trivy(self.root, "HIGH")["status"])

    def test_trivy_requires_finding_identity(self):
        self.configure({"Results": [{"Target": "lock", "Vulnerabilities": [{"Severity": "HIGH"}]}]}, 2)
        self.assertEqual("UNVERIFIED", cve_check.scan_trivy(self.root, "HIGH")["status"])

    def test_trivy_clean_report_and_threshold_remain_usable(self):
        for severity, rc, expected in ((None, 0, "PASS"), ("LOW", 0, "PASS"), ("HIGH", 2, "FAIL")):
            with self.subTest(severity=severity):
                findings = [] if severity is None else [{"VulnerabilityID": "CVE-T", "Severity": severity}]
                self.configure({"Results": [{"Target": "lock", "Vulnerabilities": findings}]}, rc)
                self.assertEqual(expected, cve_check.scan_trivy(self.root, "HIGH")["status"])

    def test_npm_incomplete_or_inconsistent_counts_are_unverified(self):
        cases = [{"total": 2}, {"high": 0}, {"low": 0, "moderate": 0, "high": 0, "critical": 0, "total": 2},
                 {"low": False, "moderate": 0, "high": 0, "critical": 0},
                 {"low": 0, "moderate": 0, "high": 0, "critical": 0, "unknown": 1}]
        for counts in cases:
            with self.subTest(counts=counts):
                self.configure({"metadata": {"vulnerabilities": counts}})
                self.assertEqual("UNVERIFIED", cve_check.scan_node(self.root, "HIGH", False)["status"])

    def test_npm_error_payload_cannot_be_hidden_by_zero_counts(self):
        self.configure({**npm_report(), "error": {"code": "EAUDIT", "summary": "registry failure"}})
        self.assertEqual("UNVERIFIED", cve_check.scan_node(self.root, "HIGH", False)["status"])

    def test_npm_nonzero_zero_findings_is_unverified(self):
        self.configure(npm_report(), 1)
        self.assertEqual("UNVERIFIED", cve_check.scan_node(self.root, "HIGH", False)["status"])

    def test_npm_lower_severity_still_passes_high(self):
        self.configure(npm_report(low=1), 1)
        result = cve_check.scan_node(self.root, "HIGH", False)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["exit"])

    def test_maven_invalid_scores_do_not_create_findings_or_success(self):
        for value in (True, float("nan"), float("inf"), -1, 11, "9.8"):
            with self.subTest(score=value):
                self.configure({"dependencies": [{"vulnerabilities": [
                    {"name": "CVE-T", "cvssv3": {"baseScore": value}}]}]})
                self.assertEqual("UNVERIFIED", cve_check.scan_maven(self.root, 7)["status"])

    def test_maven_missing_identity_is_not_a_confirmed_finding(self):
        self.configure({"dependencies": [{"vulnerabilities": [{"cvssv3": {"baseScore": 9.8}}]}]}, 1)
        self.assertEqual("UNVERIFIED", cve_check.scan_maven(self.root, 7)["status"])

    def test_maven_unknown_score_is_preserved_and_low_reports_it(self):
        report = {"dependencies": [{"vulnerabilities": [{"name": "CVE-T"}]}]}
        self.configure(report)
        result = cve_check.scan_maven(self.root, 7)
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertTrue(result["findings"])
        self.configure(report, 1)
        self.assertEqual("FAIL", cve_check.scan_maven(self.root, 0)["status"])

    def test_maven_stale_project_report_is_never_used(self):
        (self.root / "dependency-check-report.json").write_text('{"dependencies": []}')
        self.configure(scans=[{"rc": 1, "no_file": True, "stderr": "network failed"}])
        result = cve_check.scan_maven(self.root, 7)
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertTrue(result.get("reason"))

    def test_cargo_inconsistent_summary_is_not_pass(self):
        self.configure({"vulnerabilities": {"found": True, "count": 2, "list": []}})
        self.assertEqual("UNVERIFIED", cve_check.scan_cargo(self.root, "HIGH")["status"])

    def test_cargo_failed_probe_stops_before_scan(self):
        self.configure({"vulnerabilities": {"found": False, "count": 0, "list": []}},
                       probe={"rc": 124, "stderr": "timeout"})
        result = cve_check.scan_cargo(self.root, "HIGH")
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertEqual(124, result["exit"])
        self.assertFalse((self.root / "counter").exists())

    def test_pip_skipped_dependency_cannot_be_reported_clean(self):
        self.configure({"dependencies": [{"name": "x", "skip_reason": "unresolved", "vulns": []}]})
        self.assertEqual("UNVERIFIED", cve_check.scan_pip(self.root, "HIGH")["status"])

    def test_native_unrated_findings_keep_low_and_high_distinct(self):
        fixtures = ((cve_check.scan_pip, {"dependencies": [{"name": "x", "version": "1",
                     "vulns": [{"id": "PYSEC-T"}]}]}),
                    (cve_check.scan_cargo, {"vulnerabilities": {"found": True, "count": 1,
                     "list": [{"advisory": {"id": "RUSTSEC-T"}}]}}))
        for scan, report in fixtures:
            for severity, expected in (("LOW", "FAIL"), ("HIGH", "UNVERIFIED")):
                with self.subTest(scan=scan.__name__, severity=severity):
                    self.configure(report, 1)
                    result = scan(self.root, severity)
                    self.assertEqual(expected, result["status"])
                    self.assertEqual(1, len(result["findings"]))

    def test_fix_rescan_is_authoritative_and_fix_outcome_visible(self):
        self.configure(scans=[{"rc": 1, "report": npm_report(high=1)},
                              {"rc": 0, "report": npm_report()}],
                       fix={"rc": 1, "stderr": "some changes made"})
        completed = self.cli("--ecosystem", "node", "--json", "--fix")
        data = json.loads(completed.stdout)
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = data["results"][0]
        self.assertEqual("FAIL", result["before_fix"]["status"])
        self.assertIn("fix_execution", result)
        self.assertEqual(1, result["fix_execution"]["exit"])
        self.assertEqual("2", (self.root / "counter").read_text())

    def test_failed_rescan_cannot_reuse_prior_result(self):
        self.configure(scans=[{"rc": 1, "report": npm_report(high=1)},
                              {"rc": 1, "text": "network failed"}])
        completed = self.cli("--ecosystem", "node", "--json", "--fix")
        self.assertEqual(1, completed.returncode)
        self.assertEqual("UNVERIFIED", json.loads(completed.stdout)["status"])

    def test_invalid_report_does_not_authorize_fix(self):
        self.configure({"metadata": {"vulnerabilities": {"high": 1}}}, 1)
        completed = self.cli("--ecosystem", "node", "--json", "--fix")
        self.assertEqual(1, completed.returncode)
        self.assertFalse((self.root / "fixed").exists())

    def test_bad_configuration_is_json_unverified_before_any_scan(self):
        (self.root / "codeguard.json").write_text("{ broken")
        self.configure(npm_report())
        for args in (("--json",), ("--json", "--ecosystem", "node", "--fix")):
            with self.subTest(args=args):
                completed = self.cli(*args)
                self.assertEqual(1, completed.returncode)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertEqual("UNVERIFIED", json.loads(completed.stdout)["status"])
                self.assertFalse((self.root / "calls.jsonl").exists())

    def test_malformed_optional_scan_info_is_a_report_error(self):
        from codeguard.cve_policy import classify
        from codeguard.cve_reports import parse_report
        for scan_info in (None, [], "invalid"):
            with self.subTest(scan_info=scan_info):
                source = json.dumps({"dependencies": [], "scanInfo": scan_info})
                try:
                    result = parse_report("maven", source, 7)
                except AttributeError:
                    self.fail("非法报告形状不应泄漏 AttributeError")
                self.assertEqual("UNVERIFIED", classify(result, 0)[0])

    def test_npm_detail_conflict_does_not_hide_finding(self):
        self.configure({**npm_report(), "vulnerabilities": {
            "example": {"name": "example", "severity": "high", "via": ["CVE-T"]}}})
        self.assertEqual("UNVERIFIED", cve_check.scan_node(self.root, "HIGH", False)["status"])

    def test_pip_partial_error_preserves_findings_but_is_unverified(self):
        self.configure({"dependencies": [{"name": "x", "vulns": [{"id": "PYSEC-T"}]},
                                           {"name": "y", "skip_reason": "cannot resolve"}]}, 1)
        result = cve_check.scan_pip(self.root, "LOW")
        self.assertEqual("UNVERIFIED", result["status"])
        self.assertEqual("PYSEC-T", result["findings"][0]["id"])

    def test_all_scanners_clean_and_process_failure_matrix(self):
        cases = ((cve_check.scan_maven, 7, {"dependencies": []}),
                 (cve_check.scan_node, "HIGH", npm_report()),
                 (cve_check.scan_pip, "HIGH", {"dependencies": [{"name": "x", "version": "1", "vulns": []}]}),
                 (cve_check.scan_cargo, "HIGH", {"vulnerabilities": {"found": False, "count": 0, "list": []}}),
                 (cve_check.scan_trivy, "HIGH", {"Results": [{"Target": "lock"}]}))
        for scanner, severity, report in cases:
            for rc, expected in ((0, "PASS"), (124, "UNVERIFIED"), (126, "UNVERIFIED"), (127, "UNVERIFIED")):
                with self.subTest(scanner=scanner.__name__, rc=rc):
                    self.configure(report, rc)
                    result = scanner(self.root, severity)
                    self.assertEqual(expected, result["status"])
                    self.assertEqual(rc, result["exit"])
                    self.assertEqual(str(self.root), result["execution"]["cwd"])

    def test_cli_text_and_json_agree_for_all_three_verdicts(self):
        for report, rc, status, exit_code in ((npm_report(), 0, "PASS", 0),
                                              (npm_report(high=1), 1, "FAIL", 2),
                                              ({}, 0, "UNVERIFIED", 1)):
            with self.subTest(status=status):
                self.configure(report, rc)
                text = self.cli("--ecosystem", "node")
                machine = self.cli("--ecosystem", "node", "--json")
                self.assertEqual(exit_code, text.returncode)
                self.assertEqual(exit_code, machine.returncode)
                self.assertIn(status, text.stdout)
                self.assertEqual(status, json.loads(machine.stdout)["status"])

    def test_pure_parser_and_policy_import_without_runtime(self):
        program = f'''import sys
sys.path.insert(0, {str(ROOT / "scripts")!r})
from codeguard.cve_policy import classify
from codeguard.cve_reports import parse_report
assert classify(parse_report("maven", '{{"dependencies": []}}', 7), 0)[0] == "PASS"
assert not any(name in sys.modules for name in ("subprocess", "codeguard.execution", "codeguard.cve_scanners", "cve_check"))
'''
        result = subprocess.run([sys.executable, "-I", "-S", "-c", program],
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_application_never_infers_pass_from_bare_exit_zero(self):
        from codeguard.cve import ECOSYSTEM_SCANNERS, scan_project
        for status in (None, "PAss"):
            with self.subTest(status=status), patch.dict(ECOSYSTEM_SCANNERS["node"], {
                    "scan": lambda *args, verdict=status: {
                        "ecosystem": "node", "tool": "fixture", "exit": 0, "status": verdict}}):
                result = scan_project(self.root, "node")
                self.assertEqual(1, result.exit_code)
                self.assertEqual("UNVERIFIED", result.results[0]["status"])

    def test_filtered_scanner_nonzero_requires_matching_evidence(self):
        cases = ((cve_check.scan_maven, 7, 1, {"dependencies": [{"vulnerabilities": [
                    {"name": "CVE-T", "cvssv3": {"baseScore": 3.1}}]}]}),
                 (cve_check.scan_trivy, "HIGH", 2, {"Results": [{"Target": "lock", "Vulnerabilities": [
                    {"VulnerabilityID": "CVE-T", "Severity": "LOW"}]}]}))
        for scanner, threshold, rc, report in cases:
            with self.subTest(scanner=scanner.__name__):
                self.configure(report, rc)
                self.assertEqual("UNVERIFIED", scanner(self.root, threshold)["status"])

    def test_scanner_does_not_consume_host_input(self):
        self.configure(npm_report(), read_stdin=True)
        program = f'''import sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / "scripts")!r})
from codeguard.cve_scanners import scan_node
assert scan_node(Path.cwd(), "HIGH")["status"] == "PASS"
print(sys.stdin.read(), end="")
'''
        result = subprocess.run([sys.executable, "-c", program], cwd=self.root, input="host protocol payload",
                                capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("host protocol payload", result.stdout)
        self.assertEqual("", (self.root / "scanner-input").read_text())


if __name__ == "__main__":
    unittest.main()
