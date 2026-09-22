"""本轮会话修复的回归测试：版本 bump 降级 + JDK 兼容解析 + 豁免即时明示 + 工具链失配分类。

每个测试对应本会话（2026-09-22 codex/claudecode 六分支发布）中的真实痛点场景。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))


class VersionBumpDowngradeTests(unittest.TestCase):
    """P1：纯版本 bump 提交降级为 validate，不触发全量 verify。"""

    def _make_repo(self, pom_content: str) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "pom.xml").write_text(pom_content, encoding="utf-8")
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True, check=False)
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=False)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], cwd=root, capture_output=True, check=False)
        return root

    def test_pure_version_bump_detected(self):
        from java_project import _is_version_bump_only
        root = self._make_repo(
            '<?xml version="1.0"?><project><version>1.0.0</version></project>'
        )
        # 修改版本行
        pom = root / "pom.xml"
        pom.write_text(pom.read_text().replace("1.0.0", "1.0.1"), encoding="utf-8")
        import subprocess
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=False)
        self.assertTrue(_is_version_bump_only(root, ["pom.xml"]))

    def test_dependency_change_not_bump(self):
        from java_project import _is_version_bump_only
        root = self._make_repo(
            '<?xml version="1.0"?><project><version>1.0.0</version>'
            '<dependencies><dependency><artifactId>foo</artifactId></dependency></dependencies></project>'
        )
        pom = root / "pom.xml"
        pom.write_text(pom.read_text().replace("foo", "bar"), encoding="utf-8")
        import subprocess
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=False)
        self.assertFalse(_is_version_bump_only(root, ["pom.xml"]))

    def test_non_build_file_not_bump(self):
        from java_project import _is_version_bump_only
        root = self._make_repo('<?xml version="1.0"?><project><version>1.0</version></project>')
        (root / "src/Main.java").parent.mkdir(parents=True, exist_ok=True)
        (root / "src/Main.java").write_text("class Main {}", encoding="utf-8")
        import subprocess
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=False)
        self.assertFalse(_is_version_bump_only(root, ["pom.xml", "src/Main.java"]))


class ToolchainVerdictTests(unittest.TestCase):
    """P0-1：工具链失配归 UNVERIFIED，而非 FAIL。"""

    def test_maven_model_version_mismatch_is_unverified(self):
        from verdict import UNVERIFIED, lint_verdict
        output = "[FATAL] 'modelVersion' of '4.1.0' is newer than the versions supported by this version of Maven: [4.0.0]"
        status, reason = lint_verdict(1, ["mvn", "verify"], output)
        self.assertEqual(status, UNVERIFIED, f"got {status}: {reason}")

    def test_jdk_release_not_supported_is_unverified(self):
        from verdict import UNVERIFIED, lint_verdict
        output = "[ERROR] error: release version 1.8 not supported"
        status, reason = lint_verdict(1, ["javadoc", "-source", "1.8"], output)
        self.assertEqual(status, UNVERIFIED, f"got {status}: {reason}")

    def test_invalid_target_release_is_unverified(self):
        from verdict import UNVERIFIED, lint_verdict
        output = "[ERROR] error: invalid target release: 21"
        status, reason = lint_verdict(1, ["javac", "--release", "21"], output)
        self.assertEqual(status, UNVERIFIED, f"got {status}: {reason}")

    def test_class_version_mismatch_is_unverified(self):
        from verdict import UNVERIFIED, lint_verdict
        output = "java.lang.UnsupportedClassVersionError: Foo has been compiled by a more recent version of the Java Runtime"
        status, reason = lint_verdict(1, ["java", "-jar", "foo.jar"], output)
        self.assertEqual(status, UNVERIFIED, f"got {status}: {reason}")

    def test_real_violation_still_fails(self):
        from verdict import FAIL, lint_verdict
        output = "src/Main.java:5: warning: unused variable"
        status, reason = lint_verdict(1, ["mvn", "checkstyle:check"], output)
        self.assertEqual(status, FAIL, f"got {status}: {reason}")


class SkipGateNotificationTests(unittest.TestCase):
    """7.2：内联/链式豁免放行时发 hookSpecificOutput 即时明示。"""

    def test_inline_skip_gate_detected(self):
        from pre_tool_git_guard import inline_skip_gate
        self.assertTrue(inline_skip_gate("git -c codeguard.skipGate=true commit -m msg"))
        self.assertFalse(inline_skip_gate("git commit -m msg"))
        self.assertFalse(inline_skip_gate("git -c core.editor=vim commit -m msg"))  # 不是 skipGate

    def test_chain_skip_gate_detected(self):
        from pre_tool_git_guard import chain_skip_gate
        self.assertTrue(chain_skip_gate(
            "git config codeguard.skipGate true && git commit -m msg && git config --unset codeguard.skipGate"
        ))
        self.assertFalse(chain_skip_gate("git commit -m msg"))

    def test_inline_skip_not_in_message_text(self):
        from pre_tool_git_guard import inline_skip_gate
        # commit message 中提到 skipGate 不应被误判为豁免
        self.assertFalse(inline_skip_gate(
            'git commit -m "docs: mention codeguard.skipGate in README"'
        ))


class JdkResolutionTests(unittest.TestCase):
    """P0-2：JDK 兼容性解析。"""

    def test_no_pom_returns_none(self):
        from java_project import _resolve_java_home
        root = Path(tempfile.mkdtemp())
        home, reason = _resolve_java_home(root)
        self.assertIsNone(home)
        self.assertIsNone(reason)

    def test_declared_java_version_returns_reason_when_no_jdk(self):
        from java_project import _resolve_java_home
        root = Path(tempfile.mkdtemp())
        (root / "pom.xml").write_text(
            '<?xml version="1.0"?><project><java.version>99</java.version></project>',
            encoding="utf-8",
        )
        home, reason = _resolve_java_home(root)
        # JDK 99 大概率不存在——应返回 None + 原因
        if home is None:
            self.assertIsNotNone(reason)
            self.assertIn("99", reason)


if __name__ == "__main__":
    unittest.main()
