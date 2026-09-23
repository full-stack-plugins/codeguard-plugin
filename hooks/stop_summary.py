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

# 现行状态目录在 ~/.codeguard（CODEGUARD_HOME 可覆盖）；插件根的旧文件
# 升版本即丢、双副本各存一半——load_state 优先新路径，回退读旧文件一次。
LEGACY_STATE_FILE = PLUGIN_ROOT / ".session_state.json"


def load_state() -> dict:
    from codeguard.hook_state import state_path
    from codeguard.storage import read_json
    try:
        return read_json(state_path(LEGACY_STATE_FILE))
    except OSError:
        return {}


def summarize(state: dict) -> str:
    lang_state = {k: v for k, v in state.items() if not k.startswith("_")}
    meta = {k: v for k, v in state.items() if k.startswith("_")}
    if not lang_state and not meta:
        return "[codeguard] 本次会话无 linter 记录（可能没有改代码文件）"
    lines = ["[codeguard] 本次会话代码 lint 检查总结", ""]
    for lang, info in lang_state.items():
        if not isinstance(info, dict):
            continue
        total = info.get("total", 0)
        passed = info.get("passed", 0)
        failed = info.get("failed", 0)
        auto_fixed = info.get("auto_fixed", 0)
        lines.append(f"- {lang}: 共 {total} 次检查，{passed} 通过，{failed} 失败，{auto_fixed} 自动修复成功")
    skip = meta.get("_skip") or {}
    if skip.get("count"):
        kinds = "、".join(f"{k}×{v}" for k, v in (skip.get("kinds") or {}).items())
        lines.append(f"- ⚠️ 本会话绕过门禁 {skip['count']} 次（{kinds}）——确认是用户明确要求，并尽快 git config --unset codeguard.skipGate")
    return "\n".join(lines)


def _skipgate_left_enabled() -> bool:
    """会话结束时提醒：仓库级豁免还开着（忘记 unset = 门禁永久静默失效）。"""
    try:
        import subprocess

        from gate_lib import skip_gate_via_git_config
        proc = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=Path.cwd(), capture_output=True, check=False, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return False
        return skip_gate_via_git_config(Path.cwd())
    except Exception:  # noqa: BLE001 — 提醒类检查，失败绝不影响 Stop
        return False


def main(payload: dict | None = None) -> int:
    from codeguard.hook_state import observe_once, session_scope
    session_id = (payload or {}).get("session_id")
    with session_scope(payload or {}):
        return observe_once(f"stop:{session_id}" if session_id else None, lambda: _main(payload))


def _main(payload: dict | None = None) -> int:
    from codeguard.hook_state import state_path
    from codeguard.storage import take_json
    state = take_json(state_path(LEGACY_STATE_FILE))
    print(summarize(state))
    if _skipgate_left_enabled():
        print("[codeguard] ⚠️ git config codeguard.skipGate 仍为 true——该仓门禁处于豁免状态；"
              "若绕过已完成，请执行 git config --unset codeguard.skipGate 恢复")
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
