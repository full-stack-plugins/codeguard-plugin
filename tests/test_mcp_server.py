"""Groups 3+4 regression tests: MCP server via official SDK + failure log
(OpenSpec change 2026-09-22-fix-gate-trigger-and-mcp).

MCP tests skip gracefully when the `mcp` SDK is not installed (CI installs
requirements.txt; local dev may not).
"""
from __future__ import annotations

import importlib.util
import json
import selectors
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None
# CLI 失败日志用例需要真实 linter 产生 FAIL 结果——ruff 缺失时只会得到
# UNVERIFIED（工具不存在），失败路径无法覆盖（无法验证 ≠ 验证失败）。
RUFF_AVAILABLE = shutil.which("ruff") is not None
RUN_CHECK = PLUGIN / "scripts" / "run_check.py"


def _spawn_mcp() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(RUN_CHECK), "--mcp", str(PLUGIN)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )


def _send(proc: subprocess.Popen, msg: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def _read_until(proc: subprocess.Popen, want_id: int, timeout: float = 30.0) -> dict:
    assert proc.stdout is not None
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    deadline_line = None
    import time
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not sel.select(timeout=1.0):
            continue
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == want_id:
            deadline_line = msg
            break
    sel.close()
    if deadline_line is None:
        err = proc.stderr.read() if proc.stderr else ""
        raise AssertionError(f"no response for id={want_id}; stderr={err[:2000]!r}")
    return deadline_line


@unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed (pip install -r requirements.txt)")
class McpServerTests(unittest.TestCase):
    def test_mcp_boot_lists_four_tools(self):
        """stdio 服务暴露三个兼容工具和 Java 只读分析。"""
        proc = _spawn_mcp()
        try:
            _send(proc, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            })
            init = _read_until(proc, 1)
            self.assertIn("result", init, init)
            _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            listing = _read_until(proc, 2)
            names = {t["name"] for t in listing["result"]["tools"]}
            self.assertEqual(names, {"check_code_style", "auto_fix", "list_languages", "analyze_java_impact"})
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "pom.xml").write_text("<project><artifactId>demo</artifactId></project>")
                _send(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "analyze_java_impact", "arguments": {"path": tmp}}})
                result = _read_until(proc, 3)
                plan = json.loads(result["result"]["content"][0]["text"])
                self.assertEqual(plan["status"], "PLANNED")
                self.assertEqual(plan["commands"][0]["argv"], ["mvn", "-B", "verify"])
                self.assertFalse((root / "target").exists())
        finally:
            try:
                if proc.stdin:
                    proc.stdin.close()
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001 cleanup
                proc.kill()
                proc.wait(timeout=10)
            proc.stdout.close()
            proc.stderr.close()

    def test_mcp_list_languages_returns_id_and_name_only(self):
        """3.5/6.3: tool result enumerates id+name, never internal commands."""
        proc = _spawn_mcp()
        try:
            _send(proc, {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            })
            _read_until(proc, 1)
            _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            _send(proc, {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {"name": "list_languages", "arguments": {}},
            })
            result = _read_until(proc, 3)
            content = result["result"]["content"]
            payload = json.loads(content[0]["text"])
            self.assertIsInstance(payload, list)
            self.assertGreater(len(payload), 10)
            for entry in payload:
                self.assertEqual(set(entry.keys()), {"id", "name"})
        finally:
            try:
                if proc.stdin:
                    proc.stdin.close()
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001 cleanup
                proc.kill()
                proc.wait(timeout=10)
            proc.stdout.close()
            proc.stderr.close()


class FailureLogTests(unittest.TestCase):
    def _bad_python_project(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "bad.py").write_text("import os\n", encoding="utf-8")
        return tmp, root

    def test_run_check_writes_full_stderr_log_on_failure(self):
        """4.1/4.2: failing lint writes <log_dir>/.codeguard-last.log and
        attaches log_path to the failing result entry."""
        import run_per_language
        tmp, root = self._bad_python_project()
        try:
            log_dir = root / "out"
            results = run_per_language.run_check(["python"], root, log_dir=log_dir)
            self.assertEqual(len(results), 1)
            r = results[0]
            # ruff present → F401 failure; ruff absent → 127 command not found.
            # Either way passed=False with a real log written.
            self.assertFalse(r["passed"])
            log_path = Path(r["log_path"])
            self.assertTrue(log_path.is_file(), "log file must exist")
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("python", content)
            self.assertTrue(content.strip(), "log must contain stderr content")
        finally:
            tmp.cleanup()

    @unittest.skipUnless(RUFF_AVAILABLE, "ruff not installed (pip install ruff) — 需真实 linter 制造 FAIL")
    def test_cli_failure_prints_log_path(self):
        """4.2 (CLI): terminal gets a summary line + absolute log path."""
        tmp, root = self._bad_python_project()
        try:
            log_dir = root / "out"
            proc = subprocess.run(
                [sys.executable, str(RUN_CHECK), str(root),
                 "--lang", "python", "--log-dir", str(log_dir)],
                capture_output=True, check=False, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("完整日志", proc.stdout)
            expected_log = (log_dir / ".codeguard-last.log").resolve()
            self.assertIn(str(expected_log), proc.stdout)
            self.assertTrue(expected_log.is_file())
        finally:
            tmp.cleanup()

    @unittest.skipUnless(RUFF_AVAILABLE, "ruff not installed (pip install ruff) — 需真实 linter 制造 FAIL")
    def test_cli_quiet_suppresses_log_and_summary(self):
        """4.3: --quiet writes no log and prints no log summary line."""
        tmp, root = self._bad_python_project()
        try:
            log_dir = root / "out"
            proc = subprocess.run(
                [sys.executable, str(RUN_CHECK), str(root),
                 "--lang", "python", "--log-dir", str(log_dir), "--quiet"],
                capture_output=True, check=False, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertNotIn("完整日志", proc.stdout)
            self.assertFalse((log_dir / ".codeguard-last.log").exists())
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
