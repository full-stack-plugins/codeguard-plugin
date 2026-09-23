"""门禁报告呈现：只渲染已有证据，不启动检查或读取注册表。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .storage import write_private_text

PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def plugin_version() -> str:
    """已安装插件自身的 manifest 是显示版本的事实源。"""
    try:
        manifest = json.loads((PLUGIN_ROOT / ".zcode-plugin/plugin.json").read_text(encoding="utf-8"))
        version = manifest.get("version")
        return version if isinstance(version, str) and version else "unknown"
    except (OSError, ValueError, TypeError):
        return "unknown"


CODEGUARD_VERSION = plugin_version()

# maven 依赖解析失败的特征（javadoc:jar 独立 goal 在 reactor 上跑时的典型崩法）
_DEP_RESOLUTION_RE = re.compile(
    r"Could not resolve dependencies|Could not find artifact|DependencyResolutionException"
)

def format_safety_report(violations: list[tuple[str, str, str]]) -> str:
    lines = [f"codeguard 🛑 提交内容安全检查：{len(violations)} 个文件不应入库", "─" * 60]
    for f, reason, fix in violations:
        lines.append(f"  {f}")
        lines.append(f"     原因: {reason}")
        lines.append(f"     怎么修: {fix}")
        lines.append("-" * 60)
    lines.append("修复后重新暂存再提交（git add 时排除上述文件）")
    return "\n".join(lines)


def _log_path(project_root: Path, lang: str) -> Path:
    import hashlib
    import tempfile
    key = hashlib.sha1(str(project_root.resolve()).encode()).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / f"codeguard-gate-{key}-{lang}.log"


def _rule_summary(full: str) -> str:
    """ruff/checkstyle 输出的规则聚合计数行（如 "EXE001×3 UP009×1"）。

    2026-09-23 opencli 会话实测：门禁输出被截断后 AI 修一个才暴露下一个
    （whack-a-mole 升级版），聚合计数让 AI 一次看到问题全集与规模。
    非 linter 标准行格式（无规则码锚）时返回空串。
    """
    import re as _re
    counts: dict[str, int] = {}
    for line in full.splitlines():
        m = _re.search(r"\b([A-Z]{2,5}\d{3,4})\b", line)
        if m and (":" in line or "-->" in line):
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    if not counts:
        return ""
    return "规则汇总: " + " ".join(f"{k}×{v}" for k, v in sorted(counts.items()))


def _truncate_detail(full: str, project_root: Path, lang: str) -> str:
    """节选 + 总量 + 完整日志路径：截断只留头 600 字符会让 AI 一次修 3 个、
    重试再看 3 个（whack-a-mole）；必须给出"共几行、完整在哪"。"""
    lines = [ln for ln in full.splitlines() if ln.strip()]
    summary_line = _rule_summary(full)
    detail = full[:600]
    if summary_line:
        detail = summary_line + "\n" + detail
    if len(lines) > 8 or len(full) > 600:
        try:
            path = _log_path(project_root, lang)
            write_private_text(path, full)
            detail += f"\n…（截断，共 {len(lines)} 行；完整输出: {path}）"
        except OSError:
            detail += f"\n…（截断，共 {len(lines)} 行）"
    return detail


def _dependency_resolution_hint(lang: str, full: str) -> str | None:
    """Java 门禁报依赖解析失败时给行动指引，而不是只留 maven 堆栈尾部。

    javadoc:jar 以独立 goal 跑在 reactor 上，sample 类模块常设
    maven.install.skip=true，它们的构件不在本地仓——下游模块必然
    Could not resolve。没有这行提示，用户看到的是与"该改什么"无关的堆栈。
    """
    if lang != "java":
        return None
    if not _DEP_RESOLUTION_RE.search(full):
        return None
    return (
        "提示：依赖构件不可解析（如 samples 模块 maven.install.skip=true 未入本地仓）。"
        "先在仓根执行 mvn install -DskipTests（必要时加 -Dmaven.install.skip=false）再重试门禁。"
    )


def summarize_failures(failures: list) -> str:
    """问题综述（一行，用作标题/通知标题）：哪几个生态、什么性质的问题"""
    langs = "、".join(f[0] for f in failures)
    return f"codeguard ❌ 提交门禁未通过：{langs} 共 {len(failures)} 个语言生态有 lint 问题"


REPORT_MAX_CHARS = 3000  # gate_directive 总长硬上限：宿主会把超长 stderr 从尾部
                         # 截断，指令段曾因此整体丢失（实测报告只见到首段报错）


def _squeeze(text: str, budget: int) -> str:
    """保头保尾截断：尾部含「完整输出: /tmp/…」日志路径，砍中段也不能丢。"""
    if len(text) <= budget:
        return text
    keep_tail = min(150, budget // 3)
    keep_head = max(0, budget - keep_tail - 10)
    return text[:keep_head] + "\n……（中略）……" + text[-keep_tail:]


def _failure_detail_blocks(failures: list, *, fix_first: bool = False) -> list[str]:
    """每个语言的细节块。fix_first=True 把「怎么修/安装」排在长 detail 之前——
    报告被宿主截断时，行动指引必须比 linter 原始输出先存活下来。"""
    blocks: list[str] = []
    for lang, detail, fix, hint in failures:
        block = [f"【{lang}】具体问题："]
        tail = [
            f"  ▶ 怎么修: {fix}",
            f"  ▶ 未安装工具时先安装: {hint}",
        ]
        if lang == "python" and "[*]" in (detail or ""):
            tail.append("  ▶ 含 [*] 可自动修复项: ruff check --fix <涉及路径>")
        body = detail if detail else "  lint 退出码非零，无文本输出"
        if fix_first:
            block += tail + [body]
        else:
            block += [body] + tail
        block.append("─" * 60)
        blocks.append("\n".join(block))
    return blocks


def format_failure_report(failures: list) -> str:
    """渲染「综述 + 细节」两段式报告（CLI/调试面）。

    第一行 = 问题综述（宿主 UI 通常取首行作标题）；随后是细节，
    不再重复综述内容——修复"标题和详情一样"的问题。
    """
    lines = [
        summarize_failures(failures),
        "─" * 60,
    ]
    lines.extend(_failure_detail_blocks(failures))
    lines.append(f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py")
    return "\n".join(lines)


def gate_directive(failures: list, project_root: Path | str | None = None) -> str:
    """给 AI 的行动指令：收到后应立即修复并重新提交，而不是询问用户。

    project_root：本次门禁的目标仓库根——cwd 漂移会让钩子扫到"非目标仓"
    （实测：在 codex 仓 cwd 下提交 opencli，POM 4.1.0 报错让人以为改错了
    文件），首行显式标注目标仓库可第一时间发现扫错对象。

    结构 = 综述（首行契约）→ 强制指令（前置！）→ 每语言细节（fix 先于
    detail）→ 修复入口；整体压到 REPORT_MAX_CHARS 内。指令必须前置：宿主把
    超长 stderr 从尾部截断，此前指令在报告末段，长报告下 AI 只看到首段 linter
    报错、「拆两次调用」与 skipGate 逃生门全部丢失（实测）。首行仍为综述、
    综述不重复、含「具体问题」——run_all/硬门禁契约保持。
    """
    head_repo = f"本次门禁目标仓库: {Path(project_root).resolve()}\n" if project_root else ""
    header = [
        summarize_failures(failures),
        f"codeguard v{CODEGUARD_VERSION}",
        head_repo + "─" * 60,
        "**给 AI 的强制指令**：提交门禁未通过，禁止执行 git commit / git push。\n"
        + "**⚠️ 整个工具调用没有执行**：被拦截的是一次包含 git commit/push 的完整 Bash "
        "调用——其中非 git 的前序步骤（写文件、跑脚本）也全部未运行。请把「修复」与"
        "「提交」拆成两次独立的工具调用，修完再单独执行提交。\n"
        + "**⚠️ 如果报错涉及 target/、dist/、build/ 下的构建产物**：请先单独"
        "运行清理命令（如 `rm -rf target/reports`，不含 git commit/push），"
        "清理完成后再重试提交——本门禁在命令执行前拦截，此前命令链中的清理"
        "步骤不会被执行。\n"
        + "请立即处理：1) 按下面「怎么修」逐项修复（能自动修复的先跑自动修复命令）；"
        "2) 纯 lint 类修复可直接继续、不必逐项追问；但凡涉及付费、发布、删除、"
        "密钥、或跨出本仓的操作，必须先征得用户同意再执行；"
        "3) 修复完成后重新执行用户要做的提交操作。\n"
        + "确需绕过（仅用户明确要求时）：**单次豁免**用 `git -c codeguard.skipGate=true commit …`"
        "（不落配置、无残留，推荐）；**仓库级豁免**在该仓库执行 git config codeguard.skipGate true，"
"完成后 git config --unset codeguard.skipGate 恢复。环境变量 CODEGUARD_SKIP_GATE "
"只认 1/true/yes 且须存在于钩子进程环境——宿主命令内联赋值不会传入钩子，"
        "设 0/false 不豁免（该变量不建议使用，优先单次豁免）。两种豁免都会记入会话审计明细。"
        "注意：仓库级豁免对该克隆**所有分支**生效且跨会话残留，务必按上方说明 unset 恢复。",
        "─" * 60,
    ]
    footer = f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py"
    head = "\n".join(header)
    budget = max(400, REPORT_MAX_CHARS - len(head) - len(footer) - 64)
    blocks = _failure_detail_blocks(failures, fix_first=True)
    used, kept = 0, []
    for block in blocks:
        remain = budget - used
        if remain <= 0:
            kept.append("…（其余语言的问题明细已省略，按上方怎么修逐语言处理）")
            break
        if len(block) > remain:
            block = _squeeze(block, remain)
        kept.append(block)
        used += len(block) + 1
    return "\n".join([head, *kept, footer])
