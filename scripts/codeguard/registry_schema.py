"""语言注册表的纯校验规则；CLI 和运行时共用，不读取文件或启动进程。"""
from __future__ import annotations

import re

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _check_top_level(reg: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(reg.get("version"), int) or reg["version"] < 1:
        errs.append("all:top-level: 'version' missing or not positive int")
    langs = reg.get("languages")
    if not isinstance(langs, list) or not langs:
        errs.append("all:top-level: 'languages' missing or empty")
    levels = reg.get("status_levels")
    for required in ("stable", "beta", "planned"):
        if not isinstance(levels, dict) or required not in levels:
            errs.append(f"all:top-level: status_levels missing '{required}'")
    return errs


def _check_unique_ids(reg: dict) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id")
        if lid in seen:
            errs.append(f"all:ids: duplicate id '{lid}'")
        if isinstance(lid, str):
            seen.add(lid)
    return errs


def _check_id_kebab(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id")
        if isinstance(lid, str) and not KEBAB_RE.match(lid):
            errs.append(f"{lid}:id: not kebab-case")
    return errs


def _check_status(reg: dict) -> list[str]:
    errs: list[str] = []
    levels = reg.get("status_levels", {})
    valid = set(levels.keys())
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        st = lang.get("status")
        if st not in valid:
            errs.append(f"{lid}:status: '{st}' not in status_levels {sorted(valid)}")
    return errs


def _check_ext_or_marker_collision(reg: dict, key: str, label: str) -> list[str]:
    errs: list[str] = []
    owners: dict[str, str] = {}
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        if lang.get("status") not in ("stable", "beta"):
            continue
        lid = lang.get("id", "<?>")
        for ext in lang.get(key, []) or []:
            if ext in owners and owners[ext] != lid:
                errs.append(f"all:{key}s: '{ext}' owned by '{owners[ext]}' and '{lid}'")
            owners[ext] = lid
    return errs


def _check_extensions_dot_prefix(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        for ext in lang.get("extensions", []) or []:
            if not isinstance(ext, str) or not ext.startswith("."):
                errs.append(f"{lid}:extensions: '{ext}' must start with '.'")
    return errs


def _check_lint_format_shape(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        for field in ("lint", "format"):
            val = lang.get(field)
            if val is None:
                continue
            if not isinstance(val, list) or not all(isinstance(s, str) and s for s in val):
                errs.append(f"{lid}:{field}: must be list of non-empty strings")
    return errs


def _check_status_command_presence(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        st = lang.get("status")
        if st in ("stable", "beta"):
            lint = lang.get("lint") or []
            fmt = lang.get("format") or []
            if not lint and not fmt:
                errs.append(f"{lid}:commands: stable/beta requires non-empty lint or format")
        elif st == "planned":
            lint = lang.get("lint") or []
            fmt = lang.get("format") or []
            if lint or fmt:
                errs.append(f"{lid}:commands: planned must leave lint/format empty")
    return errs


def _check_requires_config(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        rc = lang.get("requiresConfig")
        if rc is None:
            continue
        if not isinstance(rc, list) or not all(isinstance(s, str) for s in rc):
            errs.append(f"{lid}:requiresConfig: must be list of strings")
    return errs


def _check_linter_config_files(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        cf = lang.get("linter_config_files")
        if cf is None:
            continue
        if not isinstance(cf, list) or not all(isinstance(s, str) for s in cf):
            errs.append(f"{lid}:linter_config_files: must be list of strings")
    return errs


def _check_since(reg: dict) -> list[str]:
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        st = lang.get("status")
        since = lang.get("since")
        if st in ("stable", "beta") and not isinstance(since, str) or (st in ("stable", "beta") and since == ""):
            errs.append(f"{lid}:since: stable/beta requires non-empty 'since' string")
    return errs


def _check_gate_severity_pin(reg: dict) -> list[str]:
    """gate 命令里调用支持 severity 的工具时必须钉扎级别。

    背景（0.8.x 前的实测坑）：同一份 shell gate 在部分发布版本里没带
    `--severity=warning`，info/style 级发现（SC2059/SC2295）也会阻塞提交；
    缺了这个钉扎，门禁结论取决于用户 cache 里恰好是哪个发布版本。
    shellcheck 支持 --severity；markdownlint 走 config 文件，不在此列。
    """
    errs: list[str] = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        for field in ("gate", "lint"):
            joined = " ".join(lang.get(field) or [])
            if "shellcheck" in joined and "--severity=" not in joined:
                errs.append(f"{lid}:{field}: shellcheck must pin --severity= (drift guard)")
    return errs


def _check_shapes(registry: object) -> list[str]:
    """先验证可遍历字段，语义规则不得因非法 JSON 形状而崩溃。"""
    if not isinstance(registry, dict):
        return ["all:top-level: registry must be an object"]
    errors = []
    if "status_levels" in registry and not isinstance(registry["status_levels"], dict):
        errors.append("all:top-level: status_levels must be an object")
    languages = registry.get("languages")
    if not isinstance(languages, list):
        return errors + ["all:top-level: languages must be a list"]
    for index, language in enumerate(languages):
        if not isinstance(language, dict):
            errors.append(f"languages[{index}]: must be an object")
            continue
        lid = language.get("id")
        for field in ("id", "status"):
            if not isinstance(language.get(field), str) or not language[field]:
                errors.append(f"languages[{index}]:{field}: must be a non-empty string")
        for field in ("extensions", "markers", "file_names", "lint", "format", "gate", "probe",
                      "requiresConfig", "linter_config_files"):
            value = language.get(field)
            if value is not None and (not isinstance(value, list) or
                                      not all(isinstance(v, str) and v for v in value)):
                errors.append(f"{lid}:{field}: must be list of non-empty strings")
        if "append_files" in language and not isinstance(language["append_files"], bool):
            errors.append(f"{lid}:append_files: must be boolean")
    return errors


def check(registry: object) -> list[str]:
    """Return all schema and consistency errors; empty list means valid."""
    errs = _check_shapes(registry)
    if errs:
        return errs
    errs += _check_top_level(registry)
    errs += _check_unique_ids(registry)
    errs += _check_id_kebab(registry)
    errs += _check_status(registry)
    errs += _check_ext_or_marker_collision(registry, "extensions", "extension")
    errs += _check_ext_or_marker_collision(registry, "markers", "marker")
    errs += _check_extensions_dot_prefix(registry)
    errs += _check_lint_format_shape(registry)
    errs += _check_status_command_presence(registry)
    errs += _check_requires_config(registry)
    errs += _check_linter_config_files(registry)
    errs += _check_since(registry)
    errs += _check_gate_severity_pin(registry)
    return errs
