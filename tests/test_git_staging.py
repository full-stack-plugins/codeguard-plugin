"""暂存意图按仓库与 Git pathspec 绑定，观察过程不能修改真实 index。"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]
import pre_tool_git_guard
from git_snapshot import validation_tree


class GitStagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-staging-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", "/dev/null")
        self.put("base.txt", "base")
        self.git("add", ".")
        self.git("commit", "-qm", "base")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              check=True, timeout=10).stdout

    def put(self, name, text="new"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def snapshot(self, command, expected, *, absent=()):
        index = self.root / ".git/index"
        before = index.read_bytes()
        with patch.object(Path, "cwd", return_value=self.root):
            lanes, extra = pre_tool_git_guard.staging_intent(command)
        with validation_tree(self.root, lanes=lanes, extra=extra) as (snapshot, changed):
            self.assertCountEqual(expected, changed)
            for name in expected:
                path = self.root / name
                if path.exists():
                    self.assertEqual(path.read_bytes(), (snapshot / name).read_bytes())
                else:
                    self.assertFalse((snapshot / name).exists())
            for name in absent:
                self.assertFalse((snapshot / name).exists())
        self.assertEqual(before, index.read_bytes(), "观察不能重写用户 index")

    def test_exclusion_is_applied_to_whole_pathspec_set(self):
        self.put("a.py")
        self.put("private/b.py")
        self.snapshot("git add '*.py' ':(exclude)private/**' && git commit -m x",
                      ["a.py"], absent=["private/b.py"])

    def test_literal_magic_does_not_expand_file_name_twice(self):
        self.put("star*.py")
        self.put("star-other.py")
        self.snapshot("git add ':(literal)star*.py' && git commit -m x",
                      ["star*.py"], absent=["star-other.py"])

    def test_quoted_filename_and_git_directory_with_spaces(self):
        self.put("space dir/a b.py")
        self.snapshot(f"git -C {shlex.quote(str(self.root / 'space dir'))} add 'a b.py' && git commit -m x",
                      ["space dir/a b.py"])

    def test_relative_cd_and_git_c_are_composed(self):
        self.put("pkg/src/a.py")
        self.put("root.py")
        self.snapshot("cd pkg && git -C src add '*.py' && git commit -m x",
                      ["pkg/src/a.py"], absent=["root.py"])

    def test_scoped_update_excludes_untracked_but_includes_deletions(self):
        self.put("pkg/a.py", "old")
        removed = self.put("pkg/removed.py")
        self.git("add", ".")
        self.git("commit", "-qm", "tracked")
        self.put("pkg/a.py", "changed")
        removed.unlink()
        self.put("pkg/new.py")
        self.snapshot("git add -u pkg && git commit -m x", ["pkg/a.py", "pkg/removed.py"], absent=["pkg/new.py"])

    def test_add_dot_from_subdirectory_does_not_stage_siblings(self):
        self.put("pkg/a.py")
        self.put("outside.py")
        self.snapshot("cd pkg && git add . && git commit -m x", ["pkg/a.py"], absent=["outside.py"])

    def test_force_add_includes_ignored_target_only(self):
        self.put(".gitignore", "ignored/\n")
        self.put("ignored/a.py")
        self.put("ignored/b.txt")
        self.snapshot("git add -f 'ignored/*.py' && git commit -m x", ["ignored/a.py"], absent=["ignored/b.txt"])

    def test_real_hook_does_not_copy_another_repositories_extra_paths(self):
        other = self.root.parent / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
        (other / "safe.txt").write_text("safe")
        self.put(".env", "fixture-only")
        self.put("safe.txt", "untracked")
        command = f"git -C {other} add -A && git -C {other} commit -m x && git -C {self.root} commit -m x"
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        result = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                                input=json.dumps(payload), cwd=self.root, capture_output=True,
                                text=True, check=False, timeout=15,
                                env={**os.environ, "CODEGUARD_HOME": str(self.root.parent / "state")})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(".env", result.stderr)

    def test_real_hook_detects_sensitive_glob_before_add_without_touching_index(self):
        self.put("private/a.pem", "fixture-only")
        before = (self.root / ".git/index").read_bytes()
        payload = {"tool_name": "Bash", "tool_input": {"command":
                   f"git -C {self.root} add 'private/*.pem' && git -C {self.root} commit -m x"}}
        result = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                                input=json.dumps(payload), cwd=self.root.parent, capture_output=True,
                                text=True, check=False, timeout=15,
                                env={**os.environ, "CODEGUARD_HOME": str(self.root.parent / "state")})
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("private/a.pem", result.stderr)
        self.assertEqual(before, (self.root / ".git/index").read_bytes())

    def test_hook_normalizes_subdirectory_to_worktree_root(self):
        self.put("space dir/a.pem", "fixture-only")
        commands = [(f"git -C {shlex.quote(str(self.root / 'space dir'))} add '*.pem' && "
                     f"git -C {shlex.quote(str(self.root / 'space dir'))} commit -m x"),
                    "cd 'space dir' && git add '*.pem' && git commit -m x"]
        for command in commands:
            with self.subTest(command=command):
                payload = {"tool_name": "Bash", "tool_input": {"command": command}}
                result = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                                        input=json.dumps(payload), cwd=self.root, capture_output=True,
                                        text=True, check=False, timeout=15,
                                        env={**os.environ, "CODEGUARD_HOME": str(self.root.parent / "state")})
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn("space dir/a.pem", result.stderr)

    def test_unpredictable_add_is_visible_unverified_not_silent_pass(self):
        for option in ("-p", "--pathspec-from-file=paths.txt"):
            with self.subTest(option=option):
                payload = {"tool_name": "Bash", "tool_input": {"command": f"git add {option} && git commit -m x"}}
                result = subprocess.run([sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                                        input=json.dumps(payload), cwd=self.root, capture_output=True,
                                        text=True, check=False, timeout=15,
                                        env={**os.environ, "CODEGUARD_HOME": str(self.root.parent / "state")})
                self.assertEqual(0, result.returncode)
                self.assertIn("暂存", result.stderr + result.stdout)
                self.assertIn("UNVERIFIED", result.stderr + result.stdout)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
