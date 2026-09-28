#!/usr/bin/env python3
"""PreToolUse 宿主适配器：AI 执行 git commit/push 前输出硬门禁决策。"""
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
from codeguard.git_guard_application import evaluate_git_command
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
from codeguard.hook_state import completed_event, record_completed_event, session_scope
from codeguard.repository_policy import env_skip_gate
from detect_lang import ensure_user_path, load_user_config
from gate_lib import (  # 兼容原有 Python 导入接口
    check_commit_safety,
    format_safety_report,
    gate_directive,
    record_skip_event,
    run_gate,
    skip_gate_via_git_config,
)

__all__ = [
    "GUARDED_PATTERNS", "_analyze_segment", "_collect_subs", "_command_indirect",
    "_fallback_roots", "_filter_fallback_roots", "_flatten_substitutions", "_git_c_path",
    "_git_seg_parts", "_git_side_effect_sub", "_guarded_mode", "_is_git_repo",
    "_normalize_segment", "_repo_root_of", "_segment_is_git_side_effect", "chain_skip_gate",
    "check_commit_safety", "extract_command", "format_safety_report", "gate_directive",
    "inline_skip_gate", "is_guarded", "main", "read_payload", "record_skip_event",
    "resolve_project_roots", "run_gate", "skip_gate_via_git_config", "staging_intent",
]

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
    command = tool_input.get("command")
    return str(command) if command else ""


def main() -> int:
    payload = read_payload()
    with session_scope(payload):
        key = ("pre:" + str(payload["tool_use_id"]) + ":" + extract_command(payload)
               if payload.get("tool_use_id") else None)
        cached = completed_event(key) if key else None
        if cached is not None and cached["code"] == 2:
            _deliver(cached["code"], cached["stdout"], cached["stderr"])
            return cached["code"]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = _main(payload)
        out, err = stdout.getvalue(), stderr.getvalue()
        # 只复用阻断结果，硬门放行和未验证永远重跑准确快照。
        delivered = _deliver(code, out, err)
        if key and code == 2 and delivered:
            record_completed_event(key, code, out, err)
        return code


def _deliver(code: int, stdout: str, stderr: str) -> bool:
    """刷新宿主输出后才允许缓存；已知拦截不能因输出故障降为放行。"""
    try:
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        sys.stdout.flush()
        sys.stderr.flush()
    except (OSError, UnicodeError, ValueError):
        if code == 2:
            return False
        raise
    return True


def _main(payload: dict) -> int:
    ensure_user_path()
    result = evaluate_git_command(
        extract_command(payload),
        cwd=Path(os.getcwd()),
        load_config=load_user_config,
        bypass_env=env_skip_gate(),
    )
    for context in result.contexts:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": context,
        }}, ensure_ascii=False))
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open，不阻断宿主工具
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
