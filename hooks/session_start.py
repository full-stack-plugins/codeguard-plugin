#!/usr/bin/env python3
"""SessionStart 钩子：检测项目语言，把规则注入 AI 上下文。

行为：
1. detect_lang 找到项目语言
2. 检查是否已有 linter 配置（.pre-commit-config.yaml、checkstyle.xml、.clippy.toml、eslint.config.js、ruff.toml）
3. 输出一段 AGENTS.md 风格的提示，让 AI 知道自己在一个被 codeguard 管理的项目里
"""
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import detect_languages, find_project_root

LINTER_CONFIG_FILES = [
    ("java", [".pre-commit-config.yaml", "checkstyle.xml", "pmd.xml"]),
    ("rust", [".pre-commit-config.yaml", "clippy.toml", ".clippy.toml"]),
    ("typescript", [".pre-commit-config.yaml", "eslint.config.js", ".eslintrc.json", ".eslintrc.js"]),
    ("python", [".pre-commit-config.yaml", "ruff.toml", ".ruff.toml", "pyproject.toml"]),
]


def detect_linter_config(project_root: Path) -> dict:
    """返回 {language: [存在的 linter 配置文件]}"""
    found = {}
    for lang, files in LINTER_CONFIG_FILES:
        present = [f for f in files if (project_root / f).exists()]
        if present:
            found[lang] = present
    return found


def main() -> int:
    project_root = find_project_root(os.getcwd())
    if project_root is None:
        project_root = Path(os.getcwd())

    languages = detect_languages(project_root)
    if not languages:
        return 0  # 未识别到代码项目，安静退出

    linter_cfg = detect_linter_config(project_root)

    # 输出注入到 AI 上下文的内容（追加模式）
    lines = []
    lines.append("# codeguard 项目记忆")
    lines.append("")
    lines.append(f"- 项目根: `{project_root}`")
    lines.append(f"- 检测到语言: {', '.join(languages)}")

    if linter_cfg:
        lines.append(f"- 已有的 linter 配置: {linter_cfg}")
    else:
        lines.append("- 未配置任何 linter（建议运行 /init 接入 codeguard）")

    lines.append("- AI 写完代码会被 PostToolUse 钩子强制 lint；失败会阻塞继续")
    lines.append("- 用户要求「提交/push」时，UserPromptSubmit 钩子会再次确认所有 linter 通过")
    lines.append("")
    lines.append("**重要**：写代码前先阅读对应语言的规范（见 skills/codeguard-{language}/SKILL.md）")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
