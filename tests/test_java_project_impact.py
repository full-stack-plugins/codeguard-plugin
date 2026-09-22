"""Java 规划的可观察契约：不用执行构建即可给出模块影响及真实命令。"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))


class JavaImpactTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="cg-java-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()

    def put(self, name, body):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        return p

    def pom(self, path=".", artifact="root", modules=(), dependencies=(), extra=""):
        self.put(f"{path}/pom.xml", '<project xmlns="http://maven.apache.org/POM/4.0.0">'
                 '<modelVersion>4.0.0</modelVersion><groupId>example</groupId>'
                 f'<artifactId>{artifact}</artifactId><version>1</version><modules>'
                 + ''.join(f'<module>{m}</module>' for m in modules) + '</modules><dependencies>'
                 + ''.join('<dependency><groupId>example</groupId>'
                           f'<artifactId>{d}</artifactId><version>1</version></dependency>' for d in dependencies)
                 + '</dependencies>' + extra + '</project>')

    def analyze(self, changed=None):
        self.assertTrue((PLUGIN / "scripts/java_project.py").is_file(), "缺少 Java 项目规划能力")
        return importlib.import_module("java_project").analyze(self.root, changed)

    def fixture(self):
        self.pom(modules=["api", "service", "app", "other"])
        self.pom("api", "api")
        self.pom("service", "service", dependencies=["api"])
        self.pom("app", "app", dependencies=["service"])
        self.pom("other", "other")

    def test_maven_reverse_transitive_closure_and_wrapper(self):
        self.fixture()
        wrapper = self.put("mvnw", "#!/bin/sh\nexit 0\n")
        wrapper.chmod(0o755)
        plan = self.analyze(["api/src/main/java/Api.java"])
        self.assertEqual(plan["affected_modules"], ["api", "app", "service"])
        self.assertEqual(plan["commands"][0]["argv"],
                         ["./mvnw", "-B", "-pl", "api,app,service", "-am", "-DskipTests", "verify"])
        self.assertEqual(plan["status"], "PLANNED")
        self.assertIn("静态规则", " ".join(plan["gaps"]))

    def test_deleted_java_file_still_affects_dependents(self):
        self.fixture()
        plan = self.analyze(["service/src/main/java/Deleted.java"])
        self.assertEqual(plan["affected_modules"], ["app", "service"])

    def test_build_descriptor_change_expands_to_every_module(self):
        self.fixture()
        plan = self.analyze(["api/pom.xml"])
        self.assertEqual(plan["affected_modules"], [".", "api", "app", "other", "service"])
        self.assertNotIn("-pl", plan["commands"][0]["argv"])

    def test_resource_change_affects_java_consumers(self):
        self.fixture()
        self.assertEqual(self.analyze(["api/src/main/resources/schema.json"])["affected_modules"],
                         ["api", "app", "service"])

    def test_inherited_dependencies_require_conservative_build(self):
        self.fixture()
        self.pom(".", modules=["api", "service", "app", "other"], dependencies=["api"])
        self.assertTrue(self.analyze(["api/src/A.java"])["conservative"])

    def test_no_changed_files_does_not_create_commands(self):
        self.fixture()
        plan = self.analyze([])
        self.assertEqual(plan["commands"], [])
        self.assertEqual(plan["status"], "SKIPPED")

    def test_gradle_dependencies_use_gradle_not_maven(self):
        self.put("settings.gradle.kts", 'include(":api", ":service", ":other")')
        self.put("build.gradle.kts", 'plugins { java }')
        self.put("api/build.gradle.kts", 'plugins { java }')
        self.put("service/build.gradle.kts", 'dependencies { implementation(project(":api")) }')
        self.put("other/build.gradle.kts", 'plugins { java }')
        self.put("gradlew", "#!/bin/sh\nexit 0\n").chmod(0o755)
        plan = self.analyze(["api/src/main/java/Api.java"])
        self.assertEqual(plan["build_system"], "gradle")
        self.assertEqual(plan["affected_modules"], ["api", "service"])
        self.assertEqual(plan["commands"][0]["argv"], ["./gradlew", ":api:check", ":service:check", "-x", "test"])

    def test_dynamic_gradle_uses_full_root_check(self):
        self.put("settings.gradle", 'include(moduleNames)')
        self.put("build.gradle", 'apply from: "shared.gradle"')
        plan = self.analyze(["api/src/main/java/A.java"])
        self.assertTrue(plan["conservative"])
        self.assertEqual(plan["commands"][0]["argv"], ["gradle", "check", "-x", "test"])
        self.assertTrue(plan["reasons"])

    def test_missing_or_malformed_build_is_unverified(self):
        self.assertEqual(self.analyze()["status"], "UNVERIFIED")
        self.put("pom.xml", "broken XML")
        self.assertEqual(self.analyze()["status"], "UNVERIFIED")

    def test_module_path_cannot_escape_repository(self):
        self.pom(modules=["../outside"])
        plan = self.analyze(["src/main/java/A.java"])
        self.assertEqual(plan["status"], "UNVERIFIED")
        self.assertEqual(plan["commands"], [])

    def test_configured_authoritative_commands_take_precedence(self):
        self.pom()
        self.put("codeguard.json", json.dumps({"java": {"commands": [["./mvnw", "verify", "-Pquality"]]}}))
        plan = self.analyze(["src/main/java/A.java"])
        self.assertEqual(plan["commands"][0]["argv"], ["./mvnw", "verify", "-Pquality"])

    def test_planning_never_executes_wrapper_or_installs(self):
        self.pom()
        self.put("mvnw", "#!/bin/sh\ntouch SHOULD_NOT_EXIST\n").chmod(0o755)
        plan = self.analyze()
        self.assertTrue(plan["commands"])
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())

    def test_check_executes_gradle_plan(self):
        self.put("build.gradle", "plugins { id 'java' }")
        self.put("gradlew", '#!/bin/sh\n[ "$1" = check ] || exit 4\nprintf "checked"\n').chmod(0o755)
        import run_per_language
        results = run_per_language.run_check(["java"], self.root)
        self.assertTrue(results[0]["passed"], results)
        self.assertEqual(results[0]["command"], ["./gradlew", "check", "-x", "test"])

    def test_java_plan_cli_returns_machine_readable_plan(self):
        self.pom()
        proc = subprocess.run(["bash", str(PLUGIN / "bin/codeguard"), "java-plan", "--json", str(self.root)],
                              capture_output=True, text=True, check=False,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["build_system"], "maven")

    def test_gradle_kotlin_dsl_java_is_detected_by_cli(self):
        self.put("build.gradle.kts", "plugins { java }")
        self.put("gradlew", "#!/bin/sh\nexit 0\n").chmod(0o755)
        proc = subprocess.run([sys.executable, str(PLUGIN / "scripts/run_check.py"),
                               "--lang", "java", "--quiet", str(self.root)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
