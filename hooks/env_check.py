#!/usr/bin/env python3
"""SessionStart 宿主适配器：读取事件与本机插件配置，输出项目记忆。"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from codeguard import startup_application
from codeguard.reporting import plugin_version
from detect_lang import (  # 兼容原有 Python 导入接口
    LANG_COMMANDS,
    REGISTRY,
    detect_languages,
    ensure_user_path,
    find_project_root,
    load_user_config,
)

__all__ = [
    "LANG_COMMANDS",
    "REGISTRY",
    "detect_languages",
    "detect_linter_config",
    "ensure_user_path",
    "find_project_root",
    "load_user_config",
    "main",
    "notify",
    "version_backlog_note",
]

detect_linter_config = startup_application.detect_linter_config
version_backlog_note = startup_application.version_backlog_note


def notify(title: str, message: str) -> None:
    """macOS 系统通知；其他宿主静默。"""
    if sys.platform != "darwin":
        return
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")[:200]
    with contextlib.suppress(OSError):
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_message}" with title "{safe_title}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _enabled_plugin_orgs() -> tuple[str, ...]:
    """ZCode 宿主注册表只在适配器读取，其他宿主缺文件时无副作用。"""
    try:
        config = json.loads((Path.home() / ".zcode" / "cli" / "config.json").read_text(encoding="utf-8"))
        orgs = {
            key.split("@", 1)[1]
            for key in (config.get("plugins", {}) or {}).get("enabledPlugins", {})
            if key.startswith("codeguard@")
        }
        return tuple(sorted(orgs))
    except (OSError, ValueError, AttributeError):
        return ()


def main(payload: dict | None = None) -> int:
    from codeguard.hook_state import observe_once, session_scope
    session_id = (payload or {}).get("session_id")
    with session_scope(payload or {}):
        return observe_once(f"start:{session_id}" if session_id else None, lambda: _main(payload))


def _main(payload: dict | None = None) -> int:
    ensure_user_path(from_login_shell=True)
    project_root = find_project_root(os.getcwd()) or Path(os.getcwd())
    current = plugin_version()
    report = startup_application.build_startup_report(
        project_root,
        plugin_version="" if current == "unknown" else current,
        cache_root=Path.home() / ".zcode" / "cli" / "plugins" / "cache",
        enabled_plugin_orgs=_enabled_plugin_orgs(),
    )
    if report.notification:
        notify(*report.notification)
    if report.text:
        print(report.text)
    return 0


if __name__ == "__main__":
    try:
        payload: dict = {}
        if not sys.stdin.isatty():
            try:
                data = json.loads(sys.stdin.read())
                if isinstance(data, dict):
                    payload = data
            except (json.JSONDecodeError, ValueError):
                payload = {}
        sys.exit(main(payload))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open，不阻断宿主工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
