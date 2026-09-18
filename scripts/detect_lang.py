"""detect_lang.py：项目语言检测 + 用户配置加载 + linter 命令表。

实现逻辑（借鉴 codegraph 的统一注册表管线）：
1. **单一事实源** `scripts/languages.json`：每语言一条注册（id/name/extensions/
   markers/lint/format/status/install_hint/since），识别与命令表全部由它构建；
2. **扩展名自动识别，零配置**：内置映射表覆盖全部注册语言；
3. **项目级自定义映射**：项目根 `codeguard.json` 的 `extensions` 可合并/覆盖内置
   默认（如 `{ "extensions": { ".dota_lua": "lua" } }`），`exclude` 数组排除文件模式；
4. **安全降级**：注册表中 lint/format 为 null 的语言（Planned 状态）安全跳过。

被 hooks/、commands/、skills/ 共享。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "languages.json"


def _load_registry() -> dict[str, dict[str, Any]]:
    """加载语言注册表：id -> language 定义"""
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {lang["id"]: lang for lang in data["languages"]}


REGISTRY = _load_registry()


# === 派生表（由注册表构建，保持与旧 API 兼容） ===
EXT_LANG_MAP: dict[str, str] = {}
FILE_LANG_MAP: dict[str, str] = {}
PROJECT_MARKERS: dict[str, str] = {}
LANG_COMMANDS: dict[str, dict[str, list[str]]] = {}
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
                "install_hint": _lang.get("install_hint"),
            }
    if _lang.get("install_hint"):
        LANG_INSTALL_HINTS[_id] = _lang["install_hint"]


# === 项目根 codeguard.json 自定义扩展映射（借鉴 codegraph.json 设计） ===
_OVERRIDES_CACHE: dict[str, dict] = {}


def load_project_overrides(project_root: str | Path) -> dict:
    """读取项目根 codeguard.json 的 extensions/exclude 自定义映射"""
    cfg = Path(project_root) / "codeguard.json"
    if not cfg.exists():
        return {}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        "extensions": {k.lower(): v for k, v in (data.get("extensions") or {}).items()},
        "exclude": list(data.get("exclude") or []),
    }


def get_overrides(project_root: str | Path) -> dict:
    key = str(Path(project_root).resolve())
    if key not in _OVERRIDES_CACHE:
        _OVERRIDES_CACHE[key] = load_project_overrides(project_root)
    return _OVERRIDES_CACHE[key]


def detect_language(file_path: str | Path, project_root: Path | None = None) -> str | None:
    """按扩展名/文件名判断语言；支持 codeguard.json 自定义映射；非代码文件返回 None"""
    p = Path(file_path)
    overrides = get_overrides(project_root) if project_root else {}
    ext_map = {**EXT_LANG_MAP, **overrides.get("extensions", {})}
    lang = ext_map.get(p.suffix.lower())
    if lang:
        return lang
    # 文件名级识别（Dockerfile 等）
    return FILE_LANG_MAP.get(p.name)


def find_project_root(start: str | Path) -> Path | None:
    """从 start 路径向上找项目根（识别到 .git 或任一项目标记文件即停）"""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for _ in range(10):
        if (p / ".git").exists():
            return p
        for marker in PROJECT_MARKERS:
            if (p / marker).exists():
                return p
        if p.parent == p:
            return None
        p = p.parent
    return None


def _excluded(f: Path, exclude_patterns: list[str]) -> bool:
    return any(re.search(pat, str(f)) for pat in exclude_patterns)


def detect_languages(project_root: str | Path) -> list[str]:
    """检测项目根中存在的语言：标记文件 + 常见源码目录浅扫描 + 根目录一层；
    支持 codeguard.json 的 exclude 排除"""
    project_root = Path(project_root)
    overrides = get_overrides(project_root)
    exclude = overrides.get("exclude", [])
    ext_map = {**EXT_LANG_MAP, **overrides.get("extensions", {})}

    langs: set[str] = set()
    # 1) 标记文件
    for marker, lang in PROJECT_MARKERS.items():
        if (project_root / marker).exists():
            langs.add(lang)
    # 2) 常见源码目录浅扫描（含脚本/二进制/钩子目录：shell 等胶水语言常在这些位置）
    src_dirs = ["src", "src/main", "lib", "pkg", "app", "tests", "test",
                "scripts", "bin", "hooks", "cmd", "internal"]
    for d in src_dirs:
        base = project_root / d
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.is_file() and not _excluded(f, exclude):
                lang = detect_language(f)
                if lang:
                    langs.add(lang)
    # 3) 根目录一层（小脚本项目）
    for f in project_root.iterdir():
        if f.is_file() and not _excluded(f, exclude):
            lang = detect_language(f)
            if lang:
                langs.add(lang)
    return sorted(langs)


def load_user_config() -> dict:
    """从 ~/.zcode/settings.local.yaml 读插件配置（简化版：正则抠块，不依赖 yaml 库）"""
    cfg_path = Path.home() / ".zcode" / "settings.local.yaml"
    defaults = {
        "enabled_languages": [],
        "strict_mode": True,
        "auto_fix_on_save": True,
        "lint_timeout_seconds": 120,
    }
    if not cfg_path.exists():
        return defaults
    try:
        text = cfg_path.read_text()
    except OSError:
        return defaults
    cfg = dict(defaults)
    m = re.search(r"codeguard:\s*(\{.*?\n\})", text, re.DOTALL)
    if not m:
        return cfg
    block = m.group(1)
    for key in ("strict_mode", "auto_fix_on_save"):
        mm = re.search(rf"{key}:\s*(true|false)", block)
        if mm:
            cfg[key] = mm.group(1) == "true"
    mm = re.search(r"lint_timeout_seconds:\s*(\d+)", block)
    if mm:
        cfg["lint_timeout_seconds"] = int(mm.group(1))
    mm = re.search(r"enabled_languages:\s*\[([^\]]*)\]", block)
    if mm:
        items = [s.strip().strip("\"'") for s in mm.group(1).split(",") if s.strip()]
        cfg["enabled_languages"] = items
    return cfg


if __name__ == "__main__":
    import sys

    pr = find_project_root(sys.argv[1] if len(sys.argv) > 1 else ".")
    if pr:
        print(json.dumps(detect_languages(pr), ensure_ascii=False))
    else:
        print("[]")
