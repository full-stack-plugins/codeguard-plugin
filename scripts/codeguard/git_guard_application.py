"""PreToolUse Git 硬门禁应用：仓库解析、豁免、准确检查与结构化决策。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from git_snapshot import SnapshotError

from .gate import run_gate
from .git_context import (
    _fallback_roots as fallback_roots,
)
from .git_context import (
    _filter_fallback_roots as filter_fallback_roots,
)
from .git_context import (
    _guarded_mode as guarded_mode,
)
from .git_context import (
    resolve_project_roots,
    staging_intent,
)
from .git_syntax import _collect_subs as collect_subs
from .git_syntax import chain_skip_gate, inline_skip_gate
from .hook_state import record_skip_event
from .reporting import format_safety_report, gate_directive
from .repository_policy import check_commit_safety, skip_gate_via_git_config


@dataclass(frozen=True)
class GitGuardResult:
    """宿主按 contexts 输出 additionalContext，按 stderr/exit_code 决定拦截。"""

    exit_code: int = 0
    contexts: tuple[str, ...] = ()
    stderr: str = ""


def evaluate_git_command(command: str, *, cwd: Path, load_config: Callable[[], dict],
                         bypass_env: bool = False) -> GitGuardResult:
    """评估一条工具命令；不修改 index，不直接输出宿主协议。"""
    mode = guarded_mode(command) if command else None
    if mode is None:
        return GitGuardResult()
    if bypass_env:
        record_skip_event("env")
        return GitGuardResult()

    cfg = load_config()
    roots = resolve_project_roots(command, cwd=cwd)
    fallback_note: str | None = None
    if not roots:
        fallback = fallback_roots(cwd)
        if fallback:
            roots = fallback
            fallback_note = f"未检测到显式 cd 仓；兜底扫描 cwd 一层子目录找到 {len(fallback)} 个 git 仓"
        else:
            return GitGuardResult(
                2,
                stderr=(f"[codeguard] 未检测到任何 git 仓：cwd={cwd} 且命令链中无 cd <仓>。"
                        "请在 git push 前先 cd <仓路径>，或在仓库根设置 git config codeguard.skipGate true。"
                        "（已用兜底扫描 cwd 一层子目录，无 git 仓。）"),
            )
    if fallback_note:
        before = len(roots)
        roots = filter_fallback_roots(roots, mode, None)
        fallback_note += f"；提交面收窄 {before}→{len(roots)} 个仓"
        if not roots:
            record_skip_event("monorepo-fallback-empty", detail=fallback_note)
            return GitGuardResult()
        record_skip_event("monorepo-fallback", roots[0], detail=fallback_note)
    if any(skip_gate_via_git_config(root) for root in roots):
        record_skip_event("skipGate", roots[0])
        return GitGuardResult()
    if inline_skip_gate(command):
        record_skip_event("inline-skipGate", roots[0])
        context = (
            "codeguard: 已通过内联豁免 `-c codeguard.skipGate` 放行本次提交"
            "（已审计记录，Stop 摘要可见）。"
        )
        return GitGuardResult(contexts=(context,))
    if chain_skip_gate(command):
        record_skip_event("chain-skipGate", roots[0])
        context = (
            "codeguard: 已通过链式豁免（set→提交→unset 同链）放行本次提交"
            "（已审计记录，Stop 摘要可见）。"
        )
        return GitGuardResult(contexts=(context,))

    pending_commit = "commit" in collect_subs(command)
    contexts: list[str] = []
    reports: list[str] = []
    for project_root in roots:
        try:
            lanes, extra = staging_intent(command, project_root=project_root)
        except SnapshotError as exc:
            contexts.append(
                f"codeguard: git UNVERIFIED：{project_root} 无法准确预测暂存面：{exc}；"
                "请完成明确的暂存操作后单独提交，并复核检查结果。"
            )
            continue
        root_extra = list(extra)
        failures, skipped = run_gate(
            project_root, cfg, mode=mode, lanes=lanes, extra=root_extra,
            exact=True, pending_commit=pending_commit,
        )
        if failures:
            reports.append(gate_directive(failures, project_root=project_root))
        unknown = [item for item in skipped if "本次改动未涉及" not in item and " SKIPPED:" not in item
                   and "markdown 风格告警" not in item]
        if unknown:
            contexts.append("codeguard: 存在未验证项，不能宣称全部通过：" + "；".join(unknown))
        violations = check_commit_safety(project_root, mode, lanes=lanes, extra=root_extra,
                                         pending_commit=pending_commit)
        if violations:
            reports.append(format_safety_report(violations) + (
                "\n\n**给 AI 的强制指令**：**密钥/凭据类**（.env、*.pem、id_* 等）"
                "立即 git rm --cached 并提醒用户轮换密钥，不能只删了事；"
                "**非密钥类**（依赖/产物目录、仓根 db/log 等）**先与用户确认**"
                "是否为有意入库的第一方代码或合法 fixture——确认属误入库才执行"
                "git rm --cached + .gitignore，确认后重新执行本次 git 命令。"
            ))

    if not reports:
        return GitGuardResult(contexts=tuple(contexts))
    detail = ("\n\n" + "=" * 20 + " 下一个仓库 " + "=" * 20 + "\n\n").join(reports)
    return GitGuardResult(2, tuple(contexts), detail)
