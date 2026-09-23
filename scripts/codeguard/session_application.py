"""会话结束应用服务：消费本会话统计，返回不依赖宿主的展示行。"""
from __future__ import annotations

from pathlib import Path

from .execution import execute
from .hook_state import state_path
from .repository_policy import skip_gate_via_git_config
from .storage import read_json, take_json


def load_state(legacy_state_file: Path) -> dict:
    """兼容只读访问旧状态路径；读取不消费记录。"""
    try:
        return read_json(state_path(legacy_state_file))
    except OSError:
        return {}


def summarize(state: dict) -> str:
    """将本次会话统计格式化为宿主无关的文本。"""
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


def skipgate_left_enabled(project_root: Path) -> bool:
    """提醒类观察；Git 或配置读取失败不改变 Stop 的退出协议。"""
    try:
        probe = execute(["git", "rev-parse", "--git-dir"], project_root, 10)
        if probe.failure or probe.returncode != 0:
            return False
        return skip_gate_via_git_config(project_root)
    except Exception:  # noqa: BLE001 — 可选提醒不得阻断会话结束
        return False


def consume_summary(legacy_state_file: Path, project_root: Path) -> tuple[str, ...]:
    """原子消费当前作用域状态，并返回需要由宿主输出的消息。"""
    state = take_json(state_path(legacy_state_file))
    lines = [summarize(state)]
    if skipgate_left_enabled(project_root):
        lines.append("[codeguard] ⚠️ git config codeguard.skipGate 仍为 true——该仓门禁处于豁免状态；"
                     "若绕过已完成，请执行 git config --unset codeguard.skipGate 恢复")
    return tuple(lines)
