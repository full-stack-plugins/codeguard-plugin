#!/usr/bin/env python3
"""UserPromptSubmit 宿主适配器：软提醒注入，不阻断用户消息。"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

from codeguard import prompt_application, prompt_policy
from codeguard.hook_state import session_scope
from detect_lang import (  # 兼容原有 Python 导入接口
    LANG_COMMANDS,
    detect_languages,
    ensure_user_path,
    find_project_root,
    load_user_config,
)
from gate_lib import (  # 兼容原有 Python 导入接口
    check_commit_safety,
    format_safety_report,
    gate_directive,
    record_skip_event,
    run_gate,
    skip_gate_via_git_config,
    summarize_failures,
)

__all__ = [
    "LANG_COMMANDS", "QUESTION_MARKERS", "TRIGGER_PATTERNS", "check_commit_safety",
    "detect_languages", "ensure_user_path", "find_project_root", "format_safety_report",
    "gate_directive", "is_trigger", "load_user_config", "main", "notify", "read_payload",
    "read_user_text", "record_skip_event", "run_gate", "skip_gate_via_git_config",
    "summarize_failures",
]

TRIGGER_PATTERNS = prompt_policy.TRIGGER_PATTERNS
QUESTION_MARKERS = prompt_policy.QUESTION_MARKERS
is_trigger = prompt_policy.is_trigger
_detect_languages_in_text = prompt_policy.detect_languages_in_text
_non_git_note = prompt_application.non_git_note


def notify(title: str, message: str) -> None:
    """macOS 系统通知；其他宿主仅依赖对话上下文。"""
    if sys.platform != "darwin":
        return
    import subprocess
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")[:200]
    with contextlib.suppress(OSError):
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_message}" with title "{safe_title}" sound name "Pop"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def read_payload() -> dict:
    """stdin 只读取一次，兼容 user_prompt 与 prompt 字段。"""
    if sys.stdin.isatty():
        return {}
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_user_text() -> str:
    payload = read_payload()
    return str(payload.get("user_prompt") or payload.get("prompt") or "")


def main() -> int:
    payload = read_payload()
    with session_scope(payload):
        return _main(payload)


def _main(payload: dict) -> int:
    user_text = str(payload.get("user_prompt") or payload.get("prompt") or "")
    if not is_trigger(user_text):
        return 0
    ensure_user_path(from_login_shell=True)
    result = prompt_application.evaluate_prompt(
        user_text,
        project_root=find_project_root(os.getcwd()),
        session_id=payload.get("session_id"),
        load_config=load_user_config,
        bypass_env=bool(os.environ.get("CODEGUARD_SKIP_GATE")),
    )
    if result.notification:
        notify(*result.notification)
    if result.additional_context is not None:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": result.additional_context,
        }}, ensure_ascii=False))
    sys.stdout.flush()
    result.acknowledge()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open，不阻断用户消息
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
