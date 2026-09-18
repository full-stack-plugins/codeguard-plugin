#!/usr/bin/env python3
"""UserPromptSubmit 钩子：用户说"提交/push/部署"时先跑 linter 门禁。

失败时【不阻断 prompt】（exit 2 会把用户消息弹回去，AI 收不到任何指令，
用户被卡死在输入框）——而是 exit 0 + stdout JSON additionalContext：
AI 收到「门禁未通过 + 修复指令」后自动修复、修完自己重新提交，形成闭环。

硬保证由 PreToolUse 钩子（pre_tool_git_guard.py）承担：AI 真去执行
git commit/push 时被拦下，工具级 stderr 会作为结果反馈给 AI 继续修。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

from detect_lang import detect_languages, ensure_user_path, find_project_root, load_user_config  # noqa: E402
from gate_lib import gate_directive, run_gate  # noqa: E402

# 触发此钩子的关键词（中英）
TRIGGER_PATTERNS = [
    "commit", "push", "deploy", "提交", "发布", "部署",
]


def notify(title: str, message: str) -> None:
    """macOS 系统通知（非 darwin 静默；仅失败时打扰，通过靠注入文本确认）"""
    if sys.platform != "darwin":
        return
    import subprocess
    safe_t = title.replace('"', "'")
    safe_m = message.replace('"', "'")[:200]
    try:
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_m}" with title "{safe_t}" sound name "Pop"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


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
        return 0
    user_text = read_user_text()
    if not is_trigger(user_text):
        return 0

    cfg = load_user_config()
    project_root = find_project_root(os.getcwd()) or Path(os.getcwd())
    failures, skipped = run_gate(project_root, cfg)

    if failures:
        # 软引导：prompt 正常送达 AI，同时注入修复指令，AI 自动修复后重新提交
        notify("codeguard 门禁未通过", f"{len(failures)} 个生态待修，AI 正在处理")
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": gate_directive(failures)
            }
        }, ensure_ascii=False))
        return 0

    # 通过：注入明确的成功确认（无此行用户会以为门禁根本没跑）；
    # 即使宿主把它渲染成提示条，文案也是明确的「✅ 通过」语义
    skipped_langs = {s.split()[0] for s in skipped}
    checked = sorted(set(detect_languages(project_root)) - skipped_langs)
    skipped_note = f"；跳过 {len(skipped)} 项（{'；'.join(skipped)}）" if skipped else ""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"codeguard ✅ 提交门禁通过：已检查 {len(checked)} 个语言生态"
                f"（{', '.join(checked) or '无'}），可以提交{skipped_note}。"
            )
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
