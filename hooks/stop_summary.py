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

# 钩子状态文件（由 post_tool_lint.py 写）
STATE_FILE = PLUGIN_ROOT / ".session_state.json"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def summarize(state: dict) -> str:
    if not state:
        return "[codeguard] 本次会话无 linter 记录（可能没有改代码文件）"
    lines = ["[codeguard] 本次会话代码 lint 检查总结", ""]
    for lang, info in state.items():
        total = info.get("total", 0)
        passed = info.get("passed", 0)
        failed = info.get("failed", 0)
        auto_fixed = info.get("auto_fixed", 0)
        lines.append(f"- {lang}: 共 {total} 次检查，{passed} 通过，{failed} 失败，{auto_fixed} 自动修复成功")
    return "\n".join(lines)


def main() -> int:
    state = load_state()
    print(summarize(state))
    # 会话结束清理状态
    try:
        STATE_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
