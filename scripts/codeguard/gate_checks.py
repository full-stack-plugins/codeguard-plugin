"""语言门禁检查：返回独立结果，不知道宿主、会话或缓存。"""
from __future__ import annotations

from pathlib import Path

from .baseline import baseline_stale_finding
from .discovery import detect_language, project_uses_linter
from .execution import execute
from .models import GateDecision, GateOutcome
from .planning import scoped_plan
from .registry import LANG_COMMANDS
from .reporting import _dependency_resolution_hint, _log_path, _truncate_detail
from .toolchain import ToolchainProbe
from .verdict import FAIL, PASS, SKIPPED, UNVERIFIED, lint_verdict

_ZSH_SKIP_NOTE = ("ShellCheck 不支持 zsh 方言，{n} 个 zsh 文件未送检。"
                  "修复：在每个 .zsh 文件头添加 `# shellcheck shell=bash` 注释后重试")


def _java_check(root: Path, cfg: dict, changed: list[str] | None) -> GateOutcome:
    from .language_check import run_check

    outcome = run_check(["java"], root, timeout=cfg.get("lint_timeout_seconds", 120),
                        files=changed, log_dir=_log_path(root, "java").with_suffix(""))[0]
    decisions = ()
    if outcome.get("command") and not outcome.get("dry_run") and outcome["status"] not in ("PLANNED", "SKIPPED"):
        decisions = (GateDecision(tuple(outcome["command"]), outcome["exit_code"],
                                  outcome["status"], outcome["reason"]),)
    if outcome["status"] == PASS:
        return GateOutcome(decisions=decisions)
    if outcome["status"] != FAIL:
        hint = "；若 wrapper 缺执行位：chmod +x mvnw" if "不可执行" in outcome.get("reason", "") else ""
        return GateOutcome(notes=(f"java {outcome['status']}: {outcome['reason']}{hint}",), decisions=decisions)
    detail = _truncate_detail(outcome.get("stdout_tail", "") + outcome.get("stderr_tail", ""), root, "java")
    if outcome.get("log_path"):
        detail += f"\n完整输出: {outcome['log_path']}"
    return GateOutcome(("java", detail, "按 Java 影响计划修复并复跑 verify/check",
                        "无需安装工具；用项目自带 mvnw/gradlew 与匹配 JDK 复跑"), decisions=decisions)


def check_language(root: Path, cfg: dict, lang: str, *, scope: str,
                   changed: list[str] | None, baseline_ref: str,
                   probe: ToolchainProbe | None = None) -> GateOutcome:
    """保留 delta/全量、Markdown advisory、zsh 能力边界及有证据的基线豁免。"""
    definition = LANG_COMMANDS.get(lang)
    if not definition:
        return GateOutcome(notes=(f"{lang} PLANNED：没有可执行检查命令",))
    if lang == "java":
        return _java_check(root, cfg, changed if scope == "delta" else None)
    files = []
    notes = []
    if scope == "delta":
        files = [name for name in (changed or [])
                 if detect_language(name, root) == lang and (root / name).is_file()]
        if lang == "shell":
            zsh = [name for name in files if name.endswith(".zsh")]
            if zsh:
                files = [name for name in files if name not in zsh]
                notes.append(_ZSH_SKIP_NOTE.format(n=len(zsh)))
        if not files:
            return GateOutcome(notes=tuple(notes or [f"{lang} 本次改动未涉及，跳过"]))

    delta = scope == "delta" and 0 < len(files) <= 50
    base = (definition.get("lint") if delta else definition.get("gate") or definition.get("lint"))
    base = base or definition.get("gate") or definition.get("lint")
    if not base:
        return GateOutcome(notes=tuple(notes + [f"{lang} PLANNED：没有可执行检查命令"]))
    if not delta and "{file}" in " ".join(base):
        return GateOutcome(notes=tuple(notes + [f"{lang} 未配置项目级 gate 命令（lint 为单文件模式），本次未验证"]))
    if not project_uses_linter(definition, root):
        return GateOutcome(notes=tuple(notes + [f"{lang} 项目未接入（缺 linter 配置文件），本次未验证"]))
    hint = definition.get("install_hint") or "见 docs/LANGUAGES.md"
    available, reason = (probe or ToolchainProbe(root)).probe(definition)
    if not available:
        return GateOutcome(notes=tuple(notes + [f"{lang} 工具链不可用未验证：{reason}（安装: {hint}）"]))

    plan = scoped_plan(base, root, scope="delta" if delta else "repo", files=files if delta else None,
                       append_files=definition.get("append_files", True))
    decisions = []
    stale_notes = []
    timeout = cfg.get("lint_timeout_seconds", 120)
    for index, command in enumerate(plan.commands):
        outcome = execute(command.argv, plan.cwd, timeout)
        status, reason = lint_verdict(outcome.returncode, list(command.argv), outcome.stdout + outcome.stderr)
        # 当前或基线工具状态未知都不授予豁免；不是先比较文本再猜工具是否运行成功。
        if status == FAIL and delta and "{file}" in " ".join(base):
            stale = baseline_stale_finding(root, files[index], base, outcome.stdout + outcome.stderr,
                                           timeout, baseline_ref=baseline_ref)
            if stale is not None:
                stale_notes.append(f"{files[index]}: {stale}")
                decisions.append(GateDecision(command.argv, outcome.returncode, SKIPPED, stale))
                continue
        if status == FAIL and lang == "markdown":
            status, reason = SKIPPED, "markdown 风格告警"
        decisions.append(GateDecision(command.argv, outcome.returncode, status, reason))
        if status == PASS:
            continue
        if status == UNVERIFIED:
            notes.append(f"{lang} 工具链异常未验证：{reason} (exit {outcome.returncode})")
        elif status == SKIPPED:
            notes.append("markdown 风格告警（不阻塞提交）")
        else:
            full = "\n".join(part.rstrip() for part in (outcome.stdout, outcome.stderr) if part)
            detail = _truncate_detail(full or "（linter 无输出）", root, lang)
            dependency = _dependency_resolution_hint(lang, full)
            if dependency:
                detail += f"\n{dependency}"
            fix = f"自动修复: {' '.join(definition['format'])}" if definition.get("format") else "按上述问题逐项修复"
            return GateOutcome((lang, detail, fix, hint), tuple(notes), tuple(decisions))
        break
    if stale_notes:
        notes.append(f"{lang} 存量问题已豁免（基线同命令同工具比对）：" + "；".join(stale_notes[:3]))
    return GateOutcome(notes=tuple(notes), decisions=tuple(decisions))
