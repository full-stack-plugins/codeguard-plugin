#!/usr/bin/env python3
"""SessionStart 钩子：检测项目语言，把规则注入 AI 上下文。

行为：
1. detect_lang 找到项目语言
2. 检查是否已有 linter 配置（.pre-commit-config.yaml、checkstyle.xml、.clippy.toml、eslint.config.js、ruff.toml）
3. 输出一段 AGENTS.md 风格的提示，让 AI 知道自己在一个被 codeguard 管理的项目里
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (
    LANG_COMMANDS,
    detect_languages,
    ensure_user_path,
    extract_tool_binaries,
    find_project_root,
    load_user_config,
)

LINTER_CONFIG_FILES = [
    ("java", [".pre-commit-config.yaml", "checkstyle.xml", "pmd.xml"]),
    ("rust", [".pre-commit-config.yaml", "clippy.toml", ".clippy.toml"]),
    ("typescript", [".pre-commit-config.yaml", "eslint.config.js", ".eslintrc.json", ".eslintrc.js"]),
    ("python", [".pre-commit-config.yaml", "ruff.toml", ".ruff.toml", "pyproject.toml"]),
]


def required_binaries(cmd_def: dict) -> set[str]:
    """从 lint/gate 命令提取必须存在的可执行名（统一走 detect_lang，含运行时依赖）"""
    return set(extract_tool_binaries(cmd_def))


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
    """返回 {language: [存在的 linter 配置文件]}"""
    found = {}
    for lang, files in LINTER_CONFIG_FILES:
        present = [f for f in files if (project_root / f).exists()]
        if present:
            found[lang] = present
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

    # linter 安装盘点：未安装的语言检查不生效，必须让 AI 和用户第一时间知道
    ready, missing = [], []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        bins = required_binaries(cmd_def)
        if bins and not all(shutil.which(b) for b in bins):
            hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"
            missing.append((lang, ", ".join(sorted(bins)), hint))
        else:
            ready.append(lang)

    # 输出注入到 AI 上下文的内容（追加模式）
    lines = []
    lines.append("# codeguard 项目记忆")
    lines.append("")
    lines.append(f"- 项目根: `{project_root}`")
    lines.append(f"- 检测到语言: {', '.join(languages)}")

    if missing:
        lines.append("")
        lines.append("**⚠️ 以下语言的 linter 未安装，这些语言的文件【不会】被检查（提交门禁也会跳过它们）：**")
        for lang, bins, hint in missing:
            lines.append(f"  - {lang}（缺 {bins}）→ 安装: `{hint}`")
        lines.append("  请主动提示用户安装；安装后新写的文件才会被检查。")
        notify(
            "codeguard 部分检查未生效",
            f"缺 {len(missing)} 个 linter: " + ", ".join(lang for lang, _, _ in missing) +
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
    sys.exit(main())
