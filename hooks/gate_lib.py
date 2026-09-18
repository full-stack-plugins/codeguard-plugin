"""hooks/gate_lib.py：提交门禁的共享检查逻辑。

被两个钩子复用：
- user_prompt_validator.py（UserPromptSubmit）：失败 → exit 0 + additionalContext 修复指令
- pre_tool_git_guard.py（PreToolUse Bash）：git commit/push 前硬拦截 → exit 2 + stderr 指令

统一行为：通过/跳过 = 静默；失败 = 「问题节选 + 怎么修」结构化输出。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (  # noqa: E402
    LANG_COMMANDS, detect_languages, load_user_config, project_uses_linter, probe_toolchain,
)


def run_gate(project_root: Path, cfg: dict) -> tuple[list, list]:
    """运行全量 linter 门禁。

    返回 (failures, skipped)：
    - failures: [(lang, 问题节选, 修复命令, install_hint)]
    - skipped:  [str] 无法验证的说明（工具未装/超时），不阻塞
    """
    languages = detect_languages(project_root)
    if not languages:
        return [], []

    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    failures: list[tuple[str, str, str, str]] = []
    skipped: list[str] = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        # 门禁用项目级命令（gate）：shellcheck/php -l 等文件型 linter 裸跑会报参数错
        gate_cmd = cmd_def.get("gate") or cmd_def.get("lint")
        if not gate_cmd:
            continue
        timeout = cfg.get("lint_timeout_seconds", 120)
        hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"

        # pre-flight 探活：工具链跑不起来（运行时缺失/命令损坏）≠ 代码问题。
        # 探活失败归 skipped；通过后 lint 的非零退出一律按真实检查失败处理，
        # 不再做输出文本猜测（"No such file or directory" 也可能是 lint 报的内容）。
        ok, reason = probe_toolchain(cmd_def)
        if not ok:
            skipped.append(f"{lang} 工具链不可用未验证：{reason}（安装: {hint}）")
            continue
        if not project_uses_linter(cmd_def, project_root):
            # 项目未接入该 linter（无配置文件）——归 skipped，不拦提交
            skipped.append(f"{lang} 项目未接入（缺 linter 配置文件），本次未验证")
            continue

        try:
            proc = subprocess.run(
                gate_cmd, cwd=project_root, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            skipped.append(f"{lang} 检查超时（>{timeout}s），本次未验证")
            continue
        except FileNotFoundError:
            skipped.append(f"{lang} linter 未安装，本次未验证（安装: {hint}）")
            continue
        if proc.returncode == 0:
            continue
        if lang == "markdown":
            # 文档类风格问题不阻塞提交
            skipped.append("markdown 风格告警（不阻塞提交）")
            continue
        if proc.returncode == 127:
            # POSIX 语义明确的 command not found（探活后的运行中缺失，如 npx 内部调 node）
            skipped.append(f"{lang} 工具链异常未验证：命令不存在（exit 127）")
            continue
        # 真实 lint 失败：问题摘要取输出头部（最具体的问题在前）
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        detail = "\n".join(ln for ln in f"{out}\n{err}".splitlines() if ln.strip())[:600]
        fix = f"自动修复: {' '.join(cmd_def['format'])}" if cmd_def.get("format") else "按上述问题逐项修复"
        failures.append((lang, detail, fix, hint))
    return failures, skipped


def format_failure_report(failures: list) -> str:
    """把 failures 渲染成面向 AI/用户的「问题 + 怎么修」文本"""
    lines = [
        "",
        f"codeguard ❌ 提交门禁：{len(failures)} 个生态未通过",
        "=" * 60,
    ]
    for lang, detail, fix, hint in failures:
        lines.append(f"【{lang}】发现的问题（节选）：")
        lines.append(detail if detail else "  lint 退出码非零，无文本输出")
        lines.append(f"  ▶ 怎么修: {fix}")
        lines.append(f"  ▶ 未安装工具时先安装: {hint}")
        lines.append("-" * 60)
    lines.append(f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py")
    return "\n".join(lines)


def gate_directive(failures: list) -> str:
    """给 AI 的行动指令：收到后应立即修复并重新提交，而不是询问用户"""
    return (
        format_failure_report(failures)
        + "\n\n"
        + "**给 AI 的强制指令**：提交门禁未通过，禁止执行 git commit / git push。\n"
        + "请立即处理：1) 按上面「怎么修」逐项修复（能自动修复的先跑自动修复命令）；"
        + "2) 修复过程中无需向用户确认；3) 全部修复完成后重新执行用户要做的提交操作。\n"
        + "确需绕过（仅用户明确要求时）：在该仓库执行 git config codeguard.skipGate true，"
        + "完成后 git config --unset codeguard.skipGate 恢复。环境变量 CODEGUARD_SKIP_GATE "
        + "只对手动直调 run_check 有效（无法传入宿主钩子进程）。"
    )
