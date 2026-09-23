"""Git 语法、仓库定位和路径规则可脱离宿主加载，原入口继续使用相同行为。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GitBoundaryTests(unittest.TestCase):
    def isolated(self, source, *args):
        result = subprocess.run([sys.executable, "-I", "-c",
                                 "import sys;sys.path.insert(0,sys.argv[1]);" + source,
                                 str(ROOT / "scripts"), *map(str, args)],
                                capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_git_syntax_does_not_load_hook_or_execute_commands(self):
        actual = self.isolated(
            "from codeguard.git_syntax import _collect_subs,inline_skip_gate,chain_skip_gate;"
            "import json; print(json.dumps(["
            "_collect_subs('x=$(git push origin main)'),"
            "_collect_subs('if FOO=1 git -C repo commit -m x; then :; fi'),"
            "_collect_subs('echo \\\"git push\\\"'),"
            "inline_skip_gate('git -c codeguard.skipGate=true commit -m x'),"
            "inline_skip_gate('git commit -m \\\"use -c codeguard.skipGate=true here\\\"'),"
            "chain_skip_gate('git config codeguard.skipGate true && git push'),"
            "any(m in sys.modules for m in ('subprocess','gate_lib','detect_lang','pre_tool_git_guard'))"
            "]))")
        self.assertEqual([["push"], ["commit"], [], True, False, True, False], actual)

    def test_path_policy_preserves_vendor_and_fixture_exceptions_without_git(self):
        actual = self.isolated(
            "from codeguard.path_policy import check_paths,is_build_artifact; import json;"
            "print(json.dumps([[v[0] for v in check_paths(['.env','vendor/pkg/x.py',"
            "'scripts/vendor/skill_vendor.py','tests/fixtures/sample.db','sample.db',"
            "'src/secret.pem','target/site/a.html'])],"
            "is_build_artifact('target/site/a.html'),is_build_artifact('src/a.py'),"
            "any(m in sys.modules for m in ('subprocess','scope','gate_lib','git_snapshot'))]))")
        self.assertEqual([[".env", "vendor/pkg/x.py", "sample.db", "src/secret.pem", "target/site/a.html"],
                          True, False, False], actual)

    def test_repository_binding_and_indirection_work_without_hooks_on_sys_path(self):
        with tempfile.TemporaryDirectory(prefix="cg-bindings-") as tmp:
            base = Path(tmp).resolve()
            left, right = base / "left", base / "right"
            for repo in (left, right):
                repo.mkdir()
                subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            script = base / "publish.sh"
            script.write_text("#!/bin/sh\ngit push origin main\n", encoding="utf-8")
            actual = self.isolated(
                "from codeguard.git_context import resolve_project_roots,_guarded_mode,staging_intent;"
                "import json; a,b,script=sys.argv[2:];"
                "print(json.dumps([[str(p) for p in resolve_project_roots("
                "f'git -C {a} commit -m x && git -C {b} push')],"
                "_guarded_mode(f'bash {script}'),staging_intent('git add -u && git commit -m x')[0],"
                "any(m in sys.modules for m in ('gate_lib','detect_lang','pre_tool_git_guard'))]))",
                left, right, script)
            self.assertEqual([[str(left), str(right)], "push", ["staged", "unstaged"], False], actual)


if __name__ == "__main__":
    unittest.main()
