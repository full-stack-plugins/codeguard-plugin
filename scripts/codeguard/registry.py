"""已校验的语言注册表及派生索引；不负责项目发现或工具执行。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .registry_schema import check

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "languages.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, dict[str, Any]]:
    """加载语言注册表：id -> language 定义"""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    errors = check(data)
    if errors:
        raise ValueError(f"{path}: " + "; ".join(errors))
    return {lang["id"]: lang for lang in data["languages"]}


REGISTRY = load_registry()


# === 派生表（由注册表构建，保持与旧 API 兼容） ===
EXT_LANG_MAP: dict[str, str] = {}
FILE_LANG_MAP: dict[str, str] = {}
PROJECT_MARKERS: dict[str, str] = {}
LANG_COMMANDS: dict[str, dict[str, Any]] = {}
LANG_INSTALL_HINTS: dict[str, str] = {}
LANG_STATUS: dict[str, str] = {}

for _id, _lang in REGISTRY.items():
    for _ext in _lang.get("extensions", []):
        EXT_LANG_MAP[_ext.lower()] = _id
    for _fname in _lang.get("file_names", []):
        FILE_LANG_MAP[_fname] = _id
    for _marker in _lang.get("markers", []):
        PROJECT_MARKERS[_marker] = _id
    LANG_STATUS[_id] = _lang.get("status", "planned")
    # 门禁命令表只收 Stable/Beta；Planned 语言安全跳过（命令留作路线图参考）
    if _lang.get("status") in ("stable", "beta"):
        _lint, _fmt = _lang.get("lint"), _lang.get("format")
        if _lint or _fmt:
            LANG_COMMANDS[_id] = {
                "lint": _lint,
                "format": _fmt,
                "gate": _lang.get("gate"),       # 项目级门禁命令（文件型 linter 必须传文件清单）
                "probe": _lang.get("probe"),     # 显式探活命令（npx 系必配，覆盖包未装场景）
                "requiresConfig": _lang.get("requiresConfig"),  # 未接入配置的项目归 skipped
                "install_hint": _lang.get("install_hint"),
                "append_files": _lang.get("append_files", True),
            }
    if _lang.get("install_hint"):
        LANG_INSTALL_HINTS[_id] = _lang["install_hint"]
