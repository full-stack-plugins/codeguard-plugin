#!/usr/bin/env python3
"""Stop 钩子：会话结束前总结本次会话产生的代码规范问题。

让用户在关闭会话前能看到：
- 本次修改了哪些语言
- 哪些 linter 通过、哪些失败
- 自动修复成功的次数
- 残留需要手动处理的警告
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根

sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from codeguard import session_application

# 现行状态目录在 ~/.codeguard（CODEGUARD_HOME 可覆盖）；插件根的旧文件
# 升版本即丢、双副本各存一半——load_state 优先新路径，回退读旧文件一次。
LEGACY_STATE_FILE = PLUGIN_ROOT / ".session_state.json"


def load_state() -> dict:
    return session_application.load_state(LEGACY_STATE_FILE)


def summarize(state: dict) -> str:
    return session_application.summarize(state)


def _skipgate_left_enabled() -> bool:
    return session_application.skipgate_left_enabled(Path.cwd())


def main(payload: dict | None = None) -> int:
    from codeguard.hook_state import observe_once, session_scope
    session_id = (payload or {}).get("session_id")
    with session_scope(payload or {}):
        return observe_once(f"stop:{session_id}" if session_id else None, lambda: _main(payload))


def _main(payload: dict | None = None) -> int:
    prepared = session_application.prepare_summary(LEGACY_STATE_FILE, Path.cwd())
    for line in prepared.lines:
        print(line)
    sys.stdout.flush()
    prepared.acknowledge()
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
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
