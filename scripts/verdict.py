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


def _strip_dialect_blocks(output: str) -> str:
    """剥离 ShellCheck 方言不支持(SC1071)的诊断块，保留同批其余诊断。

    shellcheck 输出按 `In <file> line N:` 分块；SC1071 是"工具不支持该方言"
    的固有限制，整块丢弃。不得因此掩盖同批 .sh 的真问题——剥离后仍有剩余
    诊断就按剩余内容重判。
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for ln in output.splitlines():
        if ln.startswith("In ") and " line " in ln and current:
            blocks.append(current)
            current = [ln]
        else:
            current.append(ln)
    if current:
        blocks.append(current)
    kept = [ln for blk in blocks if not any("SC1071" in x for x in blk) for ln in blk]
    return "\n".join(kept).strip()


_CODE_RE = re.compile(r"\b([A-Z]{1,4}\d{2,4})\b")


def finding_signatures(output: str) -> set[str]:
    """从 linter 输出提取可跨运行比较的"发现签名"集合。

    优先用工具规则码（SC2086/F401/…）；无规则码的工具回退"归一化描述行"
    （剥 file:line:col 前缀与数字）——同一发现在改动前后必须签名一致，
    基线比对才有意义。提不出签名时返回空集，由调用方拒绝豁免。
    """
    sigs = set(_CODE_RE.findall(output))
    if sigs:
        return sigs
    for ln in output.splitlines():
        s = ln.strip()
        if not s or s.startswith(("In ", "^", "~", "#!")):
            continue
        norm = re.sub(r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+:\d+(:\d+)?", "", s)
        norm = re.sub(r"\d+", "#", norm).strip()
        if norm:
            sigs.add(norm)
    return sigs


def lint_verdict(rc: int, command: list[str], output: str = "") -> tuple[str, str]:
    """按工具契约归一结论；只允许明确的成功返回 PASS。"""
    if rc == 0:
        return PASS, "检查执行成功"
    # ShellCheck 不支持 zsh/dash 之外的方言（SC1071 是 error 级固有限制）：
    # 先剥离这些诊断块——只有剥离后**无剩余**才算"方言能力边界"归 UNVERIFIED；
    # 仍有剩余诊断就按剩余内容判，不许掩盖同批真问题。
    if "SC1071" in output:
        rest = _strip_dialect_blocks(output)
        if not rest:
            return UNVERIFIED, "ShellCheck 不支持该脚本方言（SC1071）"
        output = rest
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
