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
    ensure_user_path,
    find_project_root,
    load_user_config,
    project_uses_linter,
)

STATE_FILE = PLUGIN_ROOT / ".session_state.json"
# 双副本去重：同一插件可能以多个 marketplace 副本安装（partme-ai/ 与
# full-stack-plugins/ 各一份，钩子双份触发——实测），用户级固定路径跨副本共享
DEDUP_FILE = Path.home() / ".codeguard" / "hook_dedup.json"


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


def _notify_cooldown_ok(lang: str, cooldown_s: int = 60) -> bool:
    """同语言通知冷却：60s 内已弹过则抑制（additionalContext 注入不受影响）。"""
    import time
    state = {}
    try:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        pass
    entry = state.get(lang) or {}
    now = time.time()
    if now - entry.get("last_notify", 0) < cooldown_s:
        return False
    entry["last_notify"] = now
    state[lang] = entry
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))
    except OSError:
        pass
    return True

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


def should_suppress_duplicate(file_path: str) -> bool:
    """双副本去重：2 秒内同路径且文件未变化的重复触发静默跳过。

    两个 marketplace 副本各挂一份 PostToolUse 钩子时，同一 Write 事件
    会先后起两个钩子进程——第二份的输出对 AI/用户是纯重复。判定键为
    (路径, 文件 mtime_ns)：内容变了（mtime 变了）不吞，照常检查。
    """
    import time as _time
    try:
        mtime = Path(file_path).stat().st_mtime_ns
    except OSError:
        return False
    now = _time.monotonic()
    dedup = {}
    try:
        DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DEDUP_FILE.exists():
            dedup = json.loads(DEDUP_FILE.read_text())
        last = dedup.get(file_path) or {}
        if last.get("mtime_ns") == mtime and now - last.get("ts", 0) < 2.0:
            dedup[file_path] = {"mtime_ns": mtime, "ts": now}
            DEDUP_FILE.write_text(json.dumps(dedup))
            return True
        dedup[file_path] = {"mtime_ns": mtime, "ts": now}
        # 清理陈旧条目（防无限增长）
        stale = [k for k, v in dedup.items() if now - v.get("ts", 0) > 60]
        for k in stale:
            dedup.pop(k, None)
        DEDUP_FILE.write_text(json.dumps(dedup))
    except OSError:
        return False
    return False


def is_ejs_template(file_path: str) -> bool:
    """vue-cli 的 public/index.html 是 EJS 模板（<%= %>/<% if %>）。htmlhint
    对 EJS 标记必然误报（spec-char-escape / attr-value-double-quotes），
    且 CLI 不支持按规则覆盖（--rule=false 报 unknown option，实测）——
    这类文件直接跳过：EJS 语法错误由 vue-cli 构建流程兜底。"""
    try:
        return "<%" in Path(file_path).read_text(errors="ignore")[:8192]
    except OSError:
        return False


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
    ensure_user_path()   # 高频钩子：仅补静态目录（零开销），linter 找得到才跑得起来
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

    # 双副本去重：另一 marketplace 副本的钩子刚查过同一份文件则静默
    if should_suppress_duplicate(file_path):
        return 0

    # 文档类语言不拦 AI 写作流（AI 产出的报告/文档常不合 lint 严格规则，
    # 拦截会造成死循环）；提交门禁阶段仍有宽松校验
    if lang == "markdown":
        return 0

    cmd_def = LANG_COMMANDS.get(lang)
    if not cmd_def:
        return 0

    # 项目未接入该 linter（无配置文件）时，生态型 linter（eslint）必然报错
    # 退出——那是「未接入」不是「代码违规」（qumall-mall-ui 无 .eslintrc 实测）
    if not project_uses_linter(cmd_def, project_root):
        return 0

    # EJS 模板（vue-cli public/index.html）直接跳过 htmlhint：CLI 不支持
    # 按规则豁免（实测 unknown option），而误报是必然的
    if lang == "html" and is_ejs_template(file_path):
        return 0
    lint_cmd = cmd_def.get("lint") or []
    if not lint_cmd:
        return 0

    timeout = cfg.get("lint_timeout_seconds", 120)

    def materialize(cmd: list[str]) -> list[str]:
        """{file} 占位符替换：文件型 linter（shellcheck/hadolint/clang-tidy…）必须传具体文件"""
        return [c.replace("{file}", str(file_path)) for c in cmd]

    rc, stdout, stderr = run(materialize(lint_cmd), cwd=project_root, timeout=timeout)

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
            frc, _, _ = run(materialize(fmt_cmd), cwd=project_root, timeout=timeout + 60)
            if frc == 0:
                auto_fixed = True
                print("[codeguard] ✅ auto-fix succeeded, re-running lint...")
                rc, stdout, stderr = run(materialize(lint_cmd), cwd=project_root, timeout=timeout)

    passed = rc == 0
    bump_state(lang, passed=passed, auto_fixed=auto_fixed)

    if passed:
        # 已自动修复：告知 AI 文件被工具改过，避免 AI 继续用旧内容
        note = f"（已自动运行 {' '.join(cmd_def.get('format') or [])} 修复，请重新读取文件）" if auto_fixed else ""
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"codeguard: ✅ {lang} lint passed for {Path(file_path).name}{note}"
            },
            "systemMessage": f"codeguard: ✅ {lang} lint passed",
        }, ensure_ascii=False))
        return 0

    # ===== 结构化告警：AI 直接看到「什么问题 + 怎么修」 =====
    # linter 输出头部是最具体的问题（shellcheck/ruff/eslint 均如此），取头部而非尾部
    raw = (stdout or stderr or "").strip()
    problem_lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    problems = "\n".join(problem_lines[:5])[:500] or "（linter 未输出具体问题）"
    fix_cmd = " ".join(cmd_def.get("format") or []) or "按上述问题逐条修复"
    context = (
        f"codeguard ⚠️ [{lang}] {Path(file_path).name} 检查未通过\n"
        f"发现的问题（节选）:\n{problems}\n"
        f"怎么修:\n"
        f"  1. 可先运行 `{fix_cmd}` 自动修复格式类问题\n"
        f"  2. 手动修复上述具体问题后，重新保存该文件，codeguard 会自动复检"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context
        },
        "systemMessage": f"codeguard: ⚠️ {lang} lint FAILED: {Path(file_path).name}",
    }, ensure_ascii=False))

    # macOS 系统通知（用户视觉提醒；同语言 60s 冷却——批量编辑时不轰炸）
    alert = f"{lang} lint FAILED: {Path(file_path).name}"
    if _notify_cooldown_ok(lang):
        mac_notify(alert, problem_lines[0][:120] if problem_lines else "")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
