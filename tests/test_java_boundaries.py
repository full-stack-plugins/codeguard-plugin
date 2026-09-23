"""Java 架构与证据边界：真实 Git 差异不得被误判为仅发布版本变化。"""
from __future__ import annotations

import importlib.util
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
from java_project import _is_version_bump_only, analyze


class JavaBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-java-boundary-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "fixture")
        self.git("config", "core.hooksPath", "/dev/null")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              text=True, check=True, timeout=10).stdout

    def baseline(self, file, body):
        path = self.root / file
        path.write_text(body)
        self.git("add", file)
        self.git("commit", "-qm", "fixture")
        return path

    def pom(self, extra=""):
        return ("<project>\n<groupId>test</groupId>\n<artifactId>app</artifactId>\n"
                "<version>1</version>\n" + extra + "\n</project>")

    def test_dependency_version_change_does_not_downgrade(self):
        path = self.baseline("pom.xml", self.pom("<dependencies>\n<dependency>\n"
                             "<groupId>other</groupId>\n<artifactId>lib</artifactId>\n"
                             "<version>2</version>\n</dependency>\n</dependencies>"))
        path.write_text(path.read_text().replace("<version>2</version>", "<version>3</version>"))
        self.assertFalse(_is_version_bump_only(self.root, ["pom.xml"]))
        self.assertEqual(["mvn", "-B", "-DskipTests", "verify"],
                         analyze(self.root, ["pom.xml"])["commands"][0]["argv"])

    def test_compiler_configuration_change_does_not_downgrade(self):
        path = self.baseline("pom.xml", self.pom("<build>\n<plugins>\n<plugin>\n"
                             "<artifactId>maven-compiler-plugin</artifactId>\n<configuration>\n"
                             "<release>17</release>\n</configuration>\n</plugin>\n</plugins>\n</build>"))
        path.write_text(path.read_text().replace("<release>17", "<release>21"))
        self.assertFalse(_is_version_bump_only(self.root, ["pom.xml"]))

    def test_pure_project_version_with_existing_dependencies_still_downgrades(self):
        # 单行描述包含 dependency 标签，但真正变化的仅是项目顶层版本。
        body = self.pom("<dependencies><dependency><groupId>x</groupId><artifactId>y</artifactId>"
                        "<version>2</version></dependency></dependencies>").replace("\n", "")
        path = self.baseline("pom.xml", body)
        path.write_text(body.replace("<version>1</version>", "<version>1.1</version>"))
        self.assertTrue(_is_version_bump_only(self.root, ["pom.xml"]))
        self.assertEqual("validate", analyze(self.root, ["pom.xml"])["commands"][0]["argv"][-1])

    def test_gradle_logic_change_does_not_downgrade(self):
        path = self.baseline("build.gradle", "plugins { id 'java' }\nsourceCompatibility = 17\n")
        path.write_text(path.read_text().replace("17", "21"))
        self.assertFalse(_is_version_bump_only(self.root, ["build.gradle"]))
        self.assertEqual(["gradle", "check", "-x", "test"],
                         analyze(self.root, ["build.gradle"])["commands"][0]["argv"])

    def test_gradle_nested_version_assignment_is_not_project_release(self):
        path = self.baseline("build.gradle", "plugins {\n  id 'java'\n  id 'some.plugin'\n"
                             "  version '1.0'\n}\n")
        path.write_text(path.read_text().replace("'1.0'", "'2.0'"))
        self.assertFalse(_is_version_bump_only(self.root, ["build.gradle"]))

    def test_gradle_literal_project_version_remains_lightweight(self):
        path = self.baseline("build.gradle", "plugins { id 'java' }\nversion = '1'\n")
        path.write_text(path.read_text().replace("version = '1'", "version = '2'"))
        self.assertTrue(_is_version_bump_only(self.root, ["build.gradle"]))
        self.assertEqual(["gradle", "help"], analyze(self.root, ["build.gradle"])["commands"][0]["argv"])

    def test_authoritative_commands_remain_unchanged_for_version_bump(self):
        path = self.baseline("pom.xml", self.pom())
        path.write_text(path.read_text().replace("<version>1", "<version>2"))
        commands = [["custom-wrapper", "verify", "-Pquality"], ["other-check", "--test"]]
        (self.root / "codeguard.json").write_text(json.dumps({"java": {"commands": commands}}))
        self.assertEqual(commands, [c["argv"] for c in analyze(self.root, ["pom.xml"])["commands"]])

    def test_normalized_paths_choose_actual_module(self):
        (self.root / "pom.xml").write_text(self.pom("<modules><module>api</module><module>service</module></modules>"))
        for module in ("api", "service"):
            (self.root / module).mkdir()
            (self.root / module / "pom.xml").write_text(self.pom().replace("<artifactId>app", f"<artifactId>{module}"))
        plan = analyze(self.root, ["api/../service/src/A.java"])
        self.assertEqual(["service"], plan["affected_modules"])

    def test_impact_policy_imports_without_runtime_and_handles_cycles(self):
        self.assertIsNotNone(importlib.util.find_spec("codeguard.java_impact"), "缺少独立的纯影响计算边界")
        script = ("import sys,copy\nsys.path.insert(0,sys.argv[1])\n"
                  "from codeguard.java_impact import select_impact\n"
                  "from codeguard.java_planning import default_commands\n"
                  "modules={'.':{'dependencies':[]}, 'api':{'dependencies':['app']}, "
                  "'app':{'dependencies':['api']}, 'other':{'dependencies':[]}}\n"
                  "before=copy.deepcopy(modules)\n"
                  "affected,full=select_impact(modules,['api/src/A.java'],conservative=False)\n"
                  "assert affected == ['api','app'] and not full\nassert modules == before\n"
                  "assert default_commands('maven','./mvnw',affected,full=full,bump_only=False) == "
                  "[{'kind':'verify','argv':['./mvnw','-B','-pl','api,app','-am','-DskipTests','verify']}]\n"
                  "assert not any(m in sys.modules for m in "
                  "('subprocess','codeguard.execution','codeguard.java_build','mcp','gate_lib'))\n")
        result = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT / "scripts")],
                                text=True, capture_output=True, check=False, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_jdk_legacy_version_and_property_reference_resolve_through_real_probe(self):
        from java_project import _resolve_java_home

        binary = self.root / "update-alternatives"
        binary.write_text(f"#!{sys.executable}\nprint('/jdk/java-8-fixture/bin/java')\n")
        binary.chmod(0o755)
        for properties in ("<java.version>1.8</java.version>",
                           "<java.version>${target}</java.version><target>1.8</target>"):
            with self.subTest(properties=properties):
                (self.root / "pom.xml").write_text(self.pom(f"<properties>{properties}</properties>"))
                with patch("sys.platform", "linux"), patch.dict(os.environ, {"PATH": str(self.root)}):
                    home, reason = _resolve_java_home(self.root)
                self.assertEqual("/jdk/java-8-fixture", home, reason)

    def test_unavailable_git_baseline_never_downgrades(self):
        (self.root / "pom.xml").write_text(self.pom())
        self.assertFalse(_is_version_bump_only(self.root, ["pom.xml"]))
        self.assertEqual("verify", analyze(self.root, ["pom.xml"])["commands"][0]["argv"][-1])

    def test_revision_property_used_in_dependency_cannot_be_release_only(self):
        body = self.pom("<properties><revision>1</revision></properties>\n"
                        "<dependencies><dependency><groupId>external</groupId><artifactId>lib</artifactId>"
                        "<version>${revision}</version></dependency></dependencies>")
        path = self.baseline("pom.xml", body)
        path.write_text(body.replace("<revision>1", "<revision>2"))
        self.assertFalse(_is_version_bump_only(self.root, ["pom.xml"]))

    def test_revision_property_for_project_version_keeps_lightweight_check(self):
        body = self.pom("<properties><revision>1</revision></properties>").replace(
            "<version>1</version>", "<version>${revision}</version>")
        path = self.baseline("pom.xml", body)
        path.write_text(body.replace("<revision>1", "<revision>2"))
        self.assertTrue(_is_version_bump_only(self.root, ["pom.xml"]))

    def test_gradle_version_in_multiline_string_does_not_downgrade(self):
        body = 'plugins { java }\nval template = """\nversion = \'1\'\n"""\n'
        path = self.baseline("build.gradle.kts", body)
        path.write_text(body.replace("'1'", "'2'"))
        self.assertFalse(_is_version_bump_only(self.root, ["build.gradle.kts"]))

    def test_unknown_config_and_outside_changes_are_visible(self):
        (self.root / "pom.xml").write_text(self.pom())
        for configuration in ({"java": []}, {"java": {"commands": [[]]}}, {"exclude": "oops"}):
            with self.subTest(configuration=configuration):
                (self.root / "codeguard.json").write_text(json.dumps(configuration))
                plan = analyze(self.root)
                self.assertEqual("UNVERIFIED", plan["status"])
                self.assertEqual([], plan["commands"])
        (self.root / "codeguard.json").write_text("{}")
        self.assertEqual("UNVERIFIED", analyze(self.root, ["../outside.java"])["status"])

    def test_build_profiles_force_full_but_empty_changes_remain_skipped(self):
        (self.root / "pom.xml").write_text(self.pom("<profiles><profile><id>dynamic</id></profile></profiles>"))
        plan = analyze(self.root, ["src/A.java"])
        self.assertTrue(plan["conservative"])
        self.assertIn("profiles", " ".join(plan["reasons"]))
        self.assertEqual("SKIPPED", analyze(self.root, [])["status"])

    def test_planning_does_not_mutate_real_git_index(self):
        path = self.baseline("pom.xml", self.pom())
        path.write_text(path.read_text().replace("<version>1", "<version>2"))
        before = self.git("diff", "--cached", "--binary")
        index = self.root / ".git" / "index"
        before_bytes = index.read_bytes()
        plan = analyze(self.root, ["pom.xml"])
        self.assertEqual("PLANNED", plan["status"])
        self.assertEqual(before, self.git("diff", "--cached", "--binary"))
        self.assertEqual(before_bytes, index.read_bytes())

    def test_nested_project_compares_its_own_git_blob(self):
        self.baseline("pom.xml", self.pom())
        nested = self.root / "nested"
        nested.mkdir()
        file = nested / "pom.xml"
        body = self.pom().replace("<artifactId>app", "<artifactId>nested")
        file.write_text(body)
        self.git("add", "nested/pom.xml")
        self.git("commit", "-qm", "nested")
        file.write_text(body.replace("<version>1", "<version>2"))
        self.assertTrue(_is_version_bump_only(nested, ["pom.xml"]))

    def test_nested_parent_blob_cannot_hide_changed_dependency(self):
        # 顶层碰巧与嵌套项目当前依赖相同，不能拿顶层旧文件当嵌套项目基线。
        root_body = self.pom("<dependencies><dependency><groupId>x</groupId><artifactId>dep</artifactId>"
                             "<version>3</version></dependency></dependencies>")
        self.baseline("pom.xml", root_body)
        nested = self.root / "nested"
        nested.mkdir()
        file = nested / "pom.xml"
        file.write_text(root_body.replace("<version>3", "<version>2"))
        self.git("add", "nested/pom.xml")
        self.git("commit", "-qm", "nested")
        file.write_text(root_body.replace("<version>1", "<version>1.1"))
        self.assertFalse(_is_version_bump_only(nested, ["pom.xml"]))

    def test_version_bump_with_plugin_script_whitespace_is_not_pure(self):
        body = self.pom("<build><plugins><plugin><artifactId>script-plugin</artifactId>"
                        "<configuration><script>    run()</script></configuration></plugin></plugins></build>")
        path = self.baseline("pom.xml", body)
        path.write_text(body.replace("<version>1", "<version>2").replace("    run()", "run()"))
        self.assertFalse(_is_version_bump_only(self.root, ["pom.xml"]))

    def test_revision_referenced_by_plugin_attribute_is_not_pure(self):
        body = self.pom('<properties><revision>1</revision></properties>\n'
                        '<build><plugins><plugin><artifactId>script-plugin</artifactId>'
                        '<configuration><run release="${revision}" /></configuration></plugin></plugins></build>')
        path = self.baseline("pom.xml", body)
        path.write_text(body.replace("<revision>1", "<revision>2"))
        self.assertFalse(_is_version_bump_only(self.root, ["pom.xml"]))


if __name__ == "__main__":
    unittest.main()
