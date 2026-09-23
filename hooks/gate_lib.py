"""旧 Hook 导入兼容面；检查、仓库策略、审计与反馈均委托到独立服务。"""
from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from codeguard.baseline import (
    _git,
    _mentioned_files,
    _stale_attribution,
    baseline_stale_finding,
)
from codeguard.gate import (
    GATE_CACHE_TTL,
    _gate_cache_key,
    _gate_cache_path,
    _worktree_fingerprint,
    run_gate,
)
from codeguard.gate import run_batch as _run_gate_uncached
from codeguard.hook_state import (
    codeguard_home,
    record_gate_decision,
    record_skip_event,
    session_state_path,
    should_suppress_event,
)
from codeguard.path_policy import (
    GUARD_EXCLUDE_DIRS,
    GUARD_EXCLUDE_FILES,
    GUARD_ROOT_ONLY_FILES,
)
from codeguard.reporting import (
    CODEGUARD_VERSION,
    REPORT_MAX_CHARS,
    _dependency_resolution_hint,
    _failure_detail_blocks,
    _log_path,
    _rule_summary,
    _squeeze,
    _truncate_detail,
    format_failure_report,
    format_safety_report,
    gate_directive,
    summarize_failures,
)
from codeguard.repository_policy import check_commit_safety, skip_gate_via_git_config
from codeguard.spec_validation import validate as _openspec_validate
from detect_lang import (
    LANG_COMMANDS,
    detect_language,
    detect_languages,
    get_overrides,
    probe_toolchain,
    project_uses_linter,
)
from scope import changed_files

__all__ = [
    "CODEGUARD_VERSION",
    "GATE_CACHE_TTL",
    "GUARD_EXCLUDE_DIRS",
    "GUARD_EXCLUDE_FILES",
    "GUARD_ROOT_ONLY_FILES",
    "LANG_COMMANDS",
    "PLUGIN_ROOT",
    "REPORT_MAX_CHARS",
    "_dependency_resolution_hint",
    "_failure_detail_blocks",
    "_gate_cache_key",
    "_gate_cache_path",
    "_git",
    "_log_path",
    "_mentioned_files",
    "_openspec_validate",
    "_rule_summary",
    "_run_gate_uncached",
    "_squeeze",
    "_stale_attribution",
    "_truncate_detail",
    "_worktree_fingerprint",
    "baseline_stale_finding",
    "changed_files",
    "check_commit_safety",
    "codeguard_home",
    "detect_language",
    "detect_languages",
    "format_failure_report",
    "format_safety_report",
    "gate_directive",
    "get_overrides",
    "probe_toolchain",
    "project_uses_linter",
    "record_gate_decision",
    "record_skip_event",
    "run_gate",
    "session_state_path",
    "should_suppress_event",
    "skip_gate_via_git_config",
    "summarize_failures",
]


def _java_executable_from_plan(plan: dict) -> str | None:
    """从 java_project.analyze 的产物里解析构建可执行文件。

    两条来源按优先级：
    1. 顶层 ``executable`` 键（java_project 正常产出）；
    2. 回退 ``commands[0].argv[0]``——历史版本的 java_project 只把
       wrapper 体现在计划命令里（实测 68c8a37 曾因此让 mvnw 感知成为
       死代码：消费者读的键生产者从不写）。
    非 mvn/gradle wrapper（如 codeguard.json 显式命令）不参与替换。
    """
    exe = plan.get("executable")
    if exe:
        return exe
    for cmd in plan.get("commands", []) or []:
        argv = cmd.get("argv") or []
        if argv and Path(argv[0]).name in ("mvnw", "gradlew"):
            return argv[0]
    return None
