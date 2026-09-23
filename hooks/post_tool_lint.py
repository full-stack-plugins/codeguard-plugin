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

from codeguard import hook_state
from codeguard.execution import execute
from codeguard.fingerprint import check_identity
from codeguard.hook_state import codeguard_home
from codeguard.planning import scoped_plan
from detect_lang import (  # ensure_user_path/load_user_config 实际定义：scripts/paths.py、scripts/user_config.py
    LANG_COMMANDS,
    detect_language,
    ensure_user_path,
    find_project_root,
    load_user_config,
    project_uses_linter,
)
from scope import is_build_artifact

# 双副本去重：同一插件可能以多个 marketplace 副本安装（partme-ai/ 与
# full-stack-plugins/ 各一份，钩子双份触发——实测），用户级固定路径跨副本共享
# 路径按调用时的 CODEGUARD_HOME 解析；保留覆盖点供嵌入调用者隔离存储。
DEDUP_FILE: Path | None = None


def _dedup_path() -> Path:
    return DEDUP_FILE or codeguard_home() / "file_dedup.json"


def _state_path() -> Path:
    """旧无 ID 状态可回退；带会话 ID 的新统计绝不认领无归属旧数据。"""
    return hook_state.state_path(PLUGIN_ROOT / ".session_state.json")


def bump_state(lang: str, passed: bool, auto_fixed: bool = False) -> None:
    hook_state.bump_state(_state_path(), lang, passed, auto_fixed)


def _notify_cooldown_ok(lang: str, cooldown_s: int = 60) -> bool:
    return hook_state.notification_allowed(_state_path(), lang, cooldown_s)

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


def should_suppress_duplicate(file_path: str, identity: str | None = None) -> bool:
    return hook_state.completed_file_check(file_path, _dedup_path(), identity)


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
    """保存钩子的兼容执行入口，不拥有独立的故障判定。"""
    return execute(cmd, cwd, timeout).as_tuple()


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
    # 构建产物静默跳过：写到 target/site、target/apidocs 的生成 HTML/sh 由
    # 构建流程负责，检查它们只会给出下次构建就被重写的假告警，AI 还可能
    # "自动修复"生成物（prettier 改完、构建一跑又变回去）。
    # 目录认知单源：scope.FULL_SCAN_EXCLUDES。
    if is_build_artifact(file_path):
        return True, ""
    lang = detect_language(file_path)
    if not lang:
        return True, ""
    if languages and lang not in languages:
        return True, lang
    return False, lang


def main() -> int:
    from codeguard.hook_state import session_scope
    payload = read_payload()
    with session_scope(payload):
        return _main(payload)


def _main(payload: dict) -> int:
    ensure_user_path()   # 高频钩子：仅补静态目录（零开销），linter 找得到才跑得起来
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

    if not cmd_def.get("append_files", True):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"codeguard: {lang} 是项目级检查；本次保存未验证，"
            "请使用 codeguard check 或提交门禁。不会自动格式化整个项目。",
        }}, ensure_ascii=False))
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

    # 保存范围显式为 save；先冻结检查命令，修复后原样复检。
    lint_plan = scoped_plan(lint_cmd, project_root, scope="save", files=[str(file_path)])
    lint_argv = list(lint_plan.commands[0].argv)
    def identity():
        return check_identity(project_root, cfg, {lang: cmd_def}, extra_files=[file_path])
    checked_identity = identity()
    if checked_identity is not None and should_suppress_duplicate(file_path, checked_identity):
        return 0
    rc, stdout, stderr = run(lint_argv, cwd=lint_plan.cwd, timeout=timeout)

    from verdict import UNVERIFIED, lint_verdict
    verdict, reason = lint_verdict(rc, lint_cmd, stdout + stderr)
    if verdict == UNVERIFIED:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"codeguard: UNVERIFIED [{lang}] {reason} (exit {rc})；"
            "没有代码结论，不自动修复。",
        }}, ensure_ascii=False))
        return 0

    if rc == 0:
        if checked_identity is not None and checked_identity == identity():
            hook_state.record_file_check(file_path, _dedup_path(), checked_identity)
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
    touched_others: list[str] = []
    if cfg.get("auto_fix_on_save", True):
        fmt_cmd = cmd_def.get("format")
        if fmt_cmd:

            def _porcelain() -> set[str]:
                try:
                    import subprocess as _sp
                    proc = _sp.run(
                        ["git", "status", "--porcelain"],
                        cwd=project_root, capture_output=True, check=False,
                        text=True, timeout=10,
                    )
                    return {
                        ln[3:].strip() for ln in proc.stdout.splitlines()
                        if len(ln) > 3
                    } if proc.returncode == 0 else set()
                except Exception:  # noqa: BLE001 — 快照失败仅失去清单注入，不影响修复
                    return set()

            before = _porcelain()
            fix_plan = scoped_plan(fmt_cmd, project_root, scope="save", files=[str(file_path)])
            frc, _, _ = run(list(fix_plan.commands[0].argv), cwd=fix_plan.cwd, timeout=timeout + 60)
            if frc == 0:
                auto_fixed = True
                after = _porcelain()
                touched_others = sorted(
                    name for name in (after - before)
                    if not name.rstrip("/").endswith(Path(file_path).name)
                )
                checked_identity = identity()
                rc, stdout, stderr = run(lint_argv, cwd=lint_plan.cwd, timeout=timeout)

    verdict, reason = lint_verdict(rc, lint_cmd, stdout + stderr)
    if verdict == UNVERIFIED:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"codeguard: UNVERIFIED [{lang}] 修复后复检未完成：{reason}；"
            "formatter 可能已修改文件，请重新读取。没有通过/失败结论。",
        }}, ensure_ascii=False))
        return 0
    passed = rc == 0
    if checked_identity is not None and checked_identity == identity():
        hook_state.record_file_check(file_path, _dedup_path(), checked_identity)
    bump_state(lang, passed=passed, auto_fixed=auto_fixed)

    if passed:
        # 已自动修复：告知 AI 文件被工具改过，避免 AI 继续用旧内容
        note = ""
        if auto_fixed:
            note = f"（已自动运行 {' '.join(cmd_def.get('format') or [])} 修复）"
            if touched_others:
                shown = ", ".join(touched_others[:10])
                more = f" 等 {len(touched_others)} 个" if len(touched_others) > 10 else ""
                note += (
                    f"。⚠️ format 命令还改动了本文件之外的文件{more}：{shown}"
                    "——这些文件你内存里的版本已过期，必须先重新读取再继续操作"
                )
            else:
                note += "（仅本文件被改动，请重新读取）"
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
    if len(problem_lines) > 5 or len(raw) > 500:
        # 节选会让 AI 一次修 3 个、重试再看 3 个（whack-a-mole）：给总量+完整日志
        try:
            import hashlib as _h
            import tempfile as _tf
            key = _h.sha1(str(file_path).encode()).hexdigest()[:12]
            full_path = Path(_tf.gettempdir()) / f"codeguard-post-{lang}-{key}.log"
            full_path.write_text(raw, encoding="utf-8")
            problems += f"\n…（截断，共 {len(problem_lines)} 行；完整输出: {full_path}）"
        except OSError:
            problems += f"\n…（截断，共 {len(problem_lines)} 行）"
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
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
