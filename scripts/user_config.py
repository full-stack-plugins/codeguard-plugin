"""scripts/user_config.py：用户态与项目级配置加载。

暴露三个符号：`load_user_config`（~/.zcode/settings.local.yaml 全局配置）、
`load_project_overrides`（项目根 codeguard.json 自定义映射）、
`get_overrides`（带内存缓存的轻量包装）。
无 subprocess 依赖，被 hooks 与 tests 共享。

为保持向后兼容，`scripts/detect_lang.py` 顶部 re-export 这三个符号，外部
调用方继续 `from detect_lang import load_user_config` 即可。
"""
from __future__ import annotations

import json
import re
from pathlib import Path


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
    scope = data.get("gate_scope")
    return {
        "extensions": {k.lower(): v for k, v in (data.get("extensions") or {}).items()},
        "exclude": list(data.get("exclude") or []),
        # 门禁扫描范围："delta"（默认，只查本次改动涉及的文件——存量问题不拦新提交）
        # 或 "repo"（全仓扫描；仍会剔除 vendor/build 等不可编辑目录）
        "gate_scope": scope if scope in ("delta", "repo") else None,
    }


def get_overrides(project_root: str | Path) -> dict:
    key = str(Path(project_root).resolve())
    if key not in _OVERRIDES_CACHE:
        _OVERRIDES_CACHE[key] = load_project_overrides(project_root)
    return _OVERRIDES_CACHE[key]
