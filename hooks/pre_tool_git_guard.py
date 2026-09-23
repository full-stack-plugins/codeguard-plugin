#!/usr/bin/env python3
"""PreToolUse 钩子：AI 执行 git commit / git push 前硬门禁。

这是「修完才能推」的硬保证：AI 即使忽略 UserPromptSubmit 的软引导指令，
真正执行 git 命令时也会在这里被拦下。exit 2 + stderr 的反馈会作为工具
结果回给 AI（Claude/ZCode 协议），AI 看到后继续修复并重试——循环闭环：
失败 → AI 修 → 再 commit → 通过 → 放行。

通过时完全静默（exit 0，零输出）。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

from codeguard.git_context import (
    _command_indirect,
    _fallback_roots,
    _filter_fallback_roots,
    _guarded_mode,
    _is_git_repo,
    _repo_root_of,
    is_guarded,
    resolve_project_roots,
    staging_intent,
)
from codeguard.git_syntax import (
    _analyze_segment,
    _collect_subs,
    _flatten_substitutions,
    _git_c_path,
    _git_seg_parts,
    _git_side_effect_sub,
    _normalize_segment,
    _segment_is_git_side_effect,
    chain_skip_gate,
    inline_skip_gate,
)

# 保留旧导入面；实现分别属于纯语法与仓库观察适配器。
__all__ = [
    "GUARDED_PATTERNS", "_analyze_segment", "_collect_subs", "_command_indirect",
    "_fallback_roots", "_filter_fallback_roots", "_flatten_substitutions", "_git_c_path",
    "_git_seg_parts", "_git_side_effect_sub", "_guarded_mode", "_is_git_repo",
    "_normalize_segment", "_repo_root_of", "_segment_is_git_side_effect", "chain_skip_gate",
    "extract_command", "inline_skip_gate", "is_guarded", "main", "read_payload",
    "resolve_project_roots", "staging_intent",
]

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
    skip_gate_via_git_config,  # 规范实现已上移 gate_lib（UPS 也要用）
)
from git_snapshot import SnapshotError

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




def main() -> int:
    from codeguard.hook_state import (
        completed_event,
        record_completed_event,
        session_scope,
    )
    payload = read_payload()
    with session_scope(payload):
        if not payload.get("tool_use_id"):
            return _main(payload)
        # 事件 ID 与命令、会话/worktree 一起绑定；只复用已结束的检查，
        # 第一个副本尚在检查时，第二个副本宁可重跑，也不能直接放行。
        key = "pre:" + str(payload["tool_use_id"]) + ":" + extract_command(payload)
        cached = completed_event(key)
        if cached is not None and cached["code"] == 2:
            sys.stdout.write(cached["stdout"])
            sys.stderr.write(cached["stderr"])
            return cached["code"]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = _main(payload)
        out, err = stdout.getvalue(), stderr.getvalue()
        # 只复用阻断结果，不缓存放行：无输出的 0 也可能来自显式豁免，
        # 而未验证的 0 必须重跑。不能把事件去重缓存当作准确快照的替代。
        if code == 2:
            record_completed_event(key, code, out, err)
        sys.stdout.write(out)
        sys.stderr.write(err)
        return code


def _main(payload: dict) -> int:
    ensure_user_path()
    command = extract_command(payload)
    mode = _guarded_mode(command) if command else None
    if mode is None:
        return 0

    if os.environ.get("CODEGUARD_SKIP_GATE"):
        record_skip_event("env")
        return 0

    cfg = load_user_config()
    roots = resolve_project_roots(command)
    # 静默跳过漏报修复：roots=[] 时扫描 cwd 一层子目录找 git 仓作兜底
    # （monorepo 模式：workspace 根目录下多仓时，从根目录直跑 git push 不
    # 经 cd 也能被覆盖）。找不到则向 #2 抛错，让 Agent 知晓绕过发生。
    fallback_note: str | None = None
    if not roots:
        fallback = _fallback_roots(Path(os.getcwd()))
        if fallback:
            roots = fallback
            fallback_note = (
                f"未检测到显式 cd 仓；兜底扫描 cwd 一层子目录找到 {len(fallback)} 个 git 仓"
            )
        else:
            # 输出明确错误而非静默 exit 0：避免 Agent/用户误以为门禁执行过。
            print(
                f"[codeguard] 未检测到任何 git 仓：cwd={os.getcwd()} 且命令链中无 cd <仓>。"
                f"请在 git push 前先 cd <仓路径>，或在仓库根设置 git config codeguard.skipGate true。"
                f"（已用兜底扫描 cwd 一层子目录，无 git 仓。）",
                file=sys.stderr,
            )
            return 2
    if fallback_note:
        # 兜底面收窄（会话实测误拦：无关仓存量违规连带拦提交）。全空 = 本次
        # 无可拦对象，审计后放行。
        before = len(roots)
        roots = _filter_fallback_roots(roots, mode, None)
        fallback_note += f"；提交面收窄 {before}→{len(roots)} 个仓"
        if not roots:
            record_skip_event("monorepo-fallback-empty", detail=fallback_note)
            return 0
        # 兜底走通：仅在会话状态记录（不进 stderr，避免噪音），Stop 摘要可见
        record_skip_event("monorepo-fallback", roots[0], detail=fallback_note)
    if any(skip_gate_via_git_config(r) for r in roots):
        record_skip_event("skipGate", roots[0])
        return 0
    # 单次内联豁免：`git -c codeguard.skipGate=true …` 是显式意图（不落配置、
    # 无残留），放行并留审计明细——比仓库级 config 更不易"忘记恢复"。
    if inline_skip_gate(command):
        record_skip_event("inline-skipGate", roots[0])
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext":
            "codeguard: 已通过内联豁免 `-c codeguard.skipGate` 放行本次提交"
            "（已审计记录，Stop 摘要可见）。"}}
        ))
        return 0
    # 链内设置豁免：`git config codeguard.skipGate true && … && git config --unset …`
    # 是文档推荐的自清理写法；此前整链被拦连 set 段都没跑成（首用必败）。
    if chain_skip_gate(command):
        record_skip_event("chain-skipGate", roots[0])
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext":
            "codeguard: 已通过链式豁免（set→提交→unset 同链）放行本次提交"
            "（已审计记录，Stop 摘要可见）。"}}
        ))
        return 0

    # 按命令链预测实际提交面（纯 commit → 仅 staged；add -A/-a → 三路），
    # 并入 git add 显式路径（add 尚未执行、暂存区还是旧的）。
    pending_commit = "commit" in _collect_subs(command)

    # 每个被操作的仓库独立跑：linter 门禁 + 提交内容安全检查
    # （commit 查暂存区；push 查未推送提交的 diff，防已提交未发现的坏文件）
    reports = []
    for project_root in roots:
        try:
            lanes, extra = staging_intent(command, project_root=project_root)
        except SnapshotError as exc:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "additionalContext":
                f"codeguard: git UNVERIFIED：{project_root} 无法准确预测暂存面：{exc}；"
                "请完成明确的暂存操作后单独提交，并复核检查结果。",
            }}, ensure_ascii=False))
            continue
        # 保留删除路径用于影响分析；单文件 linter 自行过滤不存在的文件。
        root_extra = list(extra)
        failures, _skipped = run_gate(
            project_root, cfg, mode=mode, lanes=lanes, extra=root_extra,
            exact=True, pending_commit=pending_commit,
        )
        if failures:
            # 版本自标识由 gate_directive 首行综述之后的第二行承担——
            # 此处不再前置横幅：stderr 首行必须是综述（三个契约测试锁定）。
            reports.append(gate_directive(failures, project_root=project_root))
        unknown = [s for s in _skipped if "本次改动未涉及" not in s and " SKIPPED:" not in s
                   and "markdown 风格告警" not in s]
        if unknown:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "additionalContext":
                "codeguard: 存在未验证项，不能宣称全部通过：" + "；".join(unknown),
            }}, ensure_ascii=False))
        violations = check_commit_safety(project_root, mode, lanes=lanes, extra=root_extra,
                                         pending_commit=pending_commit)
        if violations:
            reports.append(format_safety_report(violations) + (
                "\n\n**给 AI 的强制指令**：**密钥/凭据类**（.env、*.pem、id_* 等）"
                "立即 git rm --cached 并提醒用户轮换密钥，不能只删了事；"
                "**非密钥类**（依赖/产物目录、仓根 db/log 等）**先与用户确认**"
                "是否为有意入库的第一方代码或合法 fixture——确认属误入库才执行"
                "git rm --cached + .gitignore，确认后重新执行本次 git 命令。"
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
