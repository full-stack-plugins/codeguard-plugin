#!/usr/bin/env python3
"""SessionStart 钩子：检测项目语言，把规则注入 AI 上下文。

行为：
1. detect_lang 找到项目语言
2. 检查是否已有 linter 配置（.pre-commit-config.yaml、checkstyle.xml、.clippy.toml、eslint.config.js、ruff.toml）
3. 输出一段 AGENTS.md 风格的提示，让 AI 知道自己在一个被 codeguard 管理的项目里
"""
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (
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
    try:
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_m}" with title "{safe_t}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


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


def main() -> int:
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

    lines.append("- AI 写完代码会被 PostToolUse 钩子自动 lint，告警会出现在这里，按告警里的「怎么修」处理")
    lines.append("- 用户要求「提交/push」时，UserPromptSubmit 钩子会再次确认所有 linter 通过，未通过会拦截提交")
    lines.append("")
    lines.append("**重要**：写代码前先阅读对应语言的规范（见 skills/codeguard-{language}/SKILL.md）")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
