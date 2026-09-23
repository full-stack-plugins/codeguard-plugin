"""SessionStart 应用服务：项目盘点、工具可用性与上下文内容。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import load_user_config
from .discovery import detect_languages
from .registry import LANG_COMMANDS, REGISTRY
from .toolchain import ToolchainProbe


@dataclass(frozen=True)
class StartupReport:
    """宿主适配器负责呈现 text，并在必要时发送 notification。"""

    text: str
    notification: tuple[str, str] | None = None


def detect_linter_config(project_root: Path) -> dict:
    """从语言注册表盘点项目已有的 linter 配置。"""
    found = {}
    for lang_id, lang_def in REGISTRY.items():
        files = lang_def.get("linter_config_files") or []
        if not files:
            continue
        present = [f for f in files if (project_root / f).exists()]
        if present:
            found[lang_id] = present
    return found


def _semver_tuple(version: str) -> tuple[int, ...]:
    match = re.match(r"(\d+(?:\.\d+)*)", version.strip())
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def version_backlog_note(current: str, cache_root: Path) -> str | None:
    """离线比较当前版本与 ZCode 缓存中可用的版本目录。"""
    newer: list[str] = []
    installed: list[str] = []
    if not cache_root.is_dir():
        return None
    try:
        for vendor_dir in sorted(cache_root.glob("*/codeguard/*")):
            if not vendor_dir.is_dir():
                continue
            version = vendor_dir.name
            installed.append(version)
            if _semver_tuple(version) > _semver_tuple(current):
                newer.append(version)
    except OSError:
        return None
    if not newer:
        return None
    newest = max(newer, key=_semver_tuple)
    return (
        f"- ⚠️ **版本积压**：当前生效 codeguard `v{current}`，本机 cache 已有更新版本 "
        f"`v{newest}`（共 {len(installed)} 份: {', '.join(sorted(installed))}）——"
        "钩子行为以**生效副本**为准，修复可能已存在却没跑到；请更新插件并清理旧 "
        "cache（`~/.zcode/cli/plugins/cache/*/codeguard/`），同时核对远端是否还有"
        "更新版本（本检测离线，看不到仓库最新版）。"
    )


def build_startup_report(project_root: Path, *, plugin_version: str = "",
                         cache_root: Path | None = None,
                         enabled_plugin_orgs: tuple[str, ...] = ()) -> StartupReport:
    """盘点语言和工具；不打印、不通知，也不读取宿主插件注册文件。"""
    languages = detect_languages(project_root)
    if not languages:
        return StartupReport("")

    linter_cfg = detect_linter_config(project_root)
    cfg = load_user_config()
    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    probe = ToolchainProbe(project_root)
    ready, missing = [], []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        ok, reason = probe.probe(cmd_def)
        if ok:
            ready.append(lang)
        else:
            hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"
            missing.append((lang, reason, hint))

    lines = ["# codeguard 项目记忆", "", f"- 项目根: `{project_root}`",
             f"- 检测到语言: {', '.join(languages)}"]
    notification = None
    if missing:
        lines.extend(["", "**⚠️ 以下语言的检查未生效，这些语言的文件【不会】被检查（提交门禁也会跳过它们）：**"])
        for lang, reason, hint in missing:
            lines.append(f"  - {lang}（{reason}）→ 修复: `{hint}`")
        lines.append("  请主动提示用户安装；安装后新写的文件才会被检查。")
        notification = (
            "codeguard 部分检查未生效",
            f"{len(missing)} 个语言未生效: " + ", ".join(lang for lang, _, _ in missing) + "；详情见对话",
        )
    if ready:
        lines.append(f"- 检查已生效的语言: {', '.join(ready)}")
    if linter_cfg:
        lines.append(f"- 已有的 linter 配置: {linter_cfg}")
    else:
        lines.append("- 未配置任何 linter（建议运行 /init 接入 codeguard）")

    if len(enabled_plugin_orgs) > 1:
        lines.append(
            f"- ⚠️ 检测到 codeguard **双副本同时启用**（{', '.join(sorted(enabled_plugin_orgs))}）："
            "每个钩子事件会执行两遍，报告与统计可能翻倍或分裂——建议只保留一个来源"
        )
    if plugin_version and cache_root is not None:
        note = version_backlog_note(plugin_version, cache_root)
        if note:
            lines.append(note)

    lines.append("- **硬性约束：`.` 开头的目录与文件默认忽略**——不扫描、不检查、不报告（.cursor/、.claude/、.eslintrc.js 等宿主工具目录与配置文件）；两个例外照常生效：入库安全检查照拦密钥模式（.env/*.pem 等），linter 配置发现照常匹配点文件")
    lines.append("- AI 写完代码会被 PostToolUse 钩子自动 lint，告警会出现在这里，按告警里的「怎么修」处理")
    lines.append("- 用户要求「提交/push」时，UserPromptSubmit 钩子会再次确认所有 linter 通过，未通过会拦截提交")
    lines.append("")
    lines.append("**重要**：写代码前先阅读对应语言的规范（见 skills/codeguard-{language}/SKILL.md）")
    return StartupReport("\n".join(lines), notification)
