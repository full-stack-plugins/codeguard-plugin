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

from detect_lang import (  # noqa: E402
    LANG_COMMANDS,
    detect_languages,
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

    print(f"[codeguard] 检测到「提交/push」意图，运行 linter 门禁检查...")
    failures = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        timeout = cfg.get("lint_timeout_seconds", 120)
        try:
            proc = subprocess.run(
                cmd_def["lint"], cwd=project_root, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            failures.append((lang, "timeout"))
            continue
        except FileNotFoundError:
            failures.append((lang, "linter not installed"))
            continue
        if proc.returncode != 0:
            failures.append((lang, f"exit={proc.returncode}\n{proc.stderr[-1000:]}"))

    if failures:
        print(f"\n[codeguard] \u274c 门禁检查失败，请先修复:", file=sys.stderr)
        for lang, info in failures:
            print(f"  - {lang}: {info}", file=sys.stderr)
        print(f"\n[codeguard] 自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py", file=sys.stderr)
        return 2

    print(f"[codeguard] \u2705 所有 linter 通过，可以提交")
    return 0


if __name__ == "__main__":
    sys.exit(main())
