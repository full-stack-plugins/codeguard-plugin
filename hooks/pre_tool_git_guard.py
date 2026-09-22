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
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

from detect_lang import ensure_user_path, load_user_config  # # ensure_user_path/load_user_config 实际定义：scripts/paths.py、scripts/user_config.py
from gate_lib import (
    check_commit_safety,
    format_safety_report,
    gate_directive,
    run_gate,
)

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


def _is_git_repo(p: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--git-dir"],
            capture_output=True, check=False, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0


def resolve_project_roots(command: str) -> list[Path]:
    """顺序扫描命令链，收集每个 git commit/push 段各自的仓库边界。

    链式发布（cd plugins && git commit && cd minimax && git push）操作
    多个仓库——每个 git 段的边界 = 它之前最近的 cd（且必须是 git 仓）；
    无 cd 则用 cwd（需是 git 仓）。去重保序，找不到任何边界返回 []。
    """
    import re
    roots: list[Path] = []
    last_cd: Path | None = None
    for seg in re.split(r"&&|\|\||;|\n", command):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"cd\s+(\"[^\"]+\"|'[^']+'|\S+)", seg)
        if m:
            target = Path(m.group(1).strip("\"'"))
            if target.is_dir() and _is_git_repo(target):
                last_cd = target
            else:
                last_cd = None        # cd 到非 git 目录（如 workspace 根）后边界失效
            continue
        tokens = seg.split()
        if len(tokens) >= 2 and tokens[0] == "git" and tokens[1] in ("commit", "push"):
            root = last_cd or (Path(os.getcwd()) if _is_git_repo(Path(os.getcwd())) else None)
            if root and root not in roots:
                roots.append(root)
    return roots


def is_guarded(command: str) -> bool:
    """精确匹配 git commit/push：子串匹配会误伤命令文本里的数据。

    例如 payload JSON、调试脚本内容含 "git push" 字面量时，子串匹配会
    把 echo/debug 命令也拦下并触发全仓 lint（实测踩坑）。
    匹配规则：git 是管道/分隔符后的命令词，且子命令为 commit/push。
    """
    import re
    for seg in re.split(r"&&|\|\||;|\n", command):
        tokens = seg.strip().split()
        if len(tokens) >= 2 and tokens[0] == "git" and tokens[1] in ("commit", "push"):
            return True
    return False


def skip_gate_via_git_config(project_root: Path) -> bool:
    """仓库级豁免：git config codeguard.skipGate true。

    CODEGUARD_SKIP_GATE 环境变量设在用户 shell，传不进 ZCode 宿主起的
    hook 子进程（宿主环境独立）；git config 由本钩子进程在项目根读取，
    任何调用形态都可用。优先级：环境变量 > 仓库级 git config。
    """
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "codeguard.skipGate"],
            cwd=project_root, capture_output=True, check=False, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0 and proc.stdout.strip().lower() in ("true", "1", "yes")


def main() -> int:
    ensure_user_path()
    if os.environ.get("CODEGUARD_SKIP_GATE"):
        return 0

    payload = read_payload()
    command = extract_command(payload)
    if not command or not is_guarded(command):
        return 0

    cfg = load_user_config()
    roots = resolve_project_roots(command)
    if not roots:
        return 0
    if any(skip_gate_via_git_config(r) for r in roots):
        return 0

    # 每个被操作的仓库独立跑：linter 门禁 + 提交内容安全检查
    # （commit 查暂存区；push 查未推送提交的 diff，防已提交未发现的坏文件）
    reports = []
    for project_root in roots:
        failures, _skipped = run_gate(project_root, cfg)
        if failures:
            reports.append(gate_directive(failures))
        safety_mode = "push" if "git push" in command.lower() else "commit"
        violations = check_commit_safety(project_root, safety_mode)
        if violations:
            reports.append(format_safety_report(violations) + (
                "\n\n**给 AI 的强制指令**：先把上述文件移出版本库"
                "（git rm --cached + .gitignore），然后重新执行本次 git 命令；"
                "涉及密钥/凭据的必须提醒用户轮换，不能只删了事。"
            ))

    if not reports:
        return 0
    # 硬拦截：stderr 作为工具结果反馈给 AI，AI 修复后重试本命令
    print(("\n\n" + "=" * 20 + " 下一个仓库 " + "=" * 20 + "\n\n").join(reports), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
