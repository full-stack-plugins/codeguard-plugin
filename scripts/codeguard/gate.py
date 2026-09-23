"""门禁应用服务：选择准确/观察内容面，汇总检查并持久化原仓审计。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from scope import changed_files

from .cache import cache_path, load_result, store_result
from .config import ConfigurationError, get_overrides
from .discovery import detect_languages
from .fingerprint import check_identity, digest, repository_identity
from .gate_checks import check_language
from .hook_state import codeguard_home, record_gate_decision
from .models import GateOutcome
from .registry import LANG_COMMANDS
from .spec_validation import validate as _openspec_validate
from .toolchain import ToolchainProbe


def _gate_cache_path(project_root: Path) -> Path:
    return cache_path(codeguard_home(), project_root)


def _worktree_fingerprint(project_root: Path, *, max_files: int = 10000) -> str | None:
    """兼容导出；有预算的内容身份，无法完整采集则不缓存。"""
    return repository_identity(project_root, max_files=max_files)


def _gate_cache_key(
    project_root: Path, languages: list, *,
    mode: str = "commit",
    lanes: tuple[str, ...] | list[str] | None = None,
    extra: tuple[str, ...] | list[str] | None = None,
    scope: str = "delta",
    cfg: dict | None = None,
) -> str | None:
    identity = check_identity(project_root, cfg or {},
                              {lang: LANG_COMMANDS.get(lang, {}) for lang in languages})
    if identity is None:
        return None
    return digest({"identity": identity, "mode": mode, "languages": sorted(languages),
                   "lanes": lanes, "extra": sorted(extra or ()), "scope": scope})


GATE_CACHE_TTL = 60  # 仅软观察结果；准确 Git 门禁从不读取它。


def run_gate(
    project_root: Path,
    cfg: dict,
    languages: list | None = None,
    *,
    mode: str = "commit",
    lanes: tuple[str, ...] | list[str] | None = None,
    extra: tuple[str, ...] | list[str] | None = None,
    exact: bool = False,
    pending_commit: bool = False,
) -> tuple[list, list]:
    """运行 linter 门禁（跨进程结果缓存 + 并行执行）。

    `languages` 可选：调用方（UserPromptSubmit）可传入用户消息里提到的
    语言子集，门禁只跑该子集；不传则按 `detect_languages()` 全量探测。
    `lanes`/`extra`：本次要检查的文件面（见 scope.changed_files）——硬门禁
    （PreToolUse）按命令链传入预测面；不传 = 三路宽口径（软门禁 UPS 无命令
    上下文，按"工作树有待提交改动就提醒"的宽口径注入，不硬拦）。

    仅软观察在输入身份相同且结论完整时短时复用；硬门禁 exact=True
    始终基于准确快照检查。身份采集失败不缓存，不影响实际检查。

    返回 (failures, skipped)：
    - failures: [(lang, 问题节选, 修复命令, install_hint)]
    - skipped:  [str] 无法验证的说明（工具未装/超时），不阻塞
    """
    if exact:
        from git_snapshot import SnapshotError, validation_tree
        from scope import is_build_artifact
        try:
            with validation_tree(project_root, mode, lanes=lanes, extra=extra,
                                 pending_commit=pending_commit) as (snapshot, paths):
                selected = languages if languages is not None else detect_languages(snapshot)
                enabled = cfg.get("enabled_languages", [])
                if enabled and enabled != ["auto"]:
                    selected = [lang for lang in selected if lang in enabled]
                requested_scope = (get_overrides(snapshot) or {}).get("gate_scope") or "delta"
                return run_batch(snapshot, cfg, selected, scope=requested_scope,
                                          changed=[p for p in paths if not is_build_artifact(p)],
                                          audit_root=project_root)
        except (SnapshotError, OSError, ValueError) as exc:
            return [], [f"git UNVERIFIED：无法验证准确内容快照：{exc}"]
    try:
        overrides = get_overrides(project_root)
        if languages is None:
            languages = detect_languages(project_root)
    except ConfigurationError as exc:
        return [], [f"配置 UNVERIFIED：{exc}"]
    if not languages:
        return [], []
    # 作用域：项目可用 codeguard.json gate_scope 覆盖；缺省 = git 仓 delta、
    # 非 git 目录全量。delta 只检查本次改动涉及的文件——存量问题不拦新提交。
    changed = changed_files(project_root, mode=mode, lanes=lanes, extra=extra)
    scope = overrides.get("gate_scope") or (
        "delta" if changed is not None else "repo"
    )
    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    ck = _gate_cache_key(project_root, languages, mode=mode, lanes=lanes, extra=extra,
                         scope=scope, cfg=cfg)
    cache_file = _gate_cache_path(project_root)
    cached = load_result(cache_file, ck, GATE_CACHE_TTL)
    if cached is not None:
        return cached

    failures, skipped = run_batch(
        project_root, cfg, languages,
        scope=scope, changed=changed if scope == "delta" else None,
        baseline_ref="@{upstream}" if mode == "push" else "HEAD",
    )

    after = _gate_cache_key(project_root, languages, mode=mode, lanes=lanes, extra=extra,
                           scope=scope, cfg=cfg) if ck and not skipped else None
    if ck is not None and ck == after:
        store_result(cache_file, ck, failures, skipped)
    return failures, skipped



def run_batch(project_root: Path, cfg: dict, languages: list, *, scope: str = "repo",
              changed: list[str] | None = None, baseline_ref: str = "HEAD",
              audit_root: Path | None = None) -> tuple[list, list]:
    """worker 返回独立结果；调用线程保序汇总并保留会话归属，不共享可变备注。"""
    try:
        get_overrides(project_root)
    except ConfigurationError as exc:
        return [], [f"配置 UNVERIFIED：{exc}"]
    probe = ToolchainProbe(project_root)
    worker = partial(check_language, project_root, cfg, scope=scope,
                     changed=changed, baseline_ref=baseline_ref, probe=probe)

    def checked(lang: str) -> GateOutcome:
        try:
            return worker(lang)
        except Exception as exc:  # noqa: BLE001 — 单语言故障不得抹去其它语言的已确认结论
            return GateOutcome(notes=(f"{lang} UNVERIFIED：检查器内部异常（{type(exc).__name__}）；请重试并检查诊断",))

    with ThreadPoolExecutor(max_workers=min(4, max(1, len(languages)))) as pool:
        results = list(pool.map(checked, languages))
    failures, skipped = [], []
    for lang, outcome in zip(languages, results, strict=True):
        if outcome.failure:
            failures.append(outcome.failure)
        skipped.extend(outcome.notes)
        for decision in outcome.decisions:
            record_gate_decision(audit_root or project_root, lang, list(decision.argv),
                                 decision.returncode, decision.status, decision.reason,
                                 execution_root=project_root)
    try:
        spec = _openspec_validate(project_root, timeout_seconds=cfg.get("lint_timeout_seconds", 300))
        failures.extend(spec["failures"])
        if spec["skipped"]:
            skipped.append(spec["skipped"])
    except Exception as exc:  # noqa: BLE001 — 可选集成异常仍明确未验证
        skipped.append(f"openspec UNVERIFIED：{exc!r}")
    return failures, skipped
