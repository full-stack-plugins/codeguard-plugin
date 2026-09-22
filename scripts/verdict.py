"""共享结果语义：执行状态不等于代码结论，原始退出码始终保留。"""
from __future__ import annotations

import re
from pathlib import Path

PASS, FAIL, UNVERIFIED, SKIPPED, PLANNED = "PASS", "FAIL", "UNVERIFIED", "SKIPPED", "PLANNED"
_ENV_ERROR = re.compile(
    r"Could not resolve dependencies|Could not find artifact|DependencyResolutionException|"
    r"Cannot find module|ModuleNotFoundError|Unknown lifecycle phase|"
    r"Could not resolve all|Could not find or load main class|invalid configuration",
    re.IGNORECASE,
)


def lint_verdict(rc: int, command: list[str], output: str = "") -> tuple[str, str]:
    """按工具契约归一结论；只允许明确的成功返回 PASS。"""
    if rc == 0:
        return PASS, "检查执行成功"
    if rc in (124, 127) or rc < 0 or _ENV_ERROR.search(output):
        reason = {124: "检查超时", 127: "工具不存在"}.get(rc, "工具链执行异常")
        return UNVERIFIED, reason
    tool = Path(command[0]).name if command else ""
    # pylint 的 2 为 error 位；不得沿用 ESLint/ruff 的配置错误语义。
    if tool == "pylint":
        return (UNVERIFIED, "pylint 用法错误") if rc & 32 else (FAIL, "pylint 发现违规")
    if rc == 1 or (tool == "cargo" and rc == 101):
        return FAIL, "检查发现违规"
    return UNVERIFIED, f"工具退出 {rc}，没有可确认的检查结论"


def result(language: str, status: str, reason: str, *, exit_code: int = 0, **details) -> dict:
    """兼容 passed，同时携带不会在 CLI/MCP 间丢失的明确状态。"""
    return {"language": language, "status": status, "reason": reason,
            "passed": status == PASS, "exit_code": exit_code, **details}


def exit_status(results: list[dict]) -> int:
    """聚合优先级：发现违规 > 无法验证 > 已完成/无须检查。"""
    statuses = {r.get("status", PASS if r.get("passed") else FAIL) for r in results}
    if FAIL in statuses:
        return 2
    if not statuses or statuses & {UNVERIFIED, PLANNED}:
        return 1
    return 0
