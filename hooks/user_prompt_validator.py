#!/usr/bin/env python3
"""UserPromptSubmit 钩子：用户说"提交/push/部署"时强制检查所有 linter 通过。

这是 codeguard 的「门禁钩子」——把规范检查从"提交后看 CI 红"前移到
"AI 在用户说提交那一刻就拦截"。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (
    LANG_COMMANDS,
    detect_languages,
    ensure_user_path,
    find_project_root,
    load_user_config,
)

# 触发此钩子的关键词（中英）
TRIGGER_PATTERNS = [
    "commit", "push", "deploy", "提交", "发布", "部署",
]


def is_trigger(user_text: str) -> bool:
    if not user_text:
        return False
    text = user_text.lower()
    return any(p in text for p in TRIGGER_PATTERNS)


def read_user_text() -> str:
    if sys.stdin.isatty():
        return ""
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return ""
    return data.get("user_prompt") or data.get("prompt") or ""


def main() -> int:
    ensure_user_path(from_login_shell=True)   # GUI 宿主 PATH 不含用户级工具目录
    # 逃生门：设置此环境变量后跳过提交门禁（用于确实需要绕过的场景）
    if os.environ.get("CODEGUARD_SKIP_GATE"):
        print("[codeguard] CODEGUARD_SKIP_GATE 已设置，跳过提交门禁")
        return 0
    user_text = read_user_text()
    if not is_trigger(user_text):
        return 0

    cfg = load_user_config()
    project_root = find_project_root(os.getcwd()) or Path(os.getcwd())
    languages = detect_languages(project_root)
    if not languages:
        return 0

    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    print("[codeguard] 检测到「提交/push」意图，运行 linter 门禁检查...")
    failures = []   # (lang, 问题摘要, 修复建议)
    skipped = []    # 无法验证的生态（工具未装/超时/无项目级命令），不阻塞
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        # 门禁用项目级命令（gate）：shellcheck/php -l 等文件型 linter 裸跑会报参数错
        gate_cmd = cmd_def.get("gate") or cmd_def.get("lint")
        if not gate_cmd:
            continue
        timeout = cfg.get("lint_timeout_seconds", 120)
        hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"
        try:
            proc = subprocess.run(
                gate_cmd, cwd=project_root, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            skipped.append(f"{lang} 检查超时（>{timeout}s），本次未验证")
            continue
        except FileNotFoundError:
            skipped.append(f"{lang} linter 未安装，本次未验证（安装: {hint}）")
            continue
        if proc.returncode == 0:
            continue
        if lang == "markdown":
            # 文档类风格问题不阻塞提交
            skipped.append("markdown 风格告警（不阻塞提交）")
            continue
        # 问题摘要：linter 输出头部是最具体的问题；usage/横幅类噪音剔除
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        detail = "\n".join(ln for ln in (out or err).splitlines() if ln.strip())[:600]
        fix = f"自动修复: {' '.join(cmd_def['format'])}" if cmd_def.get("format") else f"按上述问题修复后重试"
        failures.append((lang, detail, fix, hint))

    for s in skipped:
        print(f"[codeguard] ⏭️ {s}")

    if failures:
        lines = [
            "",
            f"codeguard ❌ 提交门禁：{len(failures)} 个生态未通过，修复后重新提交",
            "=" * 60,
        ]
        for lang, detail, fix, hint in failures:
            lines.append(f"【{lang}】发现的问题（节选）：")
            lines.append(detail if detail else f"  退出码 {lang} lint 非零，无文本输出")
            lines.append(f"  ▶ 怎么修: {fix}")
            lines.append(f"  ▶ 未安装工具时先安装: {hint}")
            lines.append("-" * 60)
        lines.append(f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py")
        lines.append("确需绕过: CODEGUARD_SKIP_GATE=1 后重新提交")
        print("\n".join(lines), file=sys.stderr)
        return 2

    if skipped:
        print("[codeguard] ⚠️ 部分生态未能验证（见上方 ⏭️ 行），其余通过")
    print("[codeguard] ✅ linter 门禁通过，可以提交")
    return 0


if __name__ == "__main__":
    sys.exit(main())
