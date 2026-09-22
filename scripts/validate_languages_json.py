"""scripts/validate_languages_json.py：languages.json 的 11 条 schema 与一致性校验。

CLI：
    python3 scripts/validate_languages_json.py                 # 默认路径 scripts/languages.json
    python3 scripts/validate_languages_json.py --path /tmp/foo.json
    python3 scripts/validate_languages_json.py --help

退出码：
    0 = 全部规则通过
    1 = 一条或多条规则失败（输出 N errors 汇总）
    2 = 参数错误（--path 指向不存在的文件 / --help 文本 / argparse 错误）

实现要点：
- 纯函数 check(registry: dict) -> list[str] 返回错误列表；CLI 仅做 IO + 退出码
- 11 条规则按设计稿固定顺序执行；每条失败累加错误；全部规则结束后再统一输出
- 跨语言冲突（extensions / markers）只对 stable/beta 检查，planned 留给路线图
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

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


def check(registry: dict) -> list[str]:
    """Return all schema and consistency errors; empty list means valid."""
    errs: list[str] = []
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
    errs += _check_since(registry)
    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", default="scripts/languages.json",
                        help="path to languages.json (default: scripts/languages.json)")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: --path '{path}' does not exist", file=sys.stderr)
        return 2
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to read/parse {path}: {exc}", file=sys.stderr)
        return 2

    langs = reg.get("languages", []) if isinstance(reg, dict) else []
    counts: dict[str, int] = {}
    for lang in langs:
        if isinstance(lang, dict):
            counts[lang.get("status", "unknown")] = counts.get(lang.get("status", "unknown"), 0) + 1
    print(f"INFO: languages.json contains {len(langs)} entries "
          f"({counts.get('stable', 0)} stable, {counts.get('beta', 0)} beta, {counts.get('planned', 0)} planned)")

    errs = check(reg)
    if not errs:
        print("INFO: 11 schema rules passed")
        return 0
    for err in errs:
        print(f"ERROR: {err}")
    print(f"SUMMARY: {len(errs)} errors", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())