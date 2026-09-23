"""旧语言检测脚本的兼容入口；所有实现分别归属 registry/discovery/config/toolchain。"""
from __future__ import annotations

import json
import sys

from codeguard.config import (
    ConfigurationError,
    get_overrides,
    load_project_overrides,
    load_user_config,
)
from codeguard.discovery import (
    detect_language,
    detect_languages,
    find_project_root,
    project_uses_linter,
)
from codeguard.registry import (
    EXT_LANG_MAP,
    FILE_LANG_MAP,
    LANG_COMMANDS,
    LANG_INSTALL_HINTS,
    LANG_STATUS,
    PROJECT_MARKERS,
    REGISTRY,
    REGISTRY_PATH,
)
from codeguard.toolchain import extract_tool_binaries, probe_toolchain
from paths import ensure_user_path

__all__ = [
    "EXT_LANG_MAP",
    "FILE_LANG_MAP",
    "LANG_COMMANDS",
    "LANG_INSTALL_HINTS",
    "LANG_STATUS",
    "PROJECT_MARKERS",
    "REGISTRY",
    "REGISTRY_PATH",
    "detect_language",
    "detect_languages",
    "ensure_user_path",
    "extract_tool_binaries",
    "find_project_root",
    "get_overrides",
    "load_project_overrides",
    "load_user_config",
    "probe_toolchain",
    "project_uses_linter"
]


def main() -> int:
    try:
        root = find_project_root(sys.argv[1] if len(sys.argv) > 1 else ".")
        print(json.dumps(detect_languages(root), ensure_ascii=False) if root else "[]")
        return 0
    except ConfigurationError as exc:
        print(f"[codeguard] UNVERIFIED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
