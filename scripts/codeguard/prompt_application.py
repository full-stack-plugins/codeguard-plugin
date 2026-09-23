"""UserPromptSubmit 软门禁应用：返回上下文与通知，不写宿主协议。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .discovery import detect_languages
from .fingerprint import check_identity
from .gate import run_gate
from .hook_state import completed_event, record_completed_event, record_skip_event
from .prompt_policy import detect_languages_in_text, intent_mode, is_trigger
from .registry import LANG_COMMANDS
from .reporting import format_safety_report, gate_directive, summarize_failures
from .repository_policy import check_commit_safety, skip_gate_via_git_config


@dataclass(frozen=True)
class PromptResult:
    """软门禁结果：由 Hook 适配器编码为 additionalContext。"""

    additional_context: str | None = None
    notification: tuple[str, str] | None = None
    _on_delivered: Callable[[], None] | None = field(default=None, repr=False, compare=False)

    def acknowledge(self) -> None:
        """宿主成功输出后才登记完成，输出失败时保留重试机会。"""
        if self._on_delivered is not None:
            self._on_delivered()


def non_git_note() -> str:
    return (
        "codeguard：当前目录不是 git 仓库，提交门禁已跳过"
        "（门禁只对 git 仓生效；非 git 目录曾被回退成工作区根全仓扫描——"
        "一个临时目录即可把上百个无关仓的存量 lint 变成永久红）。"
    )


def evaluate_prompt(user_text: str, *, project_root: Path | None,
                    session_id: object, load_config: Callable[[], dict],
                    bypass_env: bool = False) -> PromptResult:
    """评估提交意图，保留软提醒、逃生门、内容身份去重与宽范围观察。"""
    if not is_trigger(user_text):
        return PromptResult()
    if bypass_env:
        record_skip_event("env")
        return PromptResult()
    if project_root is None or not (project_root / ".git").exists():
        return PromptResult(non_git_note())
    lint_bypassed = skip_gate_via_git_config(project_root)
    if lint_bypassed:
        record_skip_event("skipGate", project_root)

    cfg = load_config()
    detected = detect_languages(project_root)
    subset = detect_languages_in_text(user_text, detected)

    def current_event_key() -> str | None:
        if not session_id:
            return None
        identity = check_identity(project_root, cfg,
                                  {lang: LANG_COMMANDS.get(lang, {}) for lang in (subset or detected)})
        return f"ups:{session_id}:{user_text}:{identity}" if identity is not None else None

    event_key = current_event_key()
    if event_key and completed_event(event_key) is not None:
        return PromptResult()

    # 软门没有待执行 git 命令，故保持三路宽口径；硬门另用预测暂存面。
    mode = intent_mode(user_text)
    failures, skipped = (
        ((), ()) if lint_bypassed
        else run_gate(project_root, cfg, languages=(subset or None), mode=mode)
    )
    violations = check_commit_safety(project_root, mode)
    if lint_bypassed and not violations:
        # 豁免命中且无安全违规：软门禁静默退出（与硬门禁一致），绕过计数已 +1
        return PromptResult()

    def on_delivered() -> None:
        if event_key == current_event_key():
            record_completed_event(event_key, 0, "", "")

    completion = on_delivered if event_key and not skipped else None

    if failures or violations:
        first_issue = failures[0][1].splitlines()[0][:120] if failures and failures[0][1] else "详见对话"
        headline = (f"{failures[0][0]}: {first_issue}" if failures
                    else f"提交安全: {violations[0][0]}")
        parts = [gate_directive(failures)] if failures else []
        if violations:
            parts.append(format_safety_report(violations))
        parts.append(
            "**给 AI 的强制指令**：**密钥/凭据类**必须 git rm --cached 并提醒用户"
            "轮换密钥；**非密钥类**先与用户确认是否为有意入库的第一方代码或合法"
            " fixture，确认误入库再 git rm --cached + 补 .gitignore；确认并修复后"
            "重新执行提交。"
        )
        title = summarize_failures(failures) if failures else "提交安全"
        return PromptResult("\n\n".join(parts), (title, headline), completion)

    skipped_langs = {item.split()[0] for item in skipped}
    checked = sorted(set(detect_languages(project_root)) - skipped_langs)
    skipped_note = f"；跳过 {len(skipped)} 项（{'；'.join(skipped)}）" if skipped else ""
    unknown = [item for item in skipped if "本次改动未涉及" not in item and " SKIPPED:" not in item
               and "markdown 风格告警" not in item]
    context = (
        ("codeguard ⚠️ 检查范围存在未验证项，不能宣称全部通过" if unknown
         else f"codeguard ✅ 提交门禁通过：已检查 {len(checked)} 个语言生态 + 暂存区安全")
        + f"（{', '.join(checked) or '无'}）{skipped_note}。"
    )
    return PromptResult(context, _on_delivered=completion)
