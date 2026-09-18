#!/usr/bin/env python3
"""PostToolUse 钩子：AI 写完文件后自动跑对应语言的 linter。

这是 codeguard 插件的核心钩子——把规范检查从「提交前」前移到「写完即检」。

退出码：
- 0：通过（或非代码文件）
- 2：linter 失败（严格模式下阻塞 AI 继续；非严格模式仅警告）
- 124：linter 超时
- 127：linter 命令不存在
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (  # noqa: E402
    LANG_COMMANDS,
    detect_language,
    find_project_root,
    load_user_config,
)


def read_payload() -> dict:
    """兼容多种 hook payload 格式（ZCode/Codex/Claude）"""
    if sys.stdin.isatty():
        return {}
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return {}
    return data or {}


def extract_file_path(payload: dict) -> str:
    """从多种 payload 形态里抠文件路径"""
    candidates = [
        payload.get("file_path"),
        (payload.get("tool_input") or {}).get("file_path"),
        (payload.get("tool_input") or {}).get("path"),
        (payload.get("input") or {}).get("file_path"),
    ]
    for c in candidates:
        if c:
            return str(c)
    return ""


def should_skip(file_path: str, languages: list[str]) -> tuple[bool, str]:
    """返回 (skip, lang)：是否跳过本次 lint"""
    if not file_path:
        return True, ""
    lang = detect_language(file_path)
    if not lang:
        return True, ""
    if languages and lang not in languages:
        return True, lang
    return False, lang


def run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", f"command not found: {e}"


STATE_FILE = PLUGIN_ROOT / ".session_state.json"


def bump_state(lang: str, passed: bool, auto_fixed: bool = False) -> None:
    """累计本会话 lint 结果（Stop 钩子读取汇总）；写失败静默忽略"""
    state = {}
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        pass
    entry = state.setdefault(lang, {"total": 0, "passed": 0, "failed": 0, "auto_fixed": 0})
    entry["total"] += 1
    entry["passed" if passed else "failed"] += 1
    if auto_fixed:
        entry["auto_fixed"] += 1
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))
    except OSError:
        pass


def main() -> int:
    payload = read_payload()
    file_path = extract_file_path(payload)
    if not file_path:
        return 0

    cfg = load_user_config()
    enabled = cfg.get("enabled_languages", [])
    if enabled == ["auto"] or enabled == []:
        # auto 模式：从项目根检测
        project_root = find_project_root(os.getcwd()) or Path(os.getcwd())
        languages = enabled if enabled and enabled != ["auto"] else None
    else:
        languages = enabled
        project_root = find_project_root(file_path) or Path(os.getcwd())

    skip, lang = should_skip(file_path, languages)
    if skip:
        return 0

    cmd_def = LANG_COMMANDS.get(lang)
    if not cmd_def:
        return 0

    timeout = cfg.get("lint_timeout_seconds", 120)
    print(f"[codeguard] lint {lang}: {file_path}")

    rc, stdout, stderr = run(cmd_def["lint"], cwd=project_root, timeout=timeout)
    if rc == 0:
        print(f"[codeguard] \u2705 {lang} lint passed: {file_path}")
        bump_state(lang, passed=True)
        return 0

    # linter 失败 → 尝试自动修复
    if cfg.get("auto_fix_on_save", True):
        print(f"[codeguard] \u26a0\ufe0f  {lang} lint failed, attempting auto-fix...")
        frc, fs, fe = run(cmd_def["format"], cwd=project_root, timeout=timeout + 60)
        if frc == 0:
            print(f"[codeguard] \u2705 auto-fix succeeded, re-running lint...")
            bump_state(lang, passed=False, auto_fixed=True)
            rc, stdout, stderr = run(cmd_def["lint"], cwd=project_root, timeout=timeout)

    bump_state(lang, passed=False)

    # 报告失败
    print(f"\n[codeguard] \u274c {lang} lint failed for {file_path}", file=sys.stderr)
    if stdout:
        print(stdout[-3000:], file=sys.stderr)
    if stderr:
        print(stderr[-3000:], file=sys.stderr)
    print(f"\n[codeguard] fix with: {' '.join(cmd_def['format'])}", file=sys.stderr)

    return 2 if cfg.get("strict_mode", True) else 0


if __name__ == "__main__":
    sys.exit(main())
