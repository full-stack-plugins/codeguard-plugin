"""非 Shell 正文的 git 归因回归（2026-09-23 fix-release-chain-and-gate-attribution）。

锁定四件事：
1. JS 帮助文本（模板字符串里的 git 命令样例）不触发门禁——bump-plugin.mjs 实测误报；
2. node/python 真实间接 git 调用（exec/subprocess 形态）仍触发并按「不可建模」阻断；
3. Shell 脚本正文行为不变（可建模）；
4. 非 Shell 帮助文本里的 git config codeguard.skipGate 不构成豁免变更。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))

from codeguard.git_context import (
    GitIntentError,
    is_guarded,
    resolve_git_operations,
)
from codeguard.git_syntax import dynamic_git_effects

JS_HELP = """console.log(`release usage:
  cd <root> && git add -A && git commit -m "release: x" && git push
`);"""

JS_REAL = 'execFileSync("git", ["commit", "-m", "x"]);'
PY_REAL = "import subprocess\nsubprocess.run([\"git\", \"push\"])\n"
JS_SKIP_TEXT = 'console.log(`bypass: git config codeguard.skipGate true`);'


def _write(tmp: Path, name: str, text: str) -> Path:
    target = tmp / name
    target.write_text(text, encoding="utf-8")
    return target


class DetectionTests(unittest.TestCase):
    def test_js_help_text_not_guarded(self) -> None:
        script = _write(Path(tempfile.mkdtemp()), "help.mjs", JS_HELP)
        self.assertFalse(is_guarded(f"node {script}"))

    def test_node_real_git_call_guarded(self) -> None:
        script = _write(Path(tempfile.mkdtemp()), "real.mjs", JS_REAL)
        self.assertTrue(is_guarded(f"node {script}"))

    def test_python_subprocess_guarded(self) -> None:
        script = _write(Path(tempfile.mkdtemp()), "real.py", PY_REAL)
        self.assertTrue(is_guarded(f"python3 {script}"))

    def test_shell_script_still_modeled(self) -> None:
        repo = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True, check=False)
        script = _write(repo, "deploy.sh", "#!/bin/bash\ngit commit -m t\n")
        self.assertTrue(is_guarded(f"bash {script}"))
        operations = resolve_git_operations(f"bash {script}", cwd=repo)
        self.assertTrue(operations and operations[0].mode == "commit")

    def test_nons_shell_help_skip_text_is_not_config_change(self) -> None:
        self.assertEqual(dynamic_git_effects(JS_SKIP_TEXT), ([], None))

    def test_dynamic_call_forms_detected(self) -> None:
        subs, _ = dynamic_git_effects('os.system("git commit -m x")')
        self.assertEqual(subs, ["commit"])
        subs, _ = dynamic_git_effects('subprocess.run(["git", "push"])')
        self.assertEqual(subs, ["push"])
        subs, skip = dynamic_git_effects(
            'execFileSync("git", ["config", "codeguard.skipGate", "true"])')
        self.assertTrue(skip)

    def test_non_shell_real_call_resolves_to_unverified(self) -> None:
        script = _write(Path(tempfile.mkdtemp()), "real.mjs", JS_REAL)
        with self.assertRaises(GitIntentError):
            resolve_git_operations(f"node {script}")


class HeredocSemanticsTests(unittest.TestCase):
    """heredoc 正文按归属语义归因（2026-09-23 fix-heredoc-git-attribution 五态）。"""

    def test_python_heredoc_sample_text_not_guarded(self) -> None:
        cmd = "python3 - <<'PY'\ns = '''cd a && git add && git commit && git push%'''\nprint(s)\nPY"
        self.assertFalse(is_guarded(cmd))

    def test_unquoted_data_heredoc_substitution_guarded(self) -> None:
        self.assertTrue(is_guarded("cat <<EOF\n$(git push origin b)\nEOF"))

    def test_quoted_data_heredoc_literal_not_guarded(self) -> None:
        self.assertFalse(is_guarded("cat <<'EOF'\n$(git push origin b)\nEOF"))

    def test_shell_interpreter_heredoc_still_modeled(self) -> None:
        repo = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=repo, capture_output=True, check=False)
        cmd = "bash <<'SH'\ngit commit -m t\nSH"
        self.assertTrue(is_guarded(cmd))
        operations = resolve_git_operations(cmd, cwd=repo)
        self.assertTrue(operations and operations[0].mode == "commit")

    def test_direct_command_unchanged(self) -> None:
        self.assertTrue(is_guarded("git commit -m t"))


if __name__ == "__main__":
    unittest.main()
