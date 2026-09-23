"""PostToolUse 保存检查应用：单文件范围、修复复检与有证据的反馈。"""
from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from scope import is_build_artifact

from . import hook_state
from .discovery import detect_language, project_uses_linter
from .execution import execute
from .fingerprint import check_identity
from .hook_state import codeguard_home
from .planning import scoped_plan
from .registry import LANG_COMMANDS
from .verdict import UNVERIFIED, lint_verdict

PLUGIN_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SaveResult:
    """宿主输出 additionalContext 后确认统计；通知由宿主适配器执行。"""

    additional_context: str | None = None
    system_message: str | None = None
    notification: tuple[str, str, str] | None = None
    _on_delivered: Callable[[], None] | None = field(default=None, repr=False, compare=False)

    def acknowledge(self) -> None:
        if self._on_delivered is not None:
            self._on_delivered()


def state_path() -> Path:
    """兼容旧无 ID 状态，带会话 ID 时绝不认领无归属记录。"""
    return hook_state.state_path(PLUGIN_ROOT / ".session_state.json")


def dedup_path() -> Path:
    return codeguard_home() / "file_dedup.json"


def bump_state(lang: str, passed: bool, auto_fixed: bool = False) -> None:
    hook_state.bump_state(state_path(), lang, passed, auto_fixed)


def notification_allowed(lang: str, cooldown_s: int = 60) -> bool:
    return hook_state.notification_allowed(state_path(), lang, cooldown_s)


def should_suppress_duplicate(file_path: str, identity: str | None,
                              store: Path | None = None) -> bool:
    return hook_state.completed_file_check(file_path, store or dedup_path(), identity)


def is_ejs_template(file_path: str) -> bool:
    """EJS 标记不是 HTML，htmlhint 会对模板语法产生必然误报。"""
    try:
        return "<%" in Path(file_path).read_text(errors="ignore")[:8192]
    except OSError:
        return False


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    """检查器与 formatter 使用共享进程边界，保留原 tuple 兼容语义。"""
    return execute(cmd, cwd, timeout).as_tuple()


def should_skip(file_path: str, languages: list[str]) -> tuple[bool, str]:
    if not file_path or is_build_artifact(file_path):
        return True, ""
    lang = detect_language(file_path)
    if not lang:
        return True, ""
    if languages and lang not in languages:
        return True, lang
    return False, lang


def _porcelain(project_root: Path) -> set[str]:
    """修复影响提示的尽力观察，不作为是否通过的证据。"""
    outcome = execute(["git", "status", "--porcelain"], project_root, 10)
    if outcome.failure or outcome.returncode != 0:
        return set()
    return {line[3:].strip() for line in outcome.stdout.splitlines() if len(line) > 3}


def _failure_context(file_path: str, lang: str, cmd_def: dict, stdout: str,
                     stderr: str) -> tuple[str, str]:
    raw = (stdout or stderr or "").strip()
    problem_lines = [line.strip() for line in raw.splitlines() if line.strip()]
    problems = "\n".join(problem_lines[:5])[:500] or "（linter 未输出具体问题）"
    if len(problem_lines) > 5 or len(raw) > 500:
        try:
            key = hashlib.sha1(str(file_path).encode()).hexdigest()[:12]
            full_path = Path(tempfile.gettempdir()) / f"codeguard-post-{lang}-{key}.log"
            full_path.write_text(raw, encoding="utf-8")
            problems += f"\n…（截断，共 {len(problem_lines)} 行；完整输出: {full_path}）"
        except OSError:
            problems += f"\n…（截断，共 {len(problem_lines)} 行）"
    fix_cmd = " ".join(cmd_def.get("format") or []) or "按上述问题逐条修复"
    context = (
        f"codeguard ⚠️ [{lang}] {Path(file_path).name} 检查未通过\n"
        f"发现的问题（节选）:\n{problems}\n"
        "怎么修:\n"
        f"  1. 可先运行 `{fix_cmd}` 自动修复格式类问题\n"
        "  2. 手动修复上述具体问题后，重新保存该文件，codeguard 会自动复检"
    )
    return context, problem_lines[0][:120] if problem_lines else ""


def evaluate_save(file_path: str, project_root: Path, cfg: dict,
                  *, store: Path | None = None) -> SaveResult:
    """冻结 save 计划并执行一次检查；必要时只修复并复检同一文件。"""
    skipped, lang = should_skip(file_path, cfg.get("enabled_languages", []))
    if skipped or lang == "markdown":
        return SaveResult()
    cmd_def = LANG_COMMANDS.get(lang)
    if not cmd_def:
        return SaveResult()
    if not cmd_def.get("append_files", True):
        return SaveResult(f"codeguard: {lang} 是项目级检查；本次保存未验证，"
                          "请使用 codeguard check 或提交门禁。不会自动格式化整个项目。")
    if not project_uses_linter(cmd_def, project_root):
        return SaveResult()
    if lang == "html" and is_ejs_template(file_path):
        return SaveResult()
    lint_cmd = cmd_def.get("lint") or []
    if not lint_cmd:
        return SaveResult()

    timeout = cfg.get("lint_timeout_seconds", 120)
    lint_plan = scoped_plan(lint_cmd, project_root, scope="save", files=[str(file_path)])
    lint_argv = list(lint_plan.commands[0].argv)
    store = store or dedup_path()

    def identity() -> str | None:
        return check_identity(project_root, cfg, {lang: cmd_def}, extra_files=[file_path])

    checked_identity = identity()
    if checked_identity is not None and should_suppress_duplicate(file_path, checked_identity, store):
        return SaveResult()
    rc, stdout, stderr = run(lint_argv, cwd=lint_plan.cwd, timeout=timeout)
    verdict, reason = lint_verdict(rc, lint_cmd, stdout + stderr)
    if verdict == UNVERIFIED:
        return SaveResult(f"codeguard: UNVERIFIED [{lang}] {reason} (exit {rc})；"
                          "没有代码结论，不自动修复。")

    auto_fixed = False
    touched_others: list[str] = []
    if rc != 0 and cfg.get("auto_fix_on_save", True):
        fmt_cmd = cmd_def.get("format")
        if fmt_cmd:
            before = _porcelain(project_root)
            fix_plan = scoped_plan(fmt_cmd, project_root, scope="save", files=[str(file_path)])
            fix_rc, _, _ = run(list(fix_plan.commands[0].argv), cwd=fix_plan.cwd, timeout=timeout + 60)
            if fix_rc == 0:
                auto_fixed = True
                after = _porcelain(project_root)
                touched_others = sorted(name for name in (after - before)
                                        if not name.rstrip("/").endswith(Path(file_path).name))
                checked_identity = identity()
                rc, stdout, stderr = run(lint_argv, cwd=lint_plan.cwd, timeout=timeout)

    verdict, reason = lint_verdict(rc, lint_cmd, stdout + stderr)
    if verdict == UNVERIFIED:
        return SaveResult(f"codeguard: UNVERIFIED [{lang}] 修复后复检未完成：{reason}；"
                          "formatter 可能已修改文件，请重新读取。没有通过/失败结论。")

    passed = rc == 0

    def on_delivered() -> None:
        if checked_identity is not None and checked_identity == identity():
            hook_state.record_file_check(file_path, store, checked_identity)
        bump_state(lang, passed=passed, auto_fixed=auto_fixed)

    if passed:
        note = ""
        if auto_fixed:
            note = f"（已自动运行 {' '.join(cmd_def.get('format') or [])} 修复）"
            if touched_others:
                shown = ", ".join(touched_others[:10])
                more = f" 等 {len(touched_others)} 个" if len(touched_others) > 10 else ""
                note += (f"。⚠️ format 命令还改动了本文件之外的文件{more}：{shown}"
                         "——这些文件你内存里的版本已过期，必须先重新读取再继续操作")
            else:
                note += "（仅本文件被改动，请重新读取）"
        return SaveResult(
            f"codeguard: ✅ {lang} lint passed for {Path(file_path).name}{note}",
            f"codeguard: ✅ {lang} lint passed",
            _on_delivered=on_delivered,
        )

    context, first_problem = _failure_context(file_path, lang, cmd_def, stdout, stderr)
    alert = f"{lang} lint FAILED: {Path(file_path).name}"
    return SaveResult(context, f"codeguard: ⚠️ {alert}",
                      (lang, alert, first_problem), on_delivered)
