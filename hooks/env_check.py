#!/usr/bin/env python3
"""SessionStart 钩子：检测项目语言，把规则注入 AI 上下文。

行为：
1. detect_lang 找到项目语言
2. 检查是否已有 linter 配置（.pre-commit-config.yaml、checkstyle.xml、.clippy.toml、eslint.config.js、ruff.toml）
3. 输出一段 AGENTS.md 风格的提示，让 AI 知道自己在一个被 codeguard 管理的项目里
"""
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (  # ensure_user_path/load_user_config 实际定义：scripts/paths.py、scripts/user_config.py
    LANG_COMMANDS,
    REGISTRY,
    detect_languages,
    ensure_user_path,
    find_project_root,
    load_user_config,
    probe_toolchain,
)


def notify(title: str, message: str) -> None:
    """macOS 系统通知（非 darwin 静默）"""
    if sys.platform != "darwin":
        return
    safe_t = title.replace('"', "'")
    safe_m = message.replace('"', "'")[:200]
    with contextlib.suppress(OSError):
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_m}" with title "{safe_t}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def detect_linter_config(project_root: Path) -> dict:
    """返回 {language: [存在的 linter 配置文件]}，由 languages.json 驱动。

    每条 languages.json 条目的 `linter_config_files` 字段声明该语言的 linter
    配置文件路径（glob 模式允许，与 requiresConfig 同语义）。新增语言只需
    在注册表里填字段，env_check 自动盘点——不再有硬编码常量的同步陷阱。
    """
    found = {}
    for lang_id, lang_def in REGISTRY.items():
        files = lang_def.get("linter_config_files") or []
        if not files:
            continue
        present = [f for f in files if (project_root / f).exists()]
        if present:
            found[lang_id] = present
    return found


def _semver_tuple(v: str) -> tuple[int, ...]:
    import re as _re
    m = _re.match(r"(\d+(?:\.\d+)*)", v.strip())
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def version_backlog_note(current: str, cache_root: Path) -> str | None:
    """纯函数：本地插件 cache 存在比 current 更新的版本 → 提示文案；否则 None。

    检测面 = `~/.zcode/cli/plugins/cache/<vendor>/codeguard/<version>` 的**版本目录
    集合**（离线可得的唯一权威）。抓两类漂移：同 vendor 升级后旧目录未清、跨
    vendor 版本参差导致实际生效副本落后于本机已有副本。抓不到"本机最新 vs
    远端仓库最新"（需网络，钩子不联网）——文案里明示提醒核对远端。
    """
    newer: list[str] = []
    installed: list[str] = []
    if not cache_root.is_dir():
        return None
    try:
        for vendor_dir in sorted(cache_root.glob("*/codeguard/*")):
            if not vendor_dir.is_dir():
                continue
            v = vendor_dir.name
            installed.append(v)
            if _semver_tuple(v) > _semver_tuple(current):
                newer.append(v)
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


def main(payload: dict | None = None) -> int:
    # 双副本去重：宿主提供 session_id 时，同会话第二个副本静默（第一份的
    # 摘要已注入；两份都打 = 同一段"项目记忆"重复两遍）。payload 缺字段
    # （测试协议/其它宿主）时不去重，保持旧行为。
    from gate_lib import should_suppress_event

    session_id = (payload or {}).get("session_id")
    if session_id and should_suppress_event(f"start:{session_id}"):
        return 0
    ensure_user_path(from_login_shell=True)   # GUI 宿主 PATH 不含用户级工具目录，先补齐再盘点
    project_root = find_project_root(os.getcwd())
    if project_root is None:
        project_root = Path(os.getcwd())

    languages = detect_languages(project_root)
    if not languages:
        return 0  # 未识别到代码项目，安静退出

    linter_cfg = detect_linter_config(project_root)
    cfg = load_user_config()
    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    # linter 盘点：直接复用门禁的探活（比裸 which 准——能发现 npx 包未装、运行时损坏）
    ready, missing = [], []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        ok, reason = probe_toolchain(cmd_def)
        if ok:
            ready.append(lang)
        else:
            hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"
            missing.append((lang, reason, hint))

    # 输出注入到 AI 上下文的内容（追加模式）
    lines = []
    lines.append("# codeguard 项目记忆")
    lines.append("")
    lines.append(f"- 项目根: `{project_root}`")
    lines.append(f"- 检测到语言: {', '.join(languages)}")

    if missing:
        lines.append("")
        lines.append("**⚠️ 以下语言的检查未生效，这些语言的文件【不会】被检查（提交门禁也会跳过它们）：**")
        for lang, reason, hint in missing:
            lines.append(f"  - {lang}（{reason}）→ 修复: `{hint}`")
        lines.append("  请主动提示用户安装；安装后新写的文件才会被检查。")
        notify(
            "codeguard 部分检查未生效",
            f"{len(missing)} 个语言未生效: " + ", ".join(lang for lang, _, _ in missing) +
            "；详情见对话",
        )
    if ready:
        lines.append(f"- 检查已生效的语言: {', '.join(ready)}")

    if linter_cfg:
        lines.append(f"- 已有的 linter 配置: {linter_cfg}")
    else:
        lines.append("- 未配置任何 linter（建议运行 /init 接入 codeguard）")

    # 双副本检测：partme-ai 与 full-stack-plugins 同时启用时每个钩子事件
    # 跑两遍（历史实测双份触发）；提示用户停用其一，而不是默默重复。
    try:
        import json as _json
        _reg = _json.loads((Path.home() / ".zcode" / "cli" / "config.json").read_text(encoding="utf-8"))
        _orgs = sorted({
            key.split("@", 1)[1]
            for key in (_reg.get("plugins", {}) or {}).get("enabledPlugins", {})
            if key.startswith("codeguard@")
        })
    except (OSError, ValueError, AttributeError):
        _orgs = []
    if len(_orgs) > 1:
        lines.append(
            f"- ⚠️ 检测到 codeguard **双副本同时启用**（{', '.join(_orgs)}）："
            "每个钩子事件会执行两遍，报告与统计可能翻倍或分裂——建议只保留一个来源"
        )

    # 版本积压：本机 cache 里有比当前生效副本更新的版本（实测 8 份副本停留在
    # 0.5.x 而源码已 0.8.x——"发布了但没跑到"的盲区，SessionStart 即可见）
    try:
        _mf = json.loads((PLUGIN_ROOT / ".zcode-plugin" / "plugin.json").read_text(encoding="utf-8"))
        _current = str(_mf.get("version") or "")
    except (OSError, ValueError, AttributeError):
        _current = ""
    if _current:
        _note = version_backlog_note(
            _current, Path.home() / ".zcode" / "cli" / "plugins" / "cache"
        )
        if _note:
            lines.append(_note)

    lines.append("- AI 写完代码会被 PostToolUse 钩子自动 lint，告警会出现在这里，按告警里的「怎么修」处理")
    lines.append("- 用户要求「提交/push」时，UserPromptSubmit 钩子会再次确认所有 linter 通过，未通过会拦截提交")
    lines.append("")
    lines.append("**重要**：写代码前先阅读对应语言的规范（见 skills/codeguard-{language}/SKILL.md）")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        payload: dict = {}
        if not sys.stdin.isatty():
            try:
                data = json.loads(sys.stdin.read())
                if isinstance(data, dict):
                    payload = data
            except (json.JSONDecodeError, ValueError):
                payload = {}
        sys.exit(main(payload))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
