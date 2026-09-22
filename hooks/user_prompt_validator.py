#!/usr/bin/env python3
"""UserPromptSubmit 钩子：用户说"提交/push/部署"时先跑 linter 门禁。

失败时【不阻断 prompt】（exit 2 会把用户消息弹回去，AI 收不到任何指令，
用户被卡死在输入框）——而是 exit 0 + stdout JSON additionalContext：
AI 收到「门禁未通过 + 修复指令」后自动修复、修完自己重新提交，形成闭环。

硬保证由 PreToolUse 钩子（pre_tool_git_guard.py）承担：AI 真去执行
git commit/push 时被拦下，工具级 stderr 会作为结果反馈给 AI 继续修。
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根（不依赖宿主环境变量）
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

# 触发此钩子的关键词（中英）
# 英文按词边界匹配（防止 pushed/deployment 误命中），中文子串即可。
# 2026-09-22 实测回归：`我刚才 pushed 了`、`关于 deployment 策略的讨论`
# 必须静默（子串匹配曾把它们当提交意图跑全仓 lint）。
import re as _re

from detect_lang import (  # # ensure_user_path/load_user_config 实际定义：scripts/paths.py、scripts/user_config.py
    detect_languages,
    ensure_user_path,
    find_project_root,
    load_user_config,
)
from gate_lib import (
    check_commit_safety,
    format_safety_report,
    gate_directive,
    record_skip_event,
    run_gate,
    should_suppress_event,
    skip_gate_via_git_config,
    summarize_failures,
)

TRIGGER_PATTERNS = [
    "commit", "push", "deploy", "提交", "发布", "部署",
]
_TRIGGER_RE = _re.compile(
    r"\b(?:commit|push|deploy)\b|提交|发布|部署",
    _re.IGNORECASE,
)
# 行动意图短语：触发词出现且（句首祈使 或 命中行动短语）才进门禁。
_ACTION_INTENT_RE = _re.compile(
    r"请帮我|帮我|请|马上|立刻|现在|下一步|继续|please|now|next|proceed|go ahead|"
    r"commit this|push this|deploy this",
    _re.IGNORECASE,
)


def notify(title: str, message: str) -> None:
    """macOS 系统通知（非 darwin 静默；仅失败时打扰，通过靠注入文本确认）"""
    if sys.platform != "darwin":
        return
    import subprocess
    safe_t = title.replace('"', "'")
    safe_m = message.replace('"', "'")[:200]
    with contextlib.suppress(OSError):
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_m}" with title "{safe_t}" sound name "Pop"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


# 疑问句特征：在询问功能/做法，不是真的要提交（实测误触发：
# 「git 提交和推送，是不能把 .venv 排除掉么」被当成提交意图跑了全仓门禁）
QUESTION_MARKERS = ("？", "?", "么", "吗", "如何", "怎么", "有没有", "是不是", "什么是", "哪些")


def is_trigger(user_text: str) -> bool:
    """触发条件：(1) 命中触发词（英文按词边界）(2) 非疑问句 (3) 行动意图或句首祈使。

    (3) 缺一不可：`我刚才 pushed 了` 有触发词但无行动意图 → 静默；
    `commit this now` 句首祈使 → 触发；`请帮我 commit` 行动短语 → 触发。
    """
    if not user_text:
        return False
    if any(q in user_text for q in QUESTION_MARKERS):
        return False
    m = _TRIGGER_RE.search(user_text)
    if not m:
        return False
    # 句首祈使：触发词本身（或前面只有空白/常见介词）位于句首。
    stripped = user_text.lstrip()
    leading = stripped[: m.start()].strip().lower()
    if leading in ("", "git", "to", "the", "a", "an", "帮我", "请", "请帮我"):
        return True
    return bool(_ACTION_INTENT_RE.search(user_text))


def _detect_languages_in_text(user_text: str, language_ids: list[str]) -> list[str]:
    """从用户消息中提取提到的语言子集（2.1/2.2/2.3）。

    与 `languages.json` 的 `id` 字段做大小写无关匹配；没有命中返回空列表，
    由调用方回退到 `detect_languages()` 全量探测（保持原有能力）。
    """
    if not user_text or not language_ids:
        return []
    text = user_text.lower()
    hits = []
    for lang_id in language_ids:
        # 词边界避免 go 命中 gone/going、c 命中 cmake 等子串误命中。
        if _re.search(rf"\b{_re.escape(lang_id.lower())}\b", text):
            hits.append(lang_id)
    return hits


def read_payload() -> dict:
    """读一次 stdin payload（text 与 session_id 都从中取，stdin 只能读一次）。"""
    if sys.stdin.isatty():
        return {}
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_user_text() -> str:
    payload = read_payload()
    return str(payload.get("user_prompt") or payload.get("prompt") or "")


def _non_git_note() -> str:
    return (
        "codeguard：当前目录不是 git 仓库，提交门禁已跳过"
        "（门禁只对 git 仓生效；非 git 目录曾被回退成工作区根全仓扫描——"
        "一个临时目录即可把上百个无关仓的存量 lint 变成永久红）。"
    )


def main() -> int:
    payload = read_payload()
    user_text = str(payload.get("user_prompt") or payload.get("prompt") or "")
    if not is_trigger(user_text):
        return 0

    # 双副本去重：session_id + 文本 派生事件 key；测试 payload 无该字段→旧行为
    session_id = payload.get("session_id")
    if session_id and should_suppress_event(f"ups:{session_id}:{user_text[:200]}"):
        return 0

    ensure_user_path(from_login_shell=True)   # GUI 宿主 PATH 不含用户级工具目录
    # 逃生门：设置此环境变量后跳过提交门禁（用于确实需要绕过的场景）
    if os.environ.get("CODEGUARD_SKIP_GATE"):
        record_skip_event("env")
        return 0

    root = find_project_root(os.getcwd())
    if root is None or not (root / ".git").exists():
        # 非 git 目录绝不回退成"扫这个目录"——曾经的 find_project_root or cwd
        # 让工作区根成了全仓扫描对象（永久红且不可合法修复）。显式说明+跳过。
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": _non_git_note(),
            }
        }, ensure_ascii=False))
        return 0
    project_root = root
    if skip_gate_via_git_config(project_root):
        # 软门禁与硬门禁共用同一条仓库级豁免：此前 UPS 不认 skipGate，
        # 出现过"硬门放行、软门仍喊禁止提交"的自相矛盾。
        record_skip_event("skipGate", project_root)
        return 0

    cfg = load_user_config()
    # 2.2: 消息里提到了具体语言时只跑子集；没提到则回退全量探测（2.3）。
    detected = detect_languages(project_root)
    subset = _detect_languages_in_text(user_text, detected)
    # 推送意图走 push 面（含未推送提交），提交意图走 commit 面（暂存+工作区）——
    # 与硬门禁的 _guarded_mode 同一套语义，软硬两门看到同一组文件。
    mode = "push" if _re.search(r"\bpush\b|推送", user_text, _re.IGNORECASE) else "commit"
    failures, skipped = run_gate(project_root, cfg, languages=(subset or None), mode=mode)
    # 提交内容安全检查：.venv/node_modules/.env/密钥等不应入库
    violations = check_commit_safety(project_root, mode)

    if failures or violations:
        # 软引导：prompt 正常送达 AI，且注入修复指令，AI 自动修复后重新提交。
        # 注意：可能"只有安全违规、零 lint 失败"——此前 notify 直接取
        # failures[0][0] 越界，fail-open 吞成空输出（实测复现），两路都要兜。
        _first_issue = failures[0][1].splitlines()[0][:120] if failures and failures[0][1] else "详见对话"
        _headline = (
            f"{failures[0][0]}: {_first_issue}" if failures
            else (f"提交安全: {violations[0][0]}" if violations else "提交门禁发现违规")
        )
        notify(summarize_failures(failures), _headline)
        parts = [gate_directive(failures)]
        if violations:
            parts.append(format_safety_report(violations))
        parts.append(
            "**给 AI 的强制指令**：**密钥/凭据类**必须 git rm --cached 并提醒用户"
            "轮换密钥；**非密钥类**先与用户确认是否为有意入库的第一方代码或合法"
            " fixture，确认误入库再 git rm --cached + 补 .gitignore；确认并修复后"
            "重新执行提交。"
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n\n".join(parts)
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
                f"codeguard ✅ 提交门禁通过：已检查 {len(checked)} 个语言生态 + 暂存区安全"
                f"（{', '.join(checked) or '无'}），可以提交{skipped_note}。"
            )
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
