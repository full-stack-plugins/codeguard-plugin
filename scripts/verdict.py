"""共享结果语义：执行状态不等于代码结论，原始退出码始终保留。"""
from __future__ import annotations

import re
from pathlib import Path

PASS, FAIL, UNVERIFIED, SKIPPED, PLANNED = "PASS", "FAIL", "UNVERIFIED", "SKIPPED", "PLANNED"
# 工具链/环境自身不兼容的特征——不是代码违规，归 UNVERIFIED 绝不拦提交。
# 每条都来自会话实测原文（hermes/easydoc 两仓 2026-09-22 误拦复现）：
#   - Maven 3 读不了 POM 4.1.0（'modelVersion' ... is newer than ...）
#   - JDK 26 不支持 --release 8（error: release version 1.8 not supported）
#   - javac target 与当前 JDK 不匹配（error: invalid target release）
#   - 字节码高于当前 JVM（UnsupportedClassVersionError / class file version）
#   - 依赖构件不可解析、goal 用法错、配置损坏
_ENV_ERROR = re.compile(
    r"Could not resolve dependencies|Could not find artifact|DependencyResolutionException|"
    r"Cannot find module|ModuleNotFoundError|Unknown lifecycle phase|"
    r"Could not resolve all|Could not find or load main class|invalid configuration|"
    r"'modelVersion' of '[^']*' is newer than the versions supported|"
    r"requires a newer version of Maven|"
    r"error: release version [\d.]+ not supported|release version [\d.]+ not supported|"
    r"error: invalid target release|invalid target release:|"
    r"UnsupportedClassVersionError|class file version|"
    r"has been compiled by a more recent version",
    re.IGNORECASE,
)


def lint_verdict(rc: int, command: list[str], output: str = "") -> tuple[str, str]:
    """按工具契约归一结论；只允许明确的成功返回 PASS。"""
    if rc == 0:
        return PASS, "检查执行成功"
    if rc in (124, 127) or rc < 0 or _ENV_ERROR.search(output):
        reason = {124: "检查超时", 127: "工具不存在"}.get(rc, "工具链执行异常")
        return UNVERIFIED, reason
    # ShellCheck 不支持 zsh/dash 之外的方言（SC1071 是 error 级固有限制）——
    # 把 .zsh 送进 shellcheck 必然报错，那不是代码违规而是工具能力边界。
    if "SC1071" in output:
        return UNVERIFIED, "ShellCheck 不支持该脚本方言（SC1071）"
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
