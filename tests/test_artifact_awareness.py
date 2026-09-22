"""构建产物认知测试（v0.11.1）：单一事实源清单 + 四条生效通道。

需求来源：用户实测「codeguard 得知道哪些是构建产物，不需要进行检测」。
两类永久红实测：target/**/apidocs/javadoc.sh（java 门禁自己生成、shell 门禁
必红）与 target/site/jacoco/*.html（html 门禁必红）；html 门禁旧 `-exec … {} +`
形态在产物数百个时把整串换行路径塞进单参数（`xargs: insufficient space`）。

锁四件事：
1. 清单单一事实源：scope.FULL_SCAN_EXCLUDES 完备，入库面（GUARD）由它派生；
2. 注入器三形态全覆盖：-print0 / -exec / 无 NUL 锚（c 的 -o 组已加括号）；
3. changed_files 过滤产物、PostToolUse 对产物路径静默跳过；
4. html 门禁改 NUL 全管道，不再存在换行→单参数的溢出面。
"""
from __future__ import annotations

import json
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

# 双副本/历史漂移中真实缺失过的产物目录（扫描面曾缺前 14 个，入库面曾缺 upstream）
CRITICAL_ARTIFACTS = (
    "target", "build", "dist", "out", "node_modules", "coverage", ".next",
    ".nuxt", ".gradle", "vendor", "upstream", "env", ".venv", ".tox",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".eggs",
    "htmlcov", ".turbo", ".parcel-cache", ".terraform",
)


class CanonicalListTests(unittest.TestCase):
    """1) 单一事实源清单：完备 + 入库面派生不漂移。"""

    def test_critical_artifacts_all_listed(self) -> None:
        missing = [d for d in CRITICAL_ARTIFACTS if d not in scope.FULL_SCAN_EXCLUDES]
        self.assertEqual(missing, [], f"清单缺产物目录: {missing}")

    def test_guard_derived_from_single_source(self) -> None:
        self.assertEqual(
            gate_lib.GUARD_EXCLUDE_DIRS,
            set(scope.FULL_SCAN_EXCLUDES) | {".idea", ".vscode"},
            "入库面必须由单一事实源派生，禁止手抄第二份",
        )

    def test_is_build_artifact_covers_forms_and_edges(self) -> None:
        yes = ("target/site/jacoco/x.html", "./target/a.sh", ".tox/x",
               "a/target/b.sh", "/abs/path/target/apidocs/i.html",
               "node_modules/p/index.html", "upstream/dep.py")
        no = ("src/main.py", "src/targeted/main.py", "docs/build-guide.md",
              "my-target-notes.txt")
        for p in yes:
            with self.subTest(p=p):
                self.assertTrue(scope.is_build_artifact(p), p)
        for p in no:
            with self.subTest(p=p):
                self.assertFalse(scope.is_build_artifact(p), p)


class InjectionCoverageTests(unittest.TestCase):
    """2) 注入器三形态：只认 -print0 就有整族门禁漏网（html/c 实测漏）。"""

    def test_print0_form_anchor(self) -> None:
        expr = "find . -name '*.sh' -type f -print0 | xargs -0 -r shellcheck"
        out = scope._inject_find_excludes(expr)
        self.assertIn("-not -path '*/target/*'", out)
        self.assertLess(out.index("-not -path '*/target/*'"), out.index("-print0"))

    def test_exec_form_anchor(self) -> None:
        """旧 html gate 形态：无 -print0，曾在 v0.10 注入下整族漏网。"""
        expr = ("find . \\( -name '*.html' \\) -type f "
                "-exec grep -L '<%' {} + | xargs -0 -r htmlhint")
        out = scope._inject_find_excludes(expr)
        self.assertIn("-not -path '*/target/*'", out)
        self.assertLess(out.index("-not -path '*/target/*'"), out.index("-exec"))

    def test_no_nul_anchor_form_after_path(self) -> None:
        """c/objc 无 -print0/-exec：锚在 find <path> 之后，且 -o 组必须带括号。"""
        reg = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        by = {l["id"]: l for l in reg["languages"]}
        c_gate = " ".join(by["c"]["gate"])
        self.assertIn("\\( -name '*.c' -o -name '*.h' \\)", c_gate,
                     "c gate 的 -o 组必须加括号，否则注入的 -not -path 被 OR 短路")
        out = scope._inject_find_excludes(c_gate)
        self.assertIn("-not -path '*/target/*'", out)
        self.assertLess(out.index("-not -path '*/target/*'"), out.index("\\("))

    def test_idempotent_on_new_html_form(self) -> None:
        reg = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        html_gate = " ".join(next(l for l in reg["languages"] if l["id"] == "html")["gate"])
        once = scope._inject_find_excludes(html_gate)
        twice = scope._inject_find_excludes(once)
        self.assertEqual(once, twice)


class HtmlGatePipelineTests(unittest.TestCase):
    """4) html 门禁 NUL 全管道：换行→单参数溢出面必须消失。"""

    def setUp(self) -> None:
        reg = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        self.gate = " ".join(next(l for l in reg["languages"] if l["id"] == "html")["gate"])

    def test_nul_pipeline_end_to_end_shape(self) -> None:
        self.assertIn("-print0", self.gate)
        self.assertIn("xargs -0 -r grep -L '<%'", self.gate)
        self.assertIn("tr '\\n' '\\0'", self.gate)
        self.assertNotIn("-exec grep", self.gate, "旧 -exec 换行形态必须移除")

    def test_materialized_html_gate_excludes_target(self) -> None:
        reg = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
        html_gate = " ".join(next(l for l in reg["languages"] if l["id"] == "html")["gate"])
        cmd = scope.scope_cmd(["bash", "-c", html_gate], PLUGIN, full_excludes=True)
        self.assertIn("-not -path '*/target/*'", cmd[2])


class ChangedFilesFilterTests(unittest.TestCase):
    """3a) delta 面过滤：force-add 的产物文件不进检查集。"""

    def test_artifact_paths_filtered_from_changed_files(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="cg-art-"))
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
        (root / "target").mkdir()
        (root / "target" / "gen.sh").write_text("#!/bin/bash\nif [ $x = y ]; fi\n",
                                                encoding="utf-8")
        subprocess.run(["git", "add", "src/main.py"], cwd=root, check=True)
        subprocess.run(["git", "add", "-f", "target/gen.sh"], cwd=root, check=True)
        got = scope.changed_files(root, lanes=("staged",))
        self.assertEqual(got, ["src/main.py"],
                         f"产物必须被过滤，实际: {got}")

    def test_non_artifact_still_present(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="cg-art2-"))
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        self.assertEqual(scope.changed_files(root, lanes=("staged",)), ["a.py"])


class PostToolUseArtifactSkipTests(unittest.TestCase):
    """3b) PostToolUse：写到 target/ 的生成物静默跳过（不跑 linter、零输出）。"""

    def _run_hook(self, file_path: str) -> subprocess.CompletedProcess:
        import json as _json, os
        env = {**os.environ, "CODEGUARD_HOME": tempfile.mkdtemp(prefix="cg-h-"),
               "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(PLUGIN / "hooks" / "post_tool_lint.py")],
            input=_json.dumps({"tool_name": "Write",
                               "tool_input": {"file_path": file_path}}),
            capture_output=True, text=True, cwd=PLUGIN, env=env, timeout=120,
        )

    def test_generated_html_under_target_silently_skipped(self) -> None:
        fake = str(PLUGIN / "target" / "site" / "jacoco" / "report.html")
        r = self._run_hook(fake)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "", "产物跳过必须零输出")
        self.assertEqual(r.stderr.strip(), "")

    def test_generated_sh_under_target_silently_skipped(self) -> None:
        fake = str(PLUGIN / "target" / "reports" / "apidocs" / "javadoc.sh")
        r = self._run_hook(fake)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")


class SafetyDerivationTests(unittest.TestCase):
    """入库面派生的连带效果：upstream/ 依赖快照不再只被扫描面认识。"""

    def test_upstream_snapshot_flagged_as_unsafe(self) -> None:
        import subprocess as _sp
        root = Path(tempfile.mkdtemp(prefix="cg-up-"))
        _sp.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "upstream").mkdir()
        (root / "upstream" / "dep.py").write_text("y = 2\n", encoding="utf-8")
        _sp.run(["git", "add", "-A"], cwd=root, check=True)
        paths = [v[0] for v in gate_lib.check_commit_safety(root, "commit")]
        self.assertIn("upstream/dep.py", paths)


if __name__ == "__main__":
    unittest.main()
