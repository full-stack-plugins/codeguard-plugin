"""用户设置与项目覆盖：仅解析和校验，不扫描源码或执行工具。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .registry import REGISTRY


class ConfigurationError(ValueError):
    """显式项目配置不可用；调用方应呈现 UNVERIFIED，不可当作默认配置。"""


def load_user_config() -> dict:
    """从 ~/.zcode/settings.local.yaml 读插件配置（简化版：正则抠块，不依赖 yaml 库）"""
    cfg_path = Path.home() / ".zcode" / "settings.local.yaml"
    defaults = {
        "enabled_languages": [],
        # strict_mode 已移除：从未有消费点（PostToolUse 恒 exit 0 是协议 §1 设计，
        # 阻塞语义与之矛盾），文档行同步摘除——保留解析等于给用户假旋钮。
        "auto_fix_on_save": True,
        # 默认 300s：Maven 冷缓存 install -DskipTests 普遍超 2 分钟（旧 120s
        # 实测把超时误报为阻断）。AI 可在 ~/.zcode/settings.local.yaml 覆盖。
        "lint_timeout_seconds": 300,
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
    for key in ("auto_fix_on_save",):
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
def load_project_overrides(project_root: str | Path) -> dict:
    """读取项目根 codeguard.json 的 extensions/exclude 自定义映射"""
    cfg = Path(project_root) / "codeguard.json"
    if not cfg.exists():
        return {}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ConfigurationError(f"{cfg}: 无法读取或解析配置: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"{cfg}: 顶层必须为对象")
    extensions = data.get("extensions")
    if extensions is None:
        extensions = {}
    if not isinstance(extensions, dict) or any(
            not isinstance(key, str) or not key.startswith(".") or
            not isinstance(lang, str) or lang not in REGISTRY
            for key, lang in extensions.items()):
        raise ConfigurationError(f"{cfg}: extensions 必须将点号扩展名映射到已注册语言 ID")
    exclude = data.get("exclude")
    if exclude is None:
        exclude = []
    if not isinstance(exclude, list) or not all(isinstance(pattern, str) for pattern in exclude):
        raise ConfigurationError(f"{cfg}: exclude 必须为正则字符串数组")
    for pattern in exclude:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ConfigurationError(f"{cfg}: exclude 包含非法正则 {pattern!r}: {exc}") from exc
    scope = data.get("gate_scope")
    if scope is not None and scope not in ("delta", "repo"):
        raise ConfigurationError(f"{cfg}: gate_scope 只能是 delta 或 repo")
    return {
        "extensions": {k.lower(): v for k, v in extensions.items()},
        "exclude": exclude,
        # 门禁扫描范围："delta"（默认，只查本次改动涉及的文件——存量问题不拦新提交）
        # 或 "repo"（全仓扫描；仍会剔除 vendor/build 等不可编辑目录）
        "gate_scope": scope,
    }


def get_overrides(project_root: str | Path) -> dict:
    # 配置体积很小；不维护一个永不失效的进程级副本（MCP 可长驻数小时）。
    return load_project_overrides(project_root)
