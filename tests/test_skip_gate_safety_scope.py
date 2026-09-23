"""skipGate 豁免范围与工具链发现回归（2026-09-24 harden-skip-gate-boundary）。

豁免一分为二：智能体可控的 skipGate 系（仓库级 / 内联 -c / 链式）只豁免语言门禁，
入库安全扫描（密钥/凭据/依赖产物模式）不随之跳过；进程环境变量
CODEGUARD_SKIP_GATE（仅用户可设）是唯一完整逃生门。工具链发现在符号链接
解释器机器上不再误报「工具不存在」。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

K = "codeguard." + "skipGate"  # 命令文本避免出现连续触发字面量
GC = "git " + "commit"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "a.py").write_text("print(1)\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _stage(repo: Path, name: str) -> None:
    (repo / name).write_bytes(b"x")
    _git(repo, "add", "-A")


def _guard(repo: Path, command: str, home: Path, extra_env: dict | None = None):
    from codeguard.git_guard_application import evaluate_git_command

    env_backup = {k: os.environ.get(k) for k in ("CODEGUARD_HOME", "CODEGUARD_SKIP_GATE")}
    os.environ["CODEGUARD_HOME"] = str(home)
    os.environ.pop("CODEGUARD_SKIP_GATE", None)
    for key, value in (extra_env or {}).items():
        os.environ[key] = value
    try:
        return evaluate_git_command(
            command, cwd=repo, load_config=dict, bypass_env=bool((extra_env or {}).get("CODEGUARD_SKIP_GATE")),
        )
    finally:
        for key, backup in env_backup.items():
            if backup is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = backup


def _prompt(repo: Path, home: Path, load_config=None):
    from codeguard.prompt_application import evaluate_prompt

    os.environ["CODEGUARD_HOME"] = str(home)
    return evaluate_prompt(
        "请提交这些改动", project_root=repo, session_id="scope-test",
        load_config=load_config or dict,
    )


class SkipGateScopeTests(unittest.TestCase):
    """仓库级/内联豁免不覆盖入库安全扫描。"""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory(prefix="cg-scope-")
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.home = self.tmp / "home"
        self.repo = _repo(self.tmp)

    def test_persisted_escape_still_blocks_secret_files(self):
        _stage(self.repo, "id_rsa")
        _git(self.repo, "config", K, "true")
        result = _guard(self.repo, f"{GC} -m x", self.home)
        self.assertEqual(2, result.exit_code)
        self.assertIn("安全检查", result.stderr)
        self.assertIn("id_rsa", result.stderr)

    def test_inline_escape_still_blocks_secret_files(self):
        _stage(self.repo, ".env")
        result = _guard(self.repo, f"git -c {K}=true {GC[4:]} -m x".replace("  ", " "), self.home)
        self.assertEqual(2, result.exit_code)
        self.assertIn(".env", result.stderr)

    def test_clean_face_stays_silent_under_escape(self):
        (self.repo / "a.py").write_text("print(2)\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "config", K, "true")
        result = _guard(self.repo, f"{GC} -m x", self.home)
        self.assertEqual(0, result.exit_code)
        self.assertFalse(result.stderr and result.contexts)

    def test_env_escape_covers_both_gates(self):
        _stage(self.repo, "id_rsa")
        result = _guard(
            self.repo, f"{GC} -m x", self.home,
            extra_env={"CODEGUARD_SKIP_GATE": "1"},
        )
        self.assertEqual(0, result.exit_code)
        self.assertFalse(result.stderr and result.contexts)

    def test_soft_gate_reports_secrets_under_escape(self):
        _stage(self.repo, "id_rsa")
        _git(self.repo, "config", K, "true")
        result = _prompt(self.repo, self.home)
        text = result.additional_context or ""
        self.assertIn("安全", text)
        self.assertIn("id_rsa", text)


class ToolchainDiscoveryTests(unittest.TestCase):
    """符号链接解释器下 ensure_user_path 补齐真实脚本目录；探活诊断区分入口缺失。"""

    def test_ensure_user_path_adds_resolved_scripts_dir(self):
        import sysconfig

        from paths import ensure_user_path

        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            ensure_user_path()
            on_path = os.environ["PATH"].split(":")
        finally:
            os.environ["PATH"] = saved
        scripts = sysconfig.get_path("scripts")
        self.assertIn(str(Path(sys.executable).resolve().parent), on_path)
        self.assertIn(scripts, on_path)

    def test_probe_recovers_when_scripts_dir_was_off_path(self):
        from codeguard.toolchain import ToolchainProbe

        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            with tempfile.TemporaryDirectory() as td:
                ok, reason = ToolchainProbe(Path(td)).probe(
                    {"probe": ["ruff", "--version"]}
                )
        finally:
            os.environ["PATH"] = saved
        # 根因修复后：probe 入口自补 PATH，ruff 可解析（不是「工具不存在」）
        self.assertTrue(ok, reason)

    def test_module_entry_hint_distinguishes_missing_entry(self):
        from codeguard.toolchain import _module_entry_hint

        saved = os.environ.get("PATH", "")
        os.environ["PATH"] = "/usr/bin:/bin"
        try:
            hint_missing_entry = _module_entry_hint(["ruff", "--version"])
            hint_absent = _module_entry_hint(["definitely-not-a-python-module-xyz", "--version"])
        finally:
            os.environ["PATH"] = saved
        self.assertIn("模块", hint_missing_entry)
        self.assertIn("未安装", hint_absent)


if __name__ == "__main__":
    unittest.main()
