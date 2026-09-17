"""gen_language_docs.py：从 languages.json 注册表生成 docs/LANGUAGES.md。

单一事实源模式（借鉴 plugins 库 sync-marketplaces）：
  python3 gen_language_docs.py          # 生成并覆盖 docs/LANGUAGES.md

文档中的表格全部由注册表生成；注册表更新后重跑即可保持文档同步。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "languages.json"
DOC = ROOT / "docs" / "LANGUAGES.md"

STATUS_TITLES = {
    "stable": "Stable（默认强制，V0.1 起）",
    "beta": "Beta（V0.2 起）",
    "planned": "Planned（已识别，linter 在路线图上）",
}
STATUS_ORDER = ["stable", "beta", "planned"]


def cmd_str(lang: dict, key: str) -> str:
    cmd = lang.get(key)
    if not cmd:
        return "—"
    return "`" + " ".join(cmd) + "`"


def main() -> int:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    langs = data["languages"]

    unique = len({l["id"] for l in langs}) - len([l for l in langs if l["id"] in ("dockerfile", "ansible")])
    lines: list[str] = []
    lines.append("# partme-codeguard-plugin 支持的语言\n")
    lines.append(
        f"> 覆盖 **{unique} 种编程语言**（注册表 {len(langs)} 条，含 Dockerfile/Ansible 等文件类型条目）。"
        f"所有语言均可被 `detect_lang` 识别；其中 **{sum(1 for l in langs if l['status'] != 'planned')} 条**已接入 linter 强制门禁"
        "（Stable / Beta），其余列入路线图（Planned，钩子检测到后安全跳过）。\n"
    )
    lines.append(
        "> 本文档由 `scripts/languages.json` 注册表自动生成（`scripts/gen_language_docs.py`）；"
        "新增/调整语言请改注册表后重新生成。\n"
    )

    for status in STATUS_ORDER:
        group = [l for l in langs if l["status"] == status]
        if not group:
            continue
        title = STATUS_TITLES[status]
        lines.append(f"\n## {title}（{len(group)} 种）\n")
        has_cmds = status in ("stable", "beta")
        if has_cmds:
            lines.append("| 语言 | 扩展名 | Lint 命令 | Format 命令 | 安装说明 |")
            lines.append("|---|---|---|---|---|")
            for l in group:
                exts = " ".join(f"`{e}`" for e in l["extensions"]) or "（文件名匹配）"
                lines.append(
                    f"| {l['name']} | {exts} | {cmd_str(l, 'lint')} | {cmd_str(l, 'format')} | {l.get('install_hint') or '—'} |"
                )
        else:
            lines.append("| 语言 | 扩展名 | 计划 Linter | 目标版本 |")
            lines.append("|---|---|---|---|")
            for l in group:
                exts = " ".join(f"`{e}`" for e in l["extensions"]) or "—"
                lines.append(f"| {l['name']} | {exts} | {l.get('install_hint') or '—'} | {l['since']} |")

    lines.append("\n## 检测机制\n")
    lines.append("1. **文件级**：`EXT_LANG_MAP` 覆盖上表全部扩展名 → PostToolUse 钩子按文件判断语言。")
    lines.append("2. **项目级**：`PROJECT_MARKERS` 识别标记文件 → SessionStart 钩子注入语言清单。")
    lines.append("3. **自定义扩展**：项目根 `codeguard.json` 的 `extensions` 可合并/覆盖内置映射，`exclude` 排除文件。")
    lines.append("4. **Planned 状态语言**：安全跳过，不报错、不阻塞。\n")
    lines.append("## 新增语言的流程\n")
    lines.append("1. `scripts/languages.json` 注册表加一条语言定义（id/extensions/markers/lint/format/status）。")
    lines.append("2. `linters/<lang>/` 放配置模板。")
    lines.append("3. `skills/codeguard-<lang>/SKILL.md` 写规范速查（frontmatter `name` == 目录名）。")
    lines.append("4. 重跑 `python3 scripts/gen_language_docs.py` 同步本文档。")
    lines.append("5. `python3 scripts/detect_lang.py <项目>` 冒烟验证。\n")

    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[gen-language-docs] 生成 {DOC}（{len(langs)} 语言）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
