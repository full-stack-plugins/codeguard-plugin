"""全量门禁扫描剔除（构建产物目录）回归测试：2026-09-22 实战批次。

每个用例锚定 ddd4j-boot 13 分支仓实测踩过的坑：
- java 门禁 `mvn javadoc:jar` 在 target/**/apidocs/ 生成无 shebang 的
  javadoc.sh，shell 门禁的 find 把它当源码扫 → SC2148 必红；
  两个 gate 步骤互相矛盾，删了也输（java lint 并发再生成）。
- shellcheck gate 必须钉扎 --severity：老发布版本缺省时 info 级
  （SC2059/SC2295）也阻塞，门禁结论随 cache 版本漂移。
- skipGate 豁免只有总数没有明细，无法回答"哪个仓、何时被跳过"。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(PLUGIN / "hooks"))

import gate_lib  # noqa: E402
import scope  # noqa: E402
import validate_languages_json as vlj  # noqa: E402

REGISTRY = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
SHELL_GATE = next(lang for lang in REGISTRY["languages"] if lang["id"] == "shell")["gate"]


def _shellcheck_available() -> bool:
    try:
        subprocess.run(["shellcheck", "--version"], capture_output=True, check=False, timeout=10)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


class FindExcludeInjectionTests(unittest.TestCase):
    """full_excludes 必须覆盖 find 型 gate，且幂等、不影响 {file} 路径。"""

    def test_shell_gate_gains_target_exclude(self) -> None:
        out = scope.scope_cmd(SHELL_GATE, ".", full_excludes=True)
        expr = out[-1]
        self.assertIn("-not -path '*/target/*'", expr)
        # 注入必须落在 find 表达式内（-print0 之前），xargs 管道段不动
        self.assertLess(expr.index("'*/target/*'"), expr.index("-print0"))
        self.assertIn("xargs -0 shellcheck --severity=warning", expr)

    def test_injection_is_idempotent(self) -> None:
        once = scope.scope_cmd(SHELL_GATE, ".", full_excludes=True)
        twice = scope.scope_cmd(once, ".", full_excludes=True)
        self.assertEqual(once, twice)

    def test_existing_exclusion_not_duplicated(self) -> None:
        expr = scope.scope_cmd(SHELL_GATE, ".", full_excludes=True)[-1]
        self.assertEqual(expr.count("'*/node_modules/*'"), 1)

    def test_full_excludes_off_leaves_gate_verbatim(self) -> None:
        self.assertEqual(scope.scope_cmd(SHELL_GATE, "."), SHELL_GATE)

    def test_single_file_mode_unaffected(self) -> None:
        out = scope.scope_cmd(
            ["shellcheck", "--severity=warning", "{file}"], ".", single_file="a.sh")
        self.assertEqual(out, ["shellcheck", "--severity=warning", "a.sh"])

    def test_delta_fallback_full_scan_excludes(self) -> None:
        """delta 超 50 文件回退全量命令时（files=None）也必须剔除构建产物。"""
        out = scope.scope_cmd(SHELL_GATE, ".", files=None, full_excludes=True)
        self.assertIn("-not -path '*/target/*'", out[-1])


@unittest.skipUnless(_shellcheck_available(), "shellcheck not installed")
class JavadocShScenarioTests(unittest.TestCase):
    """端到端：java 门禁的 javadoc.sh 生成物不再让 shell 门禁误红。"""

    def _gate_exit(self, root: Path) -> int:
        cmd = scope.scope_cmd(SHELL_GATE, str(root), full_excludes=True)
        return subprocess.run(cmd, cwd=root, capture_output=True, timeout=60).returncode

    def test_generated_javadoc_sh_under_target_passes(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="cg-scan-"))
        gen = root / "target" / "reports" / "apidocs"
        gen.mkdir(parents=True)
        # 与 maven-javadoc-plugin 生成的 wrapper 同构：无 shebang 的单行 javadoc 调用
        (gen / "javadoc.sh").write_text(
            "/usr/bin/javadoc -J-Duser.language= -J-Duser.country= @options @packages\n")
        self.assertEqual(self._gate_exit(root), 0)

    def test_unshebangd_script_outside_target_still_fails(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="cg-scan-"))
        (root / "evil.sh").write_text("echo hi\n")
        self.assertNotEqual(self._gate_exit(root), 0)


class SkipAuditTrailTests(unittest.TestCase):
    """豁免审计：只有总数不够，必须能回答"哪个仓、何时"。"""

    def test_record_skip_event_keeps_repo_and_timestamp(self) -> None:
        old_home = os.environ.get("CODEGUARD_HOME")
        os.environ["CODEGUARD_HOME"] = tempfile.mkdtemp(prefix="cg-audit-")
        try:
            gate_lib.record_skip_event("skipGate", Path("/somewhere/myrepo"))
            state = json.loads(gate_lib.session_state_path().read_text(encoding="utf-8"))
            meta = state["_skip"]
            self.assertEqual(meta["count"], 1)
            event = meta["events"][-1]
            self.assertEqual(event["repo"], "myrepo")
            self.assertEqual(event["kind"], "skipGate")
            self.assertIn("T", event["ts"])  # ISO 形态时间戳
        finally:
            if old_home is None:
                os.environ.pop("CODEGUARD_HOME", None)
            else:
                os.environ["CODEGUARD_HOME"] = old_home

    def test_events_capped_at_20(self) -> None:
        os.environ["CODEGUARD_HOME"] = tempfile.mkdtemp(prefix="cg-audit-")
        for _ in range(25):
            gate_lib.record_skip_event("skipGate", Path("/r"))
        state = json.loads(gate_lib.session_state_path().read_text(encoding="utf-8"))
        self.assertEqual(len(state["_skip"]["events"]), 20)
        self.assertEqual(state["_skip"]["count"], 25)  # 总数不受截断影响


class DependencyResolutionHintTests(unittest.TestCase):
    """java 门禁依赖解析失败必须给行动指引，而不是只留 maven 堆栈尾部。"""

    def test_java_dependency_failure_gets_hint(self) -> None:
        out = "[ERROR] Could not resolve dependencies for project io.ddd4j:x:jar:1.0"
        hint = gate_lib._dependency_resolution_hint("java", out)
        self.assertIsNotNone(hint)
        self.assertIn("mvn install", hint)

    def test_non_java_or_unrelated_output_gets_none(self) -> None:
        self.assertIsNone(gate_lib._dependency_resolution_hint(
            "shell", "Could not resolve dependencies"))
        self.assertIsNone(gate_lib._dependency_resolution_hint("java", "BUILD SUCCESS"))


class RegistrySeverityPinTests(unittest.TestCase):
    """注册表契约：shellcheck gate 必须钉扎 --severity（防版本漂移回归）。"""

    def test_current_registry_passes(self) -> None:
        errors = [e for e in vlj.check(REGISTRY) if "severity" in e]
        self.assertEqual(errors, [])

    def test_unpinned_shellcheck_gate_is_rejected(self) -> None:
        reg = {"languages": [{"id": "shell", "status": "stable",
                              "gate": ["bash", "-c", "find . -name '*.sh' -print0 | xargs -0 shellcheck"]}]}
        errors = [e for e in vlj.check(reg) if "severity" in e]
        self.assertTrue(any(e.startswith("shell:gate:") for e in errors))


if __name__ == "__main__":
    unittest.main()
