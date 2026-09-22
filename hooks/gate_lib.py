"""hooks/gate_lib.py：提交门禁的共享检查逻辑。

被两个钩子复用：
- user_prompt_validator.py（UserPromptSubmit）：失败 → exit 0 + additionalContext 修复指令
- pre_tool_git_guard.py（PreToolUse Bash）：git commit/push 前硬拦截 → exit 2 + stderr 指令

统一行为：通过/跳过 = 静默；失败 = 「问题节选 + 怎么修」结构化输出。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (
    LANG_COMMANDS,
    detect_languages,
    probe_toolchain,
    project_uses_linter,
)

# === git 提交内容安全检查：绝不该进版本库的文件 ===
# 目录（路径任一段落匹配即违规）：依赖/虚拟环境/构建产物/IDE/缓存
GUARD_EXCLUDE_DIRS = {
    ".venv", "venv", "env", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "target", "dist", "build", "out", ".next",
    ".nuxt", ".gradle", "vendor", ".idea", ".vscode", "coverage", ".terraform",
    ".tox", ".eggs", "htmlcov", ".turbo", ".parcel-cache",
}
# 文件名模式（fnmatch）：密钥/凭据/本地环境/数据库/系统垃圾
GUARD_EXCLUDE_FILES = [
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "*.keystore", "id_rsa", "id_ed25519", "id_ecdsa", "*.pem.orig",
    "credentials*.json", "serviceAccount*.json", "*service-account*.json",
    "*.sqlite", "*.sqlite3", "*.db", ".DS_Store", "Thumbs.db", "*.log", "*.pyc",
]


def _git(project_root: Path, *args: str) -> str | None:
    """跑只读 git 命令；失败（非 git 仓/无 upstream 等）返回 None，由调用方降级"""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=project_root, capture_output=True, check=False, text=True, timeout=15
        )
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def check_commit_safety(project_root: Path, mode: str) -> list[tuple[str, str, str]]:
    """检查即将进入版本库的文件（commit=暂存区；push=未推送提交的 diff）。

    返回违规列表 [(路径, 命中规则, 建议操作)]；无法判定（非 git 仓/无对比基线）
    返回空列表并由调用方按 skipped 处理——安全检查不做静默失败。
    """
    if mode == "commit":
        out = _git(project_root, "diff", "--cached", "--name-only", "-z")
    else:  # push：检查所有未推送提交触及的文件
        out = _git(project_root, "diff", "--name-only", "-z", "@{upstream}..HEAD")
        if out is None:
            out = _git(project_root, "diff", "--name-only", "-z", "origin/main..HEAD")
    if not out:
        return []

    import fnmatch
    violations: list[tuple[str, str, str]] = []
    for raw in out.split("\0"):
        f = raw.strip()
        if not f:
            continue
        parts = f.split("/")
        hit_dir = next((seg for seg in parts[:-1] if seg in GUARD_EXCLUDE_DIRS), None)
        if hit_dir:
            violations.append((
                f, f"目录 ./{hit_dir}/ 属于依赖/产物/本地环境，不应入库",
                f"git rm -r --cached '{f}' 并在 .gitignore 加 '{hit_dir}/'",
            ))
            continue
        name = parts[-1]
        rule = next((pat for pat in GUARD_EXCLUDE_FILES if fnmatch.fnmatch(name, pat)), None)
        if rule:
            violations.append((
                f, f"文件命中敏感模式 {rule}（密钥/凭据/本地配置类）",
                f"git rm --cached '{f}' 并在 .gitignore 加 '{rule}'；确认是否已泄露需要轮换密钥",
            ))
    return violations


def format_safety_report(violations: list[tuple[str, str, str]]) -> str:
    lines = [f"codeguard 🛑 提交内容安全检查：{len(violations)} 个文件不应入库", "─" * 60]
    for f, reason, fix in violations:
        lines.append(f"  {f}")
        lines.append(f"     原因: {reason}")
        lines.append(f"     怎么修: {fix}")
        lines.append("-" * 60)
    lines.append("修复后重新暂存再提交（git add 时排除上述文件）")
    return "\n".join(lines)


def _gate_cache_path(project_root: Path) -> Path:
    import hashlib
    import tempfile
    key = hashlib.sha1(str(project_root.resolve()).encode()).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / f"codeguard-gate-{os.getuid()}-{key}.json"


def _gate_cache_key(project_root: Path, languages: list) -> str | None:
    """缓存键：HEAD + 暂存区指纹（index mtime + 文件数）。文件一变即失效。"""
    head = _git(project_root, "rev-parse", "HEAD")
    if head is None:
        return None
    idx = project_root / ".git" / "index"
    try:
        idx_sig = f"{idx.stat().st_mtime_ns}:{idx.stat().st_size}" if idx.exists() else "no-index"
    except OSError:
        return None
    return f"{head.strip()}|{idx_sig}|{','.join(sorted(languages))}"


GATE_CACHE_TTL = 60  # 秒：UPS 软门禁与紧随的 PreToolUse 硬门禁之间复用


def run_gate(project_root: Path, cfg: dict, languages: list | None = None) -> tuple[list, list]:
    """运行 linter 门禁（跨进程结果缓存 + 并行执行）。

    `languages` 可选：调用方（UserPromptSubmit）可传入用户消息里提到的
    语言子集，门禁只跑该子集；不传则按 `detect_languages()` 全量探测。

    软门禁（UserPromptSubmit）与硬门禁（PreToolUse）在正常提交路径上
    会对同一状态连跑两次全量 lint——缓存键含 HEAD 与暂存区指纹，
    文件未变则 60s 内直接复用；AI 修复并重新暂存后键变化自动失效。

    返回 (failures, skipped)：
    - failures: [(lang, 问题节选, 修复命令, install_hint)]
    - skipped:  [str] 无法验证的说明（工具未装/超时），不阻塞
    """
    import time as _time
    if languages is None:
        languages = detect_languages(project_root)
    if not languages:
        return [], []
    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    ck = _gate_cache_key(project_root, languages)
    cache_file = _gate_cache_path(project_root)
    if ck:
        try:
            blob = json.loads(cache_file.read_text())
            if blob.get("key") == ck and _time.time() - blob.get("ts", 0) < GATE_CACHE_TTL:
                return blob["failures"], blob["skipped"]
        except (OSError, ValueError, KeyError):
            pass

    failures, skipped = _run_gate_uncached(project_root, cfg, languages)

    if ck:
        try:
            cache_file.write_text(json.dumps(
                {"key": ck, "ts": _time.time(), "failures": failures, "skipped": skipped},
                ensure_ascii=False))
        except OSError:
            pass
    return failures, skipped


def _run_gate_uncached(project_root: Path, cfg: dict, languages: list) -> tuple[list, list]:
    """单次全量门禁（多语言并行，结果顺序保持语言表顺序）"""
    from concurrent.futures import ThreadPoolExecutor

    def check(lang: str):
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            return None
        gate_cmd = cmd_def.get("gate") or cmd_def.get("lint")
        if not gate_cmd:
            return None
        if "{file}" in " ".join(gate_cmd):
            # {file} 占位符只在 PostToolUse 单文件模式下被替换；门禁拿字面量
            # 当文件名跑必然报"文件不存在"→ 会被误判成 lint 失败。归跳过。
            return (lang, None, f"{lang} 未配置项目级 gate 命令（lint 为单文件模式），本次未验证")
        timeout = cfg.get("lint_timeout_seconds", 120)
        hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"
        ok, reason = probe_toolchain(cmd_def)
        if not ok:
            return (lang, None, f"{lang} 工具链不可用未验证：{reason}（安装: {hint}）")
        if not project_uses_linter(cmd_def, project_root):
            return (lang, None, f"{lang} 项目未接入（缺 linter 配置文件），本次未验证")
        try:
            proc = subprocess.run(
                gate_cmd, cwd=project_root, capture_output=True, check=False, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return (lang, None, f"{lang} 检查超时（>{timeout}s），本次未验证")
        except FileNotFoundError:
            return (lang, None, f"{lang} linter 未安装，本次未验证（安装: {hint}）")
        if proc.returncode == 0:
            return None
        if lang == "markdown":
            return (lang, None, "markdown 风格告警（不阻塞提交）")
        if proc.returncode == 127:
            return (lang, None, f"{lang} 工具链异常未验证：命令不存在（exit 127）")
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        detail = "\n".join(ln for ln in f"{out}\n{err}".splitlines() if ln.strip())[:600]
        fix = f"自动修复: {' '.join(cmd_def['format'])}" if cmd_def.get("format") else "按上述问题逐项修复"
        return (lang, (lang, detail, fix, hint), None)

    results = []
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(languages)))) as pool:
        results = list(pool.map(check, languages))

    failures, skipped = [], []
    for r in results:              # pool.map 保序，输出与语言表顺序一致
        if r is None:
            continue
        _, failure, skip = r
        if failure:
            failures.append(failure)
        if skip:
            skipped.append(skip)
    return failures, skipped

def summarize_failures(failures: list) -> str:
    """问题综述（一行，用作标题/通知标题）：哪几个生态、什么性质的问题"""
    langs = "、".join(f[0] for f in failures)
    return f"codeguard ❌ 提交门禁未通过：{langs} 共 {len(failures)} 个语言生态有 lint 问题"


def format_failure_report(failures: list) -> str:
    """渲染「综述 + 细节」两段式报告。

    第一行 = 问题综述（宿主 UI 通常取首行作标题）；随后是细节，
    不再重复综述内容——修复"标题和详情一样"的问题。
    """
    lines = [
        summarize_failures(failures),
        "─" * 60,
    ]
    for lang, detail, fix, hint in failures:
        lines.append(f"【{lang}】具体问题：")
        lines.append(detail if detail else "  lint 退出码非零，无文本输出")
        lines.append(f"  ▶ 怎么修: {fix}")
        lines.append(f"  ▶ 未安装工具时先安装: {hint}")
        lines.append("─" * 60)
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
