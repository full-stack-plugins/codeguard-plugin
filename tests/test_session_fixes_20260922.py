"""2026-09-22 会话反馈批次回归（源码 v0.8.3）：锁五项实测发现。

来自一次真实多仓修复会话（codeguard 在主工作树拦了 3 次、又被 4 种命令形态
静默绕过、且长报告把指令段截掉）：
1. 守卫绕过：`$()`/反引号/`for…do`/`if…;then` 不命中；`git -C`/`FOO=1 git`/
   `sudo git` 命中但 resolve_project_roots=[] → main 静默放行（0.8.2 半修击穿）。
2. commit 面：并行会话的未暂存 WIP 不该拦纯 `git commit`；`git add` 链要把
   "即将暂存"的文件并进检查面；lanes/extra 必须进缓存键。
3. 报告结构：整调用声明/skipGate 必须在首行综述紧后（宿主从尾部截断长报告），
   总长受控，被压细节保尾部日志路径。
4. 存量归因：delta 下项目级命令报错文件全在改动集外 → skipped 不拦。
5. 版本积压：SessionStart 检出本机 cache 存在更新版本副本。
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
import pre_tool_git_guard as guard  # noqa: E402
import scope  # noqa: E402
from env_check import version_backlog_note  # noqa: E402


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def _fresh_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="cg-sess-"))
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    return root


def _run_guard(command: str, cwd: Path) -> subprocess.CompletedProcess:
    home = Path(tempfile.mkdtemp(prefix="cg-home-"))
    env = {**os.environ, "CODEGUARD_HOME": str(home), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(PLUGIN / "hooks" / "pre_tool_git_guard.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True, cwd=cwd, env=env, timeout=120,
    )


class GuardSubstitutionTests(unittest.TestCase):
    """#1a：命令替换与控制结构里的 git 调用必须命中（实测四种形态全部漏网）。"""

    def test_dollar_paren_forms_guarded(self) -> None:
        for cmd, want in (
            ("ro=$(git push origin b 2>&1)", "push"),
            ("out=`git commit -m y`", "commit"),
            ("x=$(echo $(git push))", "push"),
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(guard._guarded_mode(cmd), want)

    def test_loop_and_control_structures_guarded(self) -> None:
        for cmd, want in (
            ("for B in a; do git push origin $B; done", "push"),
            ("if git push origin b; then echo ok; fi", "push"),
            ("while git commit -m x; do sleep 1; done", "commit"),
            ("git commit -m x || { echo retry; }", "commit"),
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(guard._guarded_mode(cmd), want)

    def test_negatives_stay_unguarded(self) -> None:
        # 只锁无命令替换时的词法阴性：echo 普通文本/只读 git 不命中。
        # 引号内散文含 `then do git push` 的展开是声明过的边界（宁可多拦）。
        self.assertFalse(guard.is_guarded('echo "git push 是危险命令"'))
        self.assertFalse(guard.is_guarded("git status && ls"))
        self.assertFalse(guard.is_guarded("ls -la"))


class RootsNormalizationTests(unittest.TestCase):
    """#1b：resolve_project_roots 必须与 is_guarded 同源——否则 roots=[] 静默放行。

    0.8.2 实测：`git -C /repo commit`、`FOO=1 git push`、`sudo git push`
    is_guarded=True 但 roots=[] → main() 首道闸直接 return 0。
    """

    def test_normalized_forms_resolve_roots(self) -> None:
        here = str(PLUGIN)
        for cmd in (
            f"git -C {here} commit -m x",
            f"FOO=1 git -C {here} push origin b",
            f"sudo git -C {here} push origin b",
            f"ro=$(git -C {here} push origin b 2>&1)",
            "git commit -m x",
        ):
            with self.subTest(cmd=cmd):
                roots = guard.resolve_project_roots(cmd)
                self.assertTrue(roots, f"roots=[] 即静默放行: {cmd}")
                self.assertEqual(roots[0], PLUGIN)

    def test_explicit_c_path_wins_over_cwd(self) -> None:
        other = Path(tempfile.mkdtemp(prefix="cg-other-"))
        _git(other, "init", "-q")
        roots = guard.resolve_project_roots(f"git -C {other} commit -m x")
        # -C 路径经 resolve() 规范化（macOS /var → /private/var symlink），
        # 与 tempfile 的字面路径比较必须先 resolve 两侧
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].resolve(), other.resolve())

    def test_multi_cd_boundary_kept(self) -> None:
        # run_all 同款断言的 worktree 等价：cd 边界 + 无 git 段为空
        roots = guard.resolve_project_roots(
            f"cd /tmp && x && cd {PLUGIN} && git commit -m t"
        )
        self.assertIn(PLUGIN, roots)
        self.assertNotIn(Path("/tmp"), roots)
        self.assertEqual(guard.resolve_project_roots("ls -la && echo done"), [])


class StagingIntentTests(unittest.TestCase):
    """#2：commit 面按命令链预测；工作树无关 WIP 不进面；extra 并入。"""

    def test_plain_commit_is_staged_only(self) -> None:
        lanes, extra = guard.staging_intent("git commit -m t")
        self.assertEqual(lanes, ("staged",))
        self.assertEqual(extra, [])

    def test_add_all_widens_to_three_lanes(self) -> None:
        for cmd in ("git add -A && git commit -m t",
                    "git add . && git commit -m t",
                    "git commit -am t"):
            with self.subTest(cmd=cmd):
                lanes, _ = guard.staging_intent(cmd)
                self.assertEqual(lanes, ("staged", "unstaged", "untracked")
                                 if "add" in cmd else ("staged", "unstaged"))

    def test_add_explicit_path_becomes_extra(self) -> None:
        repo = _fresh_repo()
        (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        prev = Path.cwd()
        os.chdir(repo)
        try:
            lanes, extra = guard.staging_intent("git add a.py && git commit -m t")
        finally:
            os.chdir(prev)
        self.assertEqual(lanes, ("staged",))
        self.assertEqual(extra, ["a.py"])

    def test_changed_files_honors_lanes_and_extra(self) -> None:
        repo = _fresh_repo()
        (repo / "base.py").write_text("x = 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "i")
        (repo / "base.py").write_text("x = 2\n", encoding="utf-8")     # 未暂存
        (repo / "staged.py").write_text("y = 1\n", encoding="utf-8")
        _git(repo, "add", "staged.py")
        (repo / "fresh.py").write_text("z = 1\n", encoding="utf-8")    # 未跟踪
        self.assertEqual(
            scope.changed_files(repo, lanes=("staged",)), ["staged.py"]
        )
        self.assertEqual(
            scope.changed_files(repo, lanes=("staged",), extra=["fresh.py"]),
            ["fresh.py", "staged.py"],
        )
        self.assertEqual(
            scope.changed_files(repo),
            ["base.py", "fresh.py", "staged.py"],
            "默认三路（软门禁宽口径）保持",
        )

    def test_lanes_and_extra_enter_cache_key(self) -> None:
        repo = _fresh_repo()
        (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        # 缓存键含 HEAD——空仓 rev-parse 失败返回 None，必须先有提交
        _git(repo, "commit", "-q", "-m", "i")
        k_staged = gate_lib._gate_cache_key(repo, ["python"], lanes=("staged",))
        k_all = gate_lib._gate_cache_key(repo, ["python"],
                                         lanes=("staged", "unstaged", "untracked"))
        k_extra = gate_lib._gate_cache_key(repo, ["python"], lanes=("staged",),
                                           extra=["b.py"])
        self.assertNotEqual(k_staged, k_all,
                            "窄面 pass 被宽面缓存复用 = 绕过")
        self.assertNotEqual(k_staged, k_extra)


@unittest.skipUnless(__import__("shutil").which("shellcheck"), "shellcheck 未安装")
class EndToEndFaceTests(unittest.TestCase):
    """e2e：真实钩子进程——本会话两个摩擦点的直接锁。"""

    def test_git_c_commit_is_blocked(self) -> None:
        """0.8.2 击穿：git -C 命中 is_guarded 但 roots=[] 静默放行。"""
        repo = _fresh_repo()
        (repo / "bad.sh").write_text("#!/bin/bash\nif [ $x = y ]; then true; fi\n",
                                     encoding="utf-8")
        _git(repo, "add", "-A")
        outside = Path(tempfile.mkdtemp(prefix="cg-outside-"))
        r = _run_guard(f"git -C {repo} commit -m t", outside)
        self.assertEqual(r.returncode, 2, r.stderr[:400])

    def test_plain_commit_ignores_unstaged_parallel_wip(self) -> None:
        """本会话实测：只暂存自己的文件，工作树里别人的未暂存 WIP 不得拦。"""
        repo = _fresh_repo()
        (repo / "good.sh").write_text('#!/bin/bash\nx="ok"\necho "$x"\n', encoding="utf-8")
        _git(repo, "add", "good.sh")
        (repo / "parallel-wip.sh").write_text(
            "#!/bin/bash\nif [ $x = y ]; then true; fi\n", encoding="utf-8")  # 未暂存坏文件
        r = _run_guard("git commit -m t", repo)
        self.assertEqual(r.returncode, 0,
                         f"无关未暂存 WIP 不得拦纯 commit: {r.stderr[:400]}")

    def test_dollar_paren_commit_blocked(self) -> None:
        repo = _fresh_repo()
        (repo / "bad.sh").write_text("#!/bin/bash\nif [ $x = y ]; then true; fi\n",
                                     encoding="utf-8")
        _git(repo, "add", "-A")
        r = _run_guard("ro=$(git commit -m t 2>&1)", repo)
        self.assertEqual(r.returncode, 2, r.stderr[:400])


class DirectiveFrontLoadTests(unittest.TestCase):
    """#3：指令前置 + 总长上限 + 保尾日志路径（宿主从尾部截断实测）。"""

    def _long_failures(self) -> list:
        long_detail = ("javax.annotation stuff\n" * 40
                       + "/abs/path/Ddd4j.java:7: error: package does not exist\n"
                       + "…（截断，共 41 行；完整输出: /tmp/codeguard-gate-x-java.log）")
        return [
            ("java", long_detail, "mvn spotless:apply", "见 docs/LANGUAGES.md"),
            ("shell", "SC2086: double quote\n" * 30 + "完整输出: /tmp/g-shell.log",
             "shfmt -w .", "brew install"),
        ]

    def test_directive_fragments_come_before_details(self) -> None:
        text = gate_lib.gate_directive(self._long_failures())
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("codeguard ❌ 提交门禁未通过："))
        self.assertEqual(lines.count(lines[0]), 1, "综述不得在细节中重复")
        first_detail = text.index("【")
        self.assertLess(text.index("整个工具调用没有执行"), first_detail)
        self.assertLess(text.index("skipGate"), first_detail)
        self.assertLess(text.index("拆成两次独立的工具调用"), first_detail)
        self.assertIn("具体问题", text)
        self.assertIn("怎么修", text)
        self.assertIn("先征得用户同意", text)
        self.assertNotIn("无需向用户确认", text)

    def test_total_length_capped_and_log_tail_survives(self) -> None:
        text = gate_lib.gate_directive(self._long_failures())
        self.assertLessEqual(len(text), gate_lib.REPORT_MAX_CHARS + 200,
                             f"总长 {len(text)} 超过硬上限")
        self.assertIn("/tmp/codeguard-gate-x-java.log", text,
                      "被压缩 detail 的尾部日志路径不得截掉")
        self.assertIn("/tmp/g-shell.log", text)

    def test_format_failure_report_contract_unchanged(self) -> None:
        """run_all unit 契约：综述一行、不重复、细节含问题与修法。"""
        r = gate_lib.format_failure_report(
            [("shell", "SC2086: double quote\nSC2154: unassigned", "shfmt -w .", "brew")]
        )
        first, rest = r.splitlines()[0], "\n".join(r.splitlines()[1:])
        self.assertTrue(0 < len(first) <= 80 and "\n" not in first)
        self.assertNotIn(first, rest)
        self.assertIn("SC2086", rest)
        self.assertIn("怎么修", rest)


class StaleAttributionTests(unittest.TestCase):
    """#4：delta 下报错文件全在改动集外 → skipped；有交集/无法归因 → failure。"""

    def setUp(self) -> None:
        self.repo = _fresh_repo()
        (self.repo / "old.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "new.py").write_text("y = 2\n", encoding="utf-8")

    def test_bare_filename_outside_changeset_is_stale(self) -> None:
        out = "old.py:1:1: E501 line too long\nold.py:2:2: E501 again"
        note = gate_lib._stale_attribution(out, self.repo, "python", ["new.py"])
        self.assertIsNotNone(note)
        self.assertIn("存量文件", note)
        self.assertIn("old.py", note)

    def test_absolute_path_is_normalized_and_counted(self) -> None:
        out = f"{self.repo}/old.py:1:1: error"
        note = gate_lib._stale_attribution(out, self.repo, "python", ["new.py"])
        self.assertIsNotNone(note)
        self.assertIn("old.py", note)

    def test_intersection_keeps_failure(self) -> None:
        out = "new.py:1:1: E501"
        self.assertIsNone(
            gate_lib._stale_attribution(out, self.repo, "python", ["new.py"])
        )

    def test_unattributable_keeps_failure(self) -> None:
        for out in ("no file mentions", "SC2086:1 weird token"):
            with self.subTest(out=out):
                self.assertIsNone(
                    gate_lib._stale_attribution(out, self.repo, "python", ["new.py"])
                )


class VersionBacklogTests(unittest.TestCase):
    """#5：SessionStart 版本积压检测（纯函数）。"""

    def setUp(self) -> None:
        self.cache = Path(tempfile.mkdtemp(prefix="cg-cache-"))
        (self.cache / "partme-ai" / "codeguard" / "0.3.4").mkdir(parents=True)
        (self.cache / "full-stack-plugins" / "codeguard" / "0.5.4").mkdir(parents=True)

    def test_stale_current_gets_note_with_newest(self) -> None:
        note = version_backlog_note("0.3.4", self.cache)
        self.assertIsNotNone(note)
        self.assertIn("0.5.4", note)
        self.assertIn("2 份", note)

    def test_current_newest_silent(self) -> None:
        self.assertIsNone(version_backlog_note("0.5.4", self.cache))
        self.assertIsNone(version_backlog_note("0.9.0", self.cache))
        self.assertIsNone(version_backlog_note("1.0.0",
                                               Path(tempfile.mkdtemp(prefix="cg-nocache-"))))


class AppendFilesTests(unittest.TestCase):
    """#P2-6：项目级命令（mvn 等）不追加文件——追加会被当 goal 误拦。"""

    def test_mvn_not_appended_when_disabled(self) -> None:
        mvn = ["mvn", "-q", "javadoc:jar", "-DskipTests"]
        got = scope.scope_cmd(mvn, PLUGIN, files=["a.java"], append_files=False)
        self.assertEqual(got, mvn)

    def test_bare_linter_still_appends_by_default(self) -> None:
        got = scope.scope_cmd(["yamllint", "."], PLUGIN, files=["a.yaml"])
        self.assertEqual(got, ["yamllint", "a.yaml"])

    def test_registry_marks_project_level_commands(self) -> None:
        reg = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        by_id = {lang["id"]: lang for lang in reg["languages"]}
        for lid in ("java", "kotlin", "rust", "go", "csharp", "vbnet",
                    "terraform", "protobuf", "elm"):
            with self.subTest(lang=lid):
                self.assertIs(by_id[lid].get("append_files"), False,
                              f"{lid} 是项目级命令，必须 append_files=false")


if __name__ == "__main__":
    unittest.main()
