#!/usr/bin/env python3
"""PreToolUse 钩子：AI 执行 git commit / git push 前硬门禁。

这是「修完才能推」的硬保证：AI 即使忽略 UserPromptSubmit 的软引导指令，
真正执行 git 命令时也会在这里被拦下。exit 2 + stderr 的反馈会作为工具
结果回给 AI（Claude/ZCode 协议），AI 看到后继续修复并重试——循环闭环：
失败 → AI 修 → 再 commit → 通过 → 放行。

通过时完全静默（exit 0，零输出）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

from detect_lang import ensure_user_path, find_project_root, load_user_config  # noqa: E402
from gate_lib import gate_directive, run_gate  # noqa: E402

# 拦截的 git 子命令（避免误拦 git status/diff/log 等只读命令）
GUARDED_PATTERNS = ("git commit", "git push")


def read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return {}


def extract_command(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    cmd = tool_input.get("command")
    return str(cmd) if cmd else ""


def resolve_project_root(command: str) -> Path:
    """门禁检查的目录边界 = 被提交的仓库，不是会话 cwd。

    多仓聚合工作区（如 codeup 下几十个子仓）里会话 cwd 是根目录，
    递归 lint 会把无关子仓的文件连坐进来；git 命令通常带 `cd <repo> &&`，
    从命令里提取目标目录，找不到再回退 cwd。
    """
    import re
    m = re.search(r"(?:^|&&|\s;\s)\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)", command)
    if m:
        target = m.group(1).strip("\"'")
        if Path(target).is_dir():
            return Path(target)
    return find_project_root(os.getcwd()) or Path(os.getcwd())


def is_guarded(command: str) -> bool:
    low = command.lower()
    return any(p in low for p in GUARDED_PATTERNS)


def main() -> int:
    ensure_user_path()
    if os.environ.get("CODEGUARD_SKIP_GATE"):
        return 0

    payload = read_payload()
    command = extract_command(payload)
    if not command or not is_guarded(command):
        return 0

    cfg = load_user_config()
    project_root = resolve_project_root(command)
    failures, _skipped = run_gate(project_root, cfg)

    if not failures:
        return 0

    # 硬拦截：stderr 作为工具结果反馈给 AI，AI 修复后重试本命令
    print(gate_directive(failures), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
