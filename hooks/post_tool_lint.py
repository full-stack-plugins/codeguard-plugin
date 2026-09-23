"""PostToolUse 宿主适配器：保存反馈以 JSON 注入上下文，绝不阻断写文件。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from codeguard import save_application
from codeguard.hook_state import codeguard_home, session_scope
from detect_lang import (  # 兼容原有 Python 导入接口
    LANG_COMMANDS,
    detect_language,
    ensure_user_path,
    find_project_root,
    load_user_config,
    project_uses_linter,
)
from scope import is_build_artifact

__all__ = [
    "DEDUP_FILE", "LANG_COMMANDS", "bump_state", "detect_language", "ensure_user_path",
    "extract_file_path", "find_project_root", "is_build_artifact", "is_ejs_template",
    "load_user_config", "mac_notify", "main", "project_uses_linter", "read_payload",
    "run", "should_skip", "should_suppress_duplicate",
]

# 多个 marketplace 副本共享用户级去重状态；保留原测试/嵌入方的覆盖点。
DEDUP_FILE: Path | None = None


def _dedup_path() -> Path:
    return DEDUP_FILE or codeguard_home() / "file_dedup.json"


def _state_path() -> Path:
    return save_application.state_path()


def bump_state(lang: str, passed: bool, auto_fixed: bool = False) -> None:
    save_application.bump_state(lang, passed, auto_fixed)


def _notify_cooldown_ok(lang: str, cooldown_s: int = 60) -> bool:
    return save_application.notification_allowed(lang, cooldown_s)


def mac_notify(title: str, message: str) -> None:
    """macOS 通知；非 macOS 宿主由 JSON 上下文呈现问题。"""
    if sys.platform != "darwin":
        return
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")[:200]
    subprocess.Popen(
        ["osascript", "-e",
         f'display notification "{safe_message}" with title "{safe_title}" sound name "Pop"'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def should_suppress_duplicate(file_path: str, identity: str | None = None) -> bool:
    return save_application.should_suppress_duplicate(file_path, identity, _dedup_path())


is_ejs_template = save_application.is_ejs_template
run = save_application.run
should_skip = save_application.should_skip


def read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return {}


def extract_file_path(payload: dict) -> str:
    for candidate in (payload.get("file_path"),
                      (payload.get("tool_input") or {}).get("file_path"),
                      (payload.get("tool_input") or {}).get("path"),
                      (payload.get("input") or {}).get("file_path")):
        if candidate:
            return str(candidate)
    return ""


def main() -> int:
    payload = read_payload()
    with session_scope(payload):
        return _main(payload)


def _main(payload: dict) -> int:
    ensure_user_path()
    file_path = extract_file_path(payload)
    if not file_path:
        return 0
    cfg = load_user_config()
    project_root = find_project_root(os.getcwd()) or Path(os.getcwd())
    result = save_application.evaluate_save(file_path, project_root, cfg, store=_dedup_path())
    if result.additional_context is not None:
        message = {"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": result.additional_context,
        }}
        if result.system_message is not None:
            message["systemMessage"] = result.system_message
        print(json.dumps(message, ensure_ascii=False))
    result.acknowledge()
    if result.notification:
        lang, title, message = result.notification
        if _notify_cooldown_ok(lang):
            mac_notify(title, message)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open，不阻断 AI 写文件
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
