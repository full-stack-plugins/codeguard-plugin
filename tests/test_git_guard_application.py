"""PreToolUse 的 Git 决策返回结构化结果，不直接写宿主 stdout/stderr。"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "hooks")]

import pre_tool_git_guard


class GitGuardApplicationTests(unittest.TestCase):
    def test_shell_segments_only_split_real_control_operators(self):
        from codeguard.git_syntax import chain_skip_gate, split_shell_segments

        self.assertEqual(
            [('echo "docs; git config codeguard.skipGate true"', None),
             ('git commit -m "a && b"', '&&')],
            split_shell_segments(
                'echo "docs; git config codeguard.skipGate true" && git commit -m "a && b"'),
        )
        self.assertEqual(
            [(r'echo docs\; git config codeguard.skipGate true', None),
             ('git commit -m x', '&&')],
            split_shell_segments(r'echo docs\; git config codeguard.skipGate true && git commit -m x'),
        )
        self.assertFalse(chain_skip_gate('echo "docs; git config codeguard.skipGate true" && git commit'))
        self.assertFalse(chain_skip_gate(r'echo docs\; git config codeguard.skipGate true && git commit'))
        self.assertTrue(chain_skip_gate('git config codeguard.skipGate true && git commit'))

    def test_bash_c_commit_uses_invocation_repository(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-repo-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "bash -c 'git commit -m x'", cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)

    def test_bash_lc_commit_is_not_an_unguarded_wrapper(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-login-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "bash -lc 'git commit -m x'", cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)

    def test_bare_prefixes_do_not_hide_shell_commit(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-prefixed-shell-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            for prefix in ("FOO=1", "env FOO=1", "command", "sudo",
                           "sudo env FOO=1"):
                with self.subTest(prefix=prefix), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                    result = git_guard_application.evaluate_git_command(
                        f"{prefix} bash -c 'git commit -m x'", cwd=repo, load_config=dict)
                    self.assertEqual(2, result.exit_code)
                    self.assertIn(".env", result.stderr)
                    gate.assert_called_once()

    def test_prefixed_shell_staging_is_predicted_without_mutating_index(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-prefixed-add-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            before = (repo / ".git/index").read_bytes()
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "env FOO=1 bash -c 'git add .env && git commit -m x'",
                    cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)
            self.assertEqual(before, (repo / ".git/index").read_bytes())

    def test_script_argument_named_dash_c_is_not_interpreter_code(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-script-argv-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / "harmless.sh").write_text("echo hello\n", encoding="utf-8")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    "bash harmless.sh -c 'git commit -m x'", cwd=repo, load_config=dict)
            self.assertEqual(0, result.exit_code)
            gate.assert_not_called()

    def test_indirect_pure_push_does_not_inspect_uncommitted_index(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-push-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    "bash -c 'git push origin main'", cwd=repo, load_config=dict)
            self.assertEqual(0, result.exit_code, result.stderr)
            gate.assert_called_once()
            self.assertEqual("push", gate.call_args.kwargs["mode"])
            self.assertFalse(gate.call_args.kwargs["pending_commit"])

    def test_bash_c_add_predicts_sensitive_file_without_staging_it(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-add-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            before = (repo / ".git/index").read_bytes()
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "bash -c 'git add .env && git commit -m x'", cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)
            self.assertEqual(before, (repo / ".git/index").read_bytes())

    def test_shell_script_after_cd_binds_its_repository(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-cd-") as tmp:
            base = Path(tmp).resolve()
            caller = self._initialized_repo(base, "caller")
            target = self._initialized_repo(base, "target")
            (target / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(target), "add", ".env"],
                           check=True, capture_output=True)
            (target / "release.sh").write_text("git commit -m x\n", encoding="utf-8")
            for interpreter in ("bash", "env FOO=1 bash"):
                with self.subTest(interpreter=interpreter), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                    result = git_guard_application.evaluate_git_command(
                        f"cd {target} && {interpreter} release.sh", cwd=caller, load_config=dict)
                    self.assertEqual(2, result.exit_code)
                    self.assertIn(".env", result.stderr)
                    gate.assert_called_once()
                    self.assertEqual(target, gate.call_args.args[0])

    def test_outer_commit_does_not_hide_inner_shell_commit(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-mixed-") as tmp:
            base = Path(tmp).resolve()
            caller = self._initialized_repo(base, "caller")
            target = self._initialized_repo(base, "target")
            (caller / "README.md").write_text("next\n", encoding="utf-8")
            (target / ".env").write_text("SECRET=value\n", encoding="utf-8")
            for repo, name in ((caller, "README.md"), (target, ".env")):
                subprocess.run(["git", "-C", str(repo), "add", name],
                               check=True, capture_output=True)
            command = (f"git -C {caller} commit -m x && "
                       f"bash -c 'cd {target} && git commit -m x'")
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    command, cwd=caller, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)
            self.assertEqual([caller, target], [call.args[0] for call in gate.call_args_list])

    def test_parent_chain_bypass_covers_only_its_inner_repository(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-bypass-") as tmp:
            base = Path(tmp).resolve()
            first = self._initialized_repo(base, "first")
            second = self._initialized_repo(base, "second")
            for repo in (first, second):
                (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
                subprocess.run(["git", "-C", str(repo), "add", ".env"],
                               check=True, capture_output=True)
            command = (f"git -C {first} config codeguard.skipGate true && "
                       f"bash -c 'git -C {first} commit -m x' && "
                       f"git -C {second} commit -m x")
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    command, cwd=base, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)
            gate.assert_called_once()
            self.assertEqual(second, gate.call_args.args[0])

    def test_non_shell_indirect_git_text_is_explicitly_unverified(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-unknown-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / "opaque.py").write_text("git commit -m x\n", encoding="utf-8")
            with patch.object(git_guard_application, "run_gate") as gate:
                result = git_guard_application.evaluate_git_command(
                    "python3 opaque.py", cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn("Git 意图 UNVERIFIED", result.stderr)
            gate.assert_not_called()

    def test_indirect_skip_gate_mutation_cannot_borrow_persisted_bypass(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-config-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            subprocess.run(["git", "-C", str(repo), "config", "codeguard.skipGate", "true"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate") as gate:
                result = git_guard_application.evaluate_git_command(
                    "bash -c 'git config codeguard.skipGate false' && git commit -m x",
                    cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn("Git 意图 UNVERIFIED", result.stderr)
            gate.assert_not_called()

    def test_unmodelled_inner_staging_blocks_instead_of_reporting_soft_context(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-indirect-staging-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / "README.md").write_text("changed\n", encoding="utf-8")
            with patch.object(git_guard_application, "run_gate") as gate:
                result = git_guard_application.evaluate_git_command(
                    "bash -c 'git add -p && git commit -m x'", cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn("Git 意图 UNVERIFIED", result.stderr)
            gate.assert_not_called()

    def test_shell_add_then_outer_commit_cannot_lose_staging_intent(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-shell-add-outer-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            for command in ("bash -c 'git add .env' && git commit -m x",
                            "bash -c 'git add .env' && bash -c 'git commit -m x'"):
                with self.subTest(command=command), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                    result = git_guard_application.evaluate_git_command(
                        command, cwd=repo, load_config=dict)
                    self.assertEqual(2, result.exit_code)
                    self.assertIn("Git 意图 UNVERIFIED", result.stderr)
                    gate.assert_not_called()

    def test_shell_add_after_pure_push_is_not_a_commit_bypass(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-shell-add-after-push-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    "git push origin main && bash -c 'git add .env'",
                    cwd=repo, load_config=dict)
            self.assertEqual(0, result.exit_code, result.stderr)
            gate.assert_called_once()

    def test_real_hook_blocks_sensitive_add_inside_shell_wrapper(self):
        with tempfile.TemporaryDirectory(prefix="cg-hook-indirect-") as tmp:
            base = Path(tmp).resolve()
            repo = self._initialized_repo(base, "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            before = (repo / ".git/index").read_bytes()
            payload = {"tool_name": "Bash", "tool_use_id": "indirect-sensitive",
                       "tool_input": {"command": "bash -c 'git add .env && git commit -m x'"}}
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                input=json.dumps(payload), cwd=repo, capture_output=True, text=True,
                env={**os.environ, "CODEGUARD_HOME": str(base / "state")}, timeout=15, check=False)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn(".env", result.stderr)
            self.assertEqual(before, (repo / ".git/index").read_bytes())

    def test_real_hook_blocks_prefixed_shell_commit(self):
        with tempfile.TemporaryDirectory(prefix="cg-hook-prefixed-") as tmp:
            base = Path(tmp).resolve()
            repo = self._initialized_repo(base, "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            payload = {"tool_name": "Bash", "tool_use_id": "prefixed-sensitive",
                       "tool_input": {"command": "env FOO=1 bash -c 'git commit -m x'"}}
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                input=json.dumps(payload), cwd=repo, capture_output=True, text=True,
                env={**os.environ, "CODEGUARD_HOME": str(base / "state")}, timeout=15, check=False)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn(".env", result.stderr)

    @staticmethod
    def _initialized_repo(base: Path, name: str) -> Path:
        repo = base / name
        repo.mkdir()
        for args in (("init", "-q"), ("config", "user.email", "test@example.com"),
                     ("config", "user.name", "Test")):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
        (repo / "README.md").write_text("safe\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"],
                       check=True, capture_output=True)
        return repo

    def test_multi_repo_commit_does_not_include_other_repos_staged_file_in_push(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-per-repo-mode-") as tmp:
            base = Path(tmp).resolve()
            repos = [self._initialized_repo(base, "commit-repo"),
                     self._initialized_repo(base, "push-repo")]
            (repos[1] / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repos[1]), "add", ".env"],
                           check=True, capture_output=True)
            command = f"cd {repos[0]} && git commit -m next && cd {repos[1]} && git push origin main"
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    command, cwd=base, load_config=dict)
            self.assertEqual(0, result.exit_code, result.stderr)
            self.assertEqual(2, gate.call_count)
            self.assertEqual(
                [("commit", True), ("push", False)],
                [(call.kwargs["mode"], call.kwargs["pending_commit"]) for call in gate.call_args_list],
            )

    def test_inline_and_chain_bypass_do_not_bypass_another_repository(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-scoped-bypass-") as tmp:
            base = Path(tmp).resolve()
            first = self._initialized_repo(base, "first")
            second = self._initialized_repo(base, "second")
            (second / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(second), "add", ".env"],
                           check=True, capture_output=True)
            for prefix in ("git -c codeguard.skipGate=true commit -m x",
                           "git config codeguard.skipGate true && git commit -m x"):
                command = f"cd {first} && {prefix} && cd {second} && git commit -m x"
                with self.subTest(prefix=prefix), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])):
                    result = git_guard_application.evaluate_git_command(
                        command, cwd=base, load_config=dict)
                self.assertEqual(2, result.exit_code)
                self.assertIn(".env", result.stderr)

    def test_unset_before_commit_cancels_existing_repository_bypass(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-unset-bypass-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            subprocess.run(["git", "-C", str(repo), "config", "codeguard.skipGate", "true"],
                           check=True, capture_output=True)
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "git config --unset codeguard.skipGate && git commit -m x",
                    cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)

    def test_prefixed_unset_cancels_existing_repository_bypass(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-prefixed-unset-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            subprocess.run(["git", "-C", str(repo), "config", "codeguard.skipGate", "true"],
                           check=True, capture_output=True)
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate:
                result = git_guard_application.evaluate_git_command(
                    "env FOO=1 git config codeguard.skipGate false && git commit -m x",
                    cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)
            gate.assert_called_once()

    def test_prefixed_inline_bypass_stays_audited_and_scoped(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-prefixed-inline-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            for prefix in ("env FOO=1", "command"):
                with self.subTest(prefix=prefix), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate, \
                        patch.object(git_guard_application, "record_skip_event") as record:
                    result = git_guard_application.evaluate_git_command(
                        f"{prefix} git -c codeguard.skipGate=true commit -m x",
                        cwd=repo, load_config=dict)
                    self.assertEqual(0, result.exit_code, result.stderr)
                    self.assertTrue(any("内联豁免" in item for item in result.contexts))
                    gate.assert_not_called()
                    record.assert_called_once_with("inline-skipGate", repo)

    def test_inline_bypass_only_covers_its_own_operation(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-inline-once-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "git -c codeguard.skipGate=true commit -m first && git commit -m second",
                    cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)
            self.assertTrue(any("内联豁免" in context for context in result.contexts))

    def test_later_chain_bypass_does_not_retroactively_skip_commit(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-late-bypass-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    "git commit -m x && git config codeguard.skipGate true",
                    cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)

    def test_writing_other_config_file_does_not_bypass_repository(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-other-config-") as tmp:
            base = Path(tmp).resolve()
            repo = self._initialized_repo(base, "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            command = f"git config --file={base / 'other-config'} codeguard.skipGate true && git commit -m x"
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    command, cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)

    def test_unproven_chain_config_does_not_bypass_commit(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-config-flow-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            for separator in ("||", ";"):
                command = f"git config codeguard.skipGate true {separator} git commit -m x"
                with self.subTest(separator=separator), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])):
                    result = git_guard_application.evaluate_git_command(
                        command, cwd=repo, load_config=dict)
                self.assertEqual(2, result.exit_code)

    def test_quoted_config_text_does_not_bypass_commit(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-quoted-config-") as tmp:
            repo = self._initialized_repo(Path(tmp).resolve(), "repo")
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", ".env"],
                           check=True, capture_output=True)
            command = 'echo "docs; git config codeguard.skipGate true" && git commit -m x'
            with patch.object(git_guard_application, "run_gate", return_value=([], [])):
                result = git_guard_application.evaluate_git_command(
                    command, cwd=repo, load_config=dict)
            self.assertEqual(2, result.exit_code)
            self.assertIn(".env", result.stderr)

    def test_same_repo_commit_then_push_keeps_both_surfaces(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-same-repo-mode-") as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            command = "git commit -m next && git push origin main"
            with patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate, \
                    patch.object(git_guard_application, "check_commit_safety", return_value=[]):
                result = git_guard_application.evaluate_git_command(
                    command, cwd=repo, load_config=dict)
            self.assertEqual(0, result.exit_code, result.stderr)
            gate.assert_called_once()
            self.assertEqual("push", gate.call_args.kwargs["mode"])
            self.assertTrue(gate.call_args.kwargs["pending_commit"])

    def test_repository_skip_gate_does_not_bypass_another_repository(self):
        from codeguard import git_guard_application
        from codeguard.git_context import GitOperation

        first, second = Path("/first-repo"), Path("/second-repo")
        with patch.object(git_guard_application, "resolve_git_operations",
                          return_value=[GitOperation(first, "commit"),
                                        GitOperation(second, "commit")]), \
                patch.object(git_guard_application, "skip_gate_via_git_config",
                             side_effect=lambda root: root == first), \
                patch.object(git_guard_application, "staging_intent",
                             return_value=(("staged",), [])), \
                patch.object(git_guard_application, "run_gate", return_value=([], [])) as gate, \
                patch.object(git_guard_application, "check_commit_safety",
                             side_effect=lambda root, *_args, **_kwargs:
                             [(".env", "sensitive", "remove it")] if root == second else []), \
                patch.object(git_guard_application, "record_skip_event") as record:
            result = git_guard_application.evaluate_git_command(
                "git commit -m x", cwd=first, load_config=dict)
        self.assertEqual(2, result.exit_code)
        self.assertIn(".env", result.stderr)
        gate.assert_called_once()
        self.assertEqual(second, gate.call_args.args[0])
        record.assert_called_once_with("skipGate", first)

    def test_explicit_non_git_target_never_falls_back_to_callers_repo(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-explicit-target-") as tmp:
            base = Path(tmp).resolve()
            repo, plain = base / "repo", base / "plain"
            repo.mkdir()
            plain.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            for command in (f"cd {plain} && git push origin main",
                            f"git -C {plain} commit -m x"):
                with self.subTest(command=command), \
                        patch.object(git_guard_application, "run_gate", return_value=([], [])) as run_gate, \
                        patch.object(git_guard_application, "fallback_roots", return_value=[]) as fallback, \
                        patch.object(git_guard_application, "check_commit_safety", return_value=[]):
                    result = git_guard_application.evaluate_git_command(
                        command, cwd=repo, load_config=dict)
                    self.assertEqual(2, result.exit_code)
                    self.assertIn(str(plain), result.stderr)
                    self.assertIn("目标", result.stderr)
                    run_gate.assert_not_called()
                    fallback.assert_not_called()

    def test_explicit_git_c_overrides_non_git_cd_target(self):
        from codeguard.git_context import resolve_project_roots

        with tempfile.TemporaryDirectory(prefix="cg-explicit-override-") as tmp:
            base = Path(tmp).resolve()
            repo, plain = base / "repo", base / "plain"
            repo.mkdir()
            plain.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            roots = resolve_project_roots(
                f"cd {plain} && git -C {repo} commit -m x", cwd=repo)
            self.assertEqual([repo], roots)

    def test_staging_intent_uses_explicit_callers_cwd(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-staging-cwd-") as tmp:
            repo = Path(tmp).resolve()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            (repo / "new.py").write_text("print(1)\n", encoding="utf-8")
            with patch.object(Path, "cwd", return_value=repo.parent), \
                    patch.object(git_guard_application, "run_gate", return_value=([], [])) as run_gate, \
                    patch.object(git_guard_application, "check_commit_safety", return_value=[]):
                result = git_guard_application.evaluate_git_command(
                    "git add '*.py' && git commit -m x", cwd=repo, load_config=dict)
            self.assertEqual(0, result.exit_code)
            self.assertEqual(["new.py"], run_gate.call_args.kwargs["extra"])

    def test_git_root_observation_failure_is_not_fail_open(self):
        from codeguard import git_guard_application
        from git_snapshot import SnapshotError

        with patch.object(git_guard_application, "resolve_git_operations",
                          side_effect=SnapshotError("rev-parse failed")), \
                patch.object(git_guard_application, "fallback_roots") as fallback:
            result = git_guard_application.evaluate_git_command(
                "git commit -m x", cwd=Path.cwd(), load_config=dict)
        self.assertEqual(2, result.exit_code)
        self.assertIn("rev-parse failed", result.stderr)
        fallback.assert_not_called()

    def test_real_hook_blocks_explicit_non_git_target(self):
        with tempfile.TemporaryDirectory(prefix="cg-hook-target-") as tmp:
            base = Path(tmp).resolve()
            repo, plain = base / "repo", base / "plain"
            repo.mkdir()
            plain.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            payload = {"tool_name": "Bash", "tool_use_id": "explicit-target",
                       "tool_input": {"command": f"cd {plain} && git push origin main"}}
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks/pre_tool_git_guard.py")],
                input=json.dumps(payload), cwd=repo, capture_output=True, text=True,
                env={**os.environ, "CODEGUARD_HOME": str(base / "state")}, timeout=15, check=False)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn(str(plain), result.stderr)
        self.assertIn("目标 UNVERIFIED", result.stderr)

    def test_no_git_repository_blocks_with_diagnostic_without_printing(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-guard-app-") as tmp:
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(git_guard_application, "resolve_git_operations", return_value=[]), \
                    patch.object(git_guard_application, "fallback_roots", return_value=[]), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                result = git_guard_application.evaluate_git_command(
                    "git push", cwd=Path(tmp), load_config=dict)
        self.assertEqual(2, result.exit_code)
        self.assertIn("未检测到任何 git 仓", result.stderr)
        self.assertEqual((), result.contexts)
        self.assertEqual("", output.getvalue() + errors.getvalue())

    def test_inline_bypass_returns_context_and_audit_without_printing(self):
        from codeguard import git_guard_application

        with tempfile.TemporaryDirectory(prefix="cg-guard-inline-") as tmp:
            root = Path(tmp)
            output = io.StringIO()
            from codeguard.git_context import GitOperation

            with patch.object(git_guard_application, "resolve_git_operations",
                              return_value=[GitOperation(root, "commit", "inline-skipGate")]), \
                    patch.object(git_guard_application, "skip_gate_via_git_config", return_value=False), \
                    patch.object(git_guard_application, "record_skip_event") as record, \
                    contextlib.redirect_stdout(output):
                result = git_guard_application.evaluate_git_command(
                    "git -c codeguard.skipGate=true commit -m ok", cwd=root, load_config=dict)
        self.assertEqual(0, result.exit_code)
        self.assertIn("内联豁免", result.contexts[0])
        record.assert_called_once()
        self.assertEqual("", output.getvalue())

    def test_blocked_event_is_not_marked_complete_before_host_output(self):
        class BrokenOutput:
            def write(self, _text):
                raise OSError("host output unavailable")

        payload = {"tool_use_id": "event-1", "tool_input": {"command": "git commit -m x"}}

        def block(_payload):
            print("blocked")
            return 2

        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "_main", side_effect=block), \
                patch.object(pre_tool_git_guard, "completed_event", return_value=None), \
                patch.object(pre_tool_git_guard, "record_completed_event") as record, \
                patch.object(sys, "stdout", BrokenOutput()):
            self.assertEqual(2, pre_tool_git_guard.main())
        record.assert_not_called()

    def test_blocked_event_is_not_cached_if_host_flush_fails(self):
        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host flush unavailable")

        payload = {"tool_use_id": "event-2", "tool_input": {"command": "git commit -m x"}}

        def block(_payload):
            print("blocked")
            return 2

        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "_main", side_effect=block), \
                patch.object(pre_tool_git_guard, "completed_event", return_value=None), \
                patch.object(pre_tool_git_guard, "record_completed_event") as record, \
                patch.object(sys, "stdout", BrokenFlush()):
            self.assertEqual(2, pre_tool_git_guard.main())
        record.assert_not_called()

    def test_block_without_event_id_still_blocks_if_stderr_flush_fails(self):
        class BrokenFlush(io.StringIO):
            def flush(self):
                raise OSError("host stderr flush unavailable")

        def block(_payload):
            print("blocked", file=sys.stderr)
            return 2

        payload = {"tool_input": {"command": "git push"}}
        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "_main", side_effect=block), \
                patch.object(sys, "stderr", BrokenFlush()):
            self.assertEqual(2, pre_tool_git_guard.main())

    def test_cached_block_remains_blocked_if_replay_cannot_write(self):
        class BrokenOutput:
            def write(self, _text):
                raise OSError("host output unavailable")

        payload = {"tool_use_id": "event-3", "tool_input": {"command": "git push"}}
        cached = {"code": 2, "stdout": "blocked\n", "stderr": ""}
        with patch.object(pre_tool_git_guard, "read_payload", return_value=payload), \
                patch.object(pre_tool_git_guard, "completed_event", return_value=cached), \
                patch.object(pre_tool_git_guard, "_main") as run, \
                patch.object(sys, "stdout", BrokenOutput()):
            self.assertEqual(2, pre_tool_git_guard.main())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
