"""codeguard PostToolUse 钩子：AI 写文件后自动 lint 并注入告警到 AI 上下文。

输出协议（三端兼容，均为 stdout 合法 JSON、exit 0 不阻断）：
  ZCode      → 解析 hookSpecificOutput.additionalContext 注入 AI 上下文
  Codex CLI  → 同一协议注入 developer context；systemMessage 显示为 UI 警告
               （纯文本 stdout 会被忽略，必须 JSON）
  Kimi Code  → PostToolUse 观察型，exit 0 时 stdout 内容附加到上下文
  用户同时收到 macOS 系统通知（可关闭）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from detect_lang import (
    LANG_COMMANDS,
    detect_language,
    find_project_root,
    load_user_config,
)

STATE_FILE = PLUGIN_ROOT / ".session_state.json"


def bump_state(lang: str, passed: bool, auto_fixed: bool = False) -> None:
    """累计本会话 lint 结果（Stop 钩子读取汇总）；写失败静默忽略"""
    state = {}
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        pass
    entry = state.setdefault(lang, {"total": 0, "passed": 0, "failed": 0, "auto_fixed": 0})
    entry["total"] += 1
    entry["passed" if passed else "failed"] += 1
    if auto_fixed:
        entry["auto_fixed"] += 1
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))
    except OSError:
        pass


def mac_notify(title: str, message: str) -> None:
    """macOS 系统通知（用户视觉提醒；非 macOS 静默跳过）"""
    if sys.platform != "darwin":
        return
    safe_title = title.replace('"', "'")
    safe_msg = message.replace('"', "'")[:200]
    subprocess.Popen(
        ["osascript", "-e",
         f'display notification "{safe_msg}" with title "{safe_title}" sound name "Pop"'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "", "command not found"


def read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return {}


def extract_file_path(payload: dict) -> str:
    for c in (payload.get("file_path"),
              (payload.get("tool_input") or {}).get("file_path"),
              (payload.get("tool_input") or {}).get("path"),
              (payload.get("input") or {}).get("file_path")):
        if c:
            return str(c)
    return ""


def should_skip(file_path: str, languages: list[str]) -> tuple[bool, str]:
    if not file_path:
        return True, ""
    lang = detect_language(file_path)
    if not lang:
        return True, ""
    if languages and lang not in languages:
        return True, lang
    return False, lang


def main() -> int:
    payload = read_payload()
    file_path = extract_file_path(payload)
    if not file_path:
        return 0

    cfg = load_user_config()
    enabled = cfg.get("enabled_languages", [])
    project_root = find_project_root(os.getcwd()) or Path(os.getcwd())

    skip, lang = should_skip(file_path, enabled)
    if skip:
        return 0

    # 文档类语言不拦 AI 写作流（AI 产出的报告/文档常不合 lint 严格规则，
    # 拦截会造成死循环）；提交门禁阶段仍有宽松校验
    if lang == "markdown":
        return 0

    cmd_def = LANG_COMMANDS.get(lang)
    if not cmd_def:
        return 0

    timeout = cfg.get("lint_timeout_seconds", 120)
    lint_cmd = cmd_def.get("lint")
    if not lint_cmd:
        return 0

    rc, stdout, stderr = run(lint_cmd, cwd=project_root, timeout=timeout)

    if rc == 0:
        bump_state(lang, passed=True)
        # 注入 AI 上下文：告诉 AI 该文件通过了门禁
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"codeguard: ✅ {lang} lint passed for {Path(file_path).name}"
            },
            "systemMessage": f"codeguard: ✅ {lang} lint passed",
        }, ensure_ascii=False))
        return 0

    # lint 失败 → 尝试自动修复
    auto_fixed = False
    if cfg.get("auto_fix_on_save", True):
        fmt_cmd = cmd_def.get("format")
        if fmt_cmd:
            print(f"[codeguard] ⚠️ {lang} lint failed, attempting auto-fix...")
            frc, _, _ = run(fmt_cmd, cwd=project_root, timeout=timeout + 60)
            if frc == 0:
                auto_fixed = True
                print("[codeguard] ✅ auto-fix succeeded, re-running lint...")
                rc, stdout, stderr = run(lint_cmd, cwd=project_root, timeout=timeout)

    passed = rc == 0
    bump_state(lang, passed=passed, auto_fixed=auto_fixed)

    # 构建告警摘要
    alert = f"{lang} lint {'passed' if passed else 'FAILED'}: {Path(file_path).name}"
    detail = (stdout or stderr)[-500:] if (stdout or stderr) else ""

    # ===== 三端标准：stdout JSON additionalContext → 注入 AI 上下文 =====
    # systemMessage：Codex/Claude/ZCode UI 警告条；AI 看到告警后自行修复
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"codeguard: ⚠️ {alert}\n{detail}\n"
                f"建议: 修复上述问题后重新保存文件，codeguard 会自动复检。"
            )
        },
        "systemMessage": f"codeguard: ⚠️ {alert}",
    }, ensure_ascii=False))

    # macOS 系统通知（用户视觉提醒）
    mac_notify(alert, detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
