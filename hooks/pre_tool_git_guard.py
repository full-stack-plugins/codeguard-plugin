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

from detect_lang import (  # # ensure_user_path/load_user_config 实际定义：scripts/paths.py、scripts/user_config.py
    ensure_user_path,
    load_user_config,
)
from gate_lib import (
    check_commit_safety,
    format_safety_report,
    gate_directive,
    record_skip_event,
    run_gate,
    should_suppress_event,
    skip_gate_via_git_config,  # 规范实现已上移 gate_lib（UPS 也要用）
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
            # cd 到非 git 目录（如 workspace 根）后边界失效——回退 cwd（与 shell 语义一致）
            last_cd = target if target.is_dir() and _is_git_repo(target) else None
            continue
        tokens = seg.split()
        if len(tokens) >= 2 and tokens[0] == "git" and tokens[1] in ("commit", "push"):
            root = last_cd or (Path(os.getcwd()) if _is_git_repo(Path(os.getcwd())) else None)
            if root and root not in roots:
                roots.append(root)
    # 有意行为（勿"修掉"）：cd 到非 git 目录后 last_cd=None，git 段回退用
    # 调用方 cwd——与 shell 语义一致（进非仓后 git 在原 cwd 执行）。
    return roots


def _segment_is_git_side_effect(seg: str) -> bool:
    """单个命令段是不是 git commit/push：git 为分隔符后的命令词。

    首 token 剥一层包裹引号（`bash -c "git commit …"` 切段后首词是 `"git`）。
    """
    tokens = seg.strip().split()
    if len(tokens) < 2:
        return False
    first = tokens[0].strip("\"'")
    second = tokens[1].strip("\"'")
    return first == "git" and second in ("commit", "push")


_SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".mjs", ".js", ".ts")
_INTERPRETERS = ("bash", "sh", "zsh", "python", "python3", "node")


def _command_indirect(command: str) -> bool:
    """间接提交识别：解释器跑的脚本文件 / -c 内联代码里含 git commit|push。

    硬门禁此前只看外层命令文本——`bash runner.sh`（脚本体内 git commit）
    完全绕过拦截，实测用 /tmp runner 连推 4 次全部漏网。这里对一层间接
    做静态扫描：脚本文本按同款分隔符切段后，任一段段首为 git+commit|push
    即命中。更深的 subprocess 拼接不在静态扫描能力内，不夸大承诺。
    """
    import re
    for seg in re.split(r"&&|\|\||;|\n", command):
        tokens = seg.strip().split()
        if not tokens:
            continue
        prog = tokens[0].rsplit("/", 1)[-1]
        if prog not in _INTERPRETERS:
            continue
        rest = tokens[1:]
        if "-c" in rest:
            body = " ".join(rest[rest.index("-c") + 1:])
            if any(_segment_is_git_side_effect(s)
                   for s in re.split(r"&&|\|\||;|\n", body)):
                return True
            continue
        for tok in rest:
            if tok.startswith("-"):
                continue
            target = Path(tok)
            if not target.is_file() or target.suffix not in _SCRIPT_SUFFIXES:
                break
            try:
                if target.stat().st_size > 1_000_000:
                    break
                body = target.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                break
            if any(_segment_is_git_side_effect(s)
                   for s in re.split(r"&&|\|\||;|\n", body)):
                return True
            break
    return False


def is_guarded(command: str) -> bool:
    """精确匹配 git commit/push：直接命令 + 一层解释器间接。

    直接：子串匹配会误伤命令文本里的数据（payload、调试脚本内容含
    "git push" 字面量），所以按分隔符切段、git 必须是段首命令词。
    间接：解释器执行的脚本/内联代码按同规则扫一层（见 _command_indirect）。
    """
    import re
    if any(_segment_is_git_side_effect(seg)
           for seg in re.split(r"&&|\|\||;|\n", command)):
        return True
    return _command_indirect(command)


def main() -> int:
    ensure_user_path()
    payload = read_payload()
    command = extract_command(payload)
    if not command or not is_guarded(command):
        return 0

    # 双副本去重：宿主带事件 id（生产 payload 的 tool_use_id）时第二副本静默；
    # 测试 payload 不带 id → 不去重，保持旧行为。
    event_id = payload.get("tool_use_id")
    if event_id and should_suppress_event(f"pre:{event_id}"):
        return 0

    if os.environ.get("CODEGUARD_SKIP_GATE"):
        record_skip_event("env")
        return 0

    cfg = load_user_config()
    roots = resolve_project_roots(command)
    if not roots:
        return 0
    if any(skip_gate_via_git_config(r) for r in roots):
        record_skip_event("skipGate")
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
