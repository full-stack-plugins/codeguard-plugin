"""计划丢失环境、提前假绿或修复后扩大范围，必须通过真实进程暴露。"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]

import gate_lib
import post_tool_lint
import run_per_language
from codeguard import check_application, execution, save_application
from detect_lang import LANG_COMMANDS


class CheckPlanIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cg-plans-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def put(self, path, content):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return dest

    def test_java_selected_environment_reaches_each_command_without_mutating_host(self):
        self.put("pom.xml", "<project><modelVersion>4.0.0</modelVersion><groupId>demo</groupId>"
                 "<artifactId>app</artifactId><version>1</version></project>")
        self.put("src/A.java", "class A {}")
        selected = str(self.root / "selected-jdk")
        commands = [[sys.executable, "-c",
                     ("import os,pathlib; p=pathlib.Path('jdk.log'); "
                     "p.open('a').write(os.environ.get('JAVA_HOME', 'missing')+'\\n'); "
                     f"raise SystemExit({rc})")] for rc in (0, 1, 0)]
        self.put("codeguard.json", json.dumps({"java": {"commands": commands}}))
        with patch("codeguard.java_analysis.resolve_java_home", return_value=(selected, None)), \
                patch.dict(os.environ, {"JAVA_HOME": "host-jdk", "CODEGUARD_HOME": str(self.root / "state")}):
            result = run_per_language.run_check(["java"], self.root, files=["src/A.java"])[0]
            self.assertEqual("FAIL", result["status"])
            self.assertEqual(commands[1], result["command"])
            self.assertEqual(["check", "check"],
                             [item["phase"] for item in result["execution_trace"]])
            self.assertNotIn(selected, json.dumps(result["execution_trace"]))
            self.assertEqual("host-jdk", os.environ["JAVA_HOME"])
            self.assertEqual([selected, selected], (self.root / "jdk.log").read_text().splitlines())
            (self.root / "jdk.log").unlink()
            failures, skipped = gate_lib._run_gate_uncached(
                self.root, {}, ["java"], scope="delta", changed=["src/A.java"])
            self.assertEqual(1, len(failures))
            self.assertEqual([], skipped)
            self.assertEqual([selected, selected], (self.root / "jdk.log").read_text().splitlines())

    def test_java_multi_command_evidence_survives_result_mcp_and_failure_log(self):
        self.put("pom.xml", "<project><modelVersion>4.0.0</modelVersion><groupId>demo</groupId>"
                 "<artifactId>app</artifactId><version>1</version></project>")
        self.put("src/A.java", "class A {}")
        commands = [
            [sys.executable, "-c", "print('x' * 2000 + 'preflight diagnostic')"],
            [sys.executable, "-c", "import sys; print('compile failed', file=sys.stderr); sys.exit(1)"],
            [sys.executable, "-c", "from pathlib import Path; Path('unexpected').touch()"],
        ]
        self.put("codeguard.json", json.dumps({"java": {"commands": commands}}))
        with patch("codeguard.java_analysis.resolve_java_home", return_value=(None, None)):
            result = run_per_language.run_check(
                ["java"], self.root, files=["src/A.java"], log_dir=self.root / "out")[0]
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(commands[1], result["command"])
        self.assertFalse((self.root / "unexpected").exists())
        trace = result["execution_trace"]
        self.assertEqual(commands[:2], [item["command"] for item in trace])
        self.assertEqual([0, 1], [item["exit_code"] for item in trace])
        self.assertEqual([str(self.root)] * 2, [item["cwd"] for item in trace])
        self.assertIn("preflight diagnostic", trace[0]["stdout_tail"])
        self.assertLessEqual(len(trace[0]["stdout_tail"]), 1000)
        self.assertIn("compile failed", trace[1]["stderr_tail"])
        self.assertIsNone(trace[0]["failure"])
        public_trace = check_application.result_envelope([result])[0]["execution_trace"]
        self.assertEqual([0, 1], [item["exit_code"] for item in public_trace])
        self.assertEqual([1, 2], [item["number"] for item in public_trace])
        self.assertEqual([Path(sys.executable).name] * 2,
                         [item["program"] for item in public_trace])
        self.assertGreater(public_trace[0]["stdout_chars"], 2000)
        self.assertNotIn("preflight diagnostic", json.dumps(public_trace))
        self.assertNotIn("command", public_trace[0])
        with patch("codeguard.java_analysis.resolve_java_home", return_value=(None, None)):
            mcp_payload = check_application.mcp_tool_payload(
                "check_code_style", {"path": str(self.root), "languages": ["java"]}, self.root)
        self.assertEqual(public_trace, mcp_payload[0]["execution_trace"])
        log_text = Path(result["log_path"]).read_text()
        self.assertIn("preflight diagnostic", log_text)
        self.assertIn("x" * 2000, log_text)

    def test_mcp_auto_fix_does_not_echo_new_trace_command_or_output(self):
        self.put("src/A.java", "class A {}")
        secret = "CG_TEST_SECRET_TOKEN_8b7f"
        trace = [{"phase": "fix", "command": ["formatter", f"--token={secret}"],
                  "cwd": str(self.root), "exit_code": 0, "failure": None,
                  "stdout_chars": len(secret), "stderr_chars": 0,
                  "stdout_tail": secret, "stderr_tail": ""}]
        fix_result = {"language": "java", "fixed": True, "exit_code": 0,
                      "stderr_tail": "", "execution_trace": trace}
        check_result = {"language": "java", "passed": True, "status": "PASS",
                        "reason": "", "exit_code": 0, "execution_trace": trace}
        with patch.object(check_application, "changed_files", return_value=["src/A.java"]), \
                patch.object(check_application, "run_fix", return_value=[fix_result]), \
                patch.object(check_application, "run_check", return_value=[check_result]):
            payload = check_application.auto_fix(self.root, ["java"])
        self.assertNotIn(secret, json.dumps(payload))
        self.assertEqual("formatter", payload["fix_results"][0]["execution_trace"][0]["program"])
        self.assertEqual("formatter", payload["check"][0]["execution_trace"][0]["program"])

    def test_mixed_zsh_fix_rechecks_the_shell_plan_without_touching_other_files(self):
        self.put("a.sh", "GOOD")
        self.put("b.sh", "BAD")
        self.put("skip.zsh", "GOOD")
        self.put("untouched.sh", "BAD")
        # 不是模拟进程：两工具实际读写文件，日志证明命令顺序与完整复检范围。
        checker = self.put("checker.py", "import pathlib,sys\n"
                           "p=pathlib.Path(sys.argv[1])\n"
                           "pathlib.Path('checked.log').open('a').write(p.name+'\\n')\n"
                           "print(p.name)\nraise SystemExit(int('BAD' in p.read_text()))\n")
        formatter = self.put("formatter.py", "import pathlib,sys\n"
                             "p=pathlib.Path(sys.argv[1])\n"
                             "p.write_text(p.read_text().replace('BAD','GOOD'))\n")
        command = {"lint": [sys.executable, str(checker), "{file}"],
                   "format": [sys.executable, str(formatter), "{file}"]}
        with patch.dict(LANG_COMMANDS, {"shell": command}):
            result = run_per_language.run_check(
                ["shell"], self.root, files=["a.sh", "b.sh", "skip.zsh"], fix=True)[0]
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(["check", "check", "fix", "fix", "recheck", "recheck", "recheck"],
                         [item["phase"] for item in result["execution_trace"]])
        self.assertEqual(["a.sh", "b.sh", "a.sh", "b.sh", "skip.zsh"],
                         (self.root / "checked.log").read_text().splitlines())
        self.assertEqual("GOOD", (self.root / "b.sh").read_text())
        self.assertEqual("GOOD", (self.root / "skip.zsh").read_text())
        self.assertEqual("BAD", (self.root / "untouched.sh").read_text())

    def test_plan_retains_attempts_and_stops_before_unexecuted_side_effect(self):
        self.assertTrue(hasattr(execution, "execute_plan"), "缺少可复用的计划执行边界")
        from codeguard.models import CheckPlan, Command

        commands = tuple(Command((sys.executable, "-c", body)) for body in (
            "print('first')", "print('failed'); raise SystemExit(1)",
            "from pathlib import Path; Path('unexpected').touch()"))
        plan = CheckPlan(self.root, "delta", commands)
        outcome = execution.execute_plan(plan, 5)
        self.assertEqual(["first\n", "failed\n"], [a.stdout for a in outcome.attempts])
        self.assertEqual(1, outcome.terminal.returncode)
        self.assertFalse((self.root / "unexpected").exists())

    def test_scopes_are_materialized_before_execution_and_empty_scope_never_runs(self):
        self.assertIsNotNone(find_spec("codeguard.planning"), "缺少共享作用域规划器")
        from codeguard.planning import scoped_plan

        argv = [sys.executable, "-c", "import sys; print('|'.join(sys.argv[1:]))", "."]
        for mode, files, expected in (("repo", None, ".\n"),
                                      ("delta", ["a.py", "b.py"], "a.py|b.py\n"),
                                      ("save", ["a.py"], "a.py\n")):
            with self.subTest(scope=mode):
                plan = scoped_plan(argv, self.root, scope=mode, files=files)
                if files is not None:
                    files.append("outside.py")
                outcome = execution.execute_plan(plan, 5)
                self.assertEqual(expected, outcome.terminal.stdout)
        for mode, files in (("delta", []), ("save", []), ("save", ["a", "b"]),
                            ("repo", ["a"]), ("delta", None)):
            with self.subTest(scope=mode, files=files), self.assertRaises(ValueError):
                scoped_plan(argv, self.root, scope=mode, files=files)
        with self.assertRaises(ValueError):
            scoped_plan(["linter", "{file}"], self.root, scope="repo")

    def test_empty_plan_and_empty_command_cannot_claim_success(self):
        self.assertTrue(hasattr(execution, "execute_plan"), "缺少可复用的计划执行边界")
        from codeguard.models import CheckPlan, Command

        with self.assertRaises(ValueError):
            CheckPlan(self.root, "repo", ())
        with self.assertRaises(ValueError):
            Command(())

    def test_gate_full_fallback_without_project_command_never_runs_empty_placeholder(self):
        paths = [f"file{n}.sh" for n in range(51)]
        for path in paths:
            self.put(path, "GOOD")
        argv = [sys.executable, "-c", "from pathlib import Path; Path('unexpected').touch()", "{file}"]
        with patch.dict(LANG_COMMANDS, {"shell": {"lint": argv}}), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.root / "state")}):
            failures, skipped = gate_lib._run_gate_uncached(
                self.root, {}, ["shell"], scope="delta", changed=paths)
        self.assertFalse((self.root / "unexpected").exists(), "不得以空路径执行单文件命令冒充全量")
        self.assertEqual([], failures)
        self.assertTrue(any("未验证" in item for item in skipped), skipped)

    def test_save_fix_and_recheck_stay_on_original_file(self):
        target = self.put("target.py", "BAD")
        other = self.put("other.py", "BAD")
        checker = self.put("checker", "import pathlib,sys\n"
                           "p=pathlib.Path(sys.argv[1])\n"
                           "pathlib.Path('checked.log').open('a').write(p.name+'\\n')\n"
                           "print('F401' if 'BAD' in p.read_text() else '')\n"
                           "raise SystemExit(int('BAD' in p.read_text()))\n")
        formatter = self.put("formatter", "import pathlib,sys\n"
                             "p=pathlib.Path(sys.argv[1])\n"
                             "p.write_text(p.read_text().replace('BAD','GOOD'))\n")
        commands = {"lint": [sys.executable, str(checker), "."],
                    "format": [sys.executable, str(formatter), "."]}
        output = io.StringIO()
        with patch.dict(LANG_COMMANDS, {"python": commands}), \
                patch.object(post_tool_lint, "read_payload", return_value={"file_path": str(target)}), \
                patch.object(post_tool_lint, "find_project_root", return_value=self.root), \
                patch.object(post_tool_lint, "load_user_config", return_value={"auto_fix_on_save": True}), \
                patch.object(save_application, "should_suppress_duplicate", return_value=False), \
                patch.dict(os.environ, {"CODEGUARD_HOME": str(self.root / "state")}), \
                contextlib.redirect_stdout(output):
            self.assertEqual(0, post_tool_lint.main())
        self.assertIn("passed", json.loads(output.getvalue())["hookSpecificOutput"]["additionalContext"])
        self.assertEqual("GOOD", target.read_text())
        self.assertEqual("BAD", other.read_text())
        self.assertEqual(["target.py", "target.py"], (self.root / "checked.log").read_text().splitlines())


if __name__ == "__main__":
    unittest.main()
