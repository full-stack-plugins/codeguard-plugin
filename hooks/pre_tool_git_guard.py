#!/usr/bin/env python3
"""PreToolUse 钩子：AI 执行 git commit / git push 前硬门禁。

这是「修完才能推」的硬保证：AI 即使忽略 UserPromptSubmit 的软引导指令，
真正执行 git 命令时也会在这里被拦下。exit 2 + stderr 的反馈会作为工具
结果回给 AI（Claude/ZCode 协议），AI 看到后继续修复并重试——循环闭环：
失败 → AI 修 → 再 commit → 通过 → 放行。

通过时完全静默（exit 0，零输出）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))

from detect_lang import (  # # ensure_user_path/load_user_config 实际定义：scripts/paths.py、scripts/user_config.py
    ensure_user_path,
    load_user_config,
)
from gate_lib import (
    check_commit_safety,
    format_safety_report,
    gate_directive,
    record_skip_event,
    run_gate,
    should_suppress_event,
    skip_gate_via_git_config,  # 规范实现已上移 gate_lib（UPS 也要用）
)

# 拦截的 git 子命令（避免误拦 git status/diff/log 等只读命令）
GUARDED_PATTERNS = ("git commit", "git push")


def read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return {}


def extract_command(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    cmd = tool_input.get("command")
    return str(cmd) if cmd else ""


def _is_git_repo(p: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--git-dir"],
            capture_output=True, check=False, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0


def _flatten_substitutions(command: str) -> str:
    """把 `$(...)` 与反引号的内层文本并入待扫面（按 shell 语义它们会真的执行）。

    漏检实例（实测静默放行）：`ro=$(git push origin b 2>&1)`、`` x=`git commit` ``
    ——段首是赋值词/反引号而非 git，切段扫描永远看不到子命令。内层可能还有
    内层（`$(echo $(git push))`），工作队列递归展开，深度上限防畸形输入死循环。
    能力边界：单引号内的字面量（`'$(git push)'` 不执行）不做引号语义区分，
    宁可多拦不漏拦——误拦方向由 lint 门禁自身的 delta 面兜底（不改文件不红）。
    """
    parts: list[str] = []
    queue: list[str] = [command]
    seen = 0
    while queue and seen < 50:
        text = queue.pop(0)
        seen += 1
        parts.append(text)
        i = 0
        while True:
            j = text.find("$(", i)
            if j < 0:
                break
            depth, k = 1, j + 2
            while k < len(text) and depth:
                if text[k] == "(":
                    depth += 1
                elif text[k] == ")":
                    depth -= 1
                k += 1
            i = j + 2
            if depth == 0:
                inner = text[j + 2:k - 1]
                if inner and inner not in parts:
                    queue.append(inner)
        if "`" in text:
            seg = text.split("`")
            for inner in seg[1::2]:
                if inner and inner not in parts:
                    queue.append(inner)
    return "\n".join(parts)


def resolve_project_roots(command: str) -> list[Path]:
    """顺序扫描命令链，收集每个 git commit/push 段各自的仓库边界。

    链式发布（cd plugins && git commit && cd minimax && git push）操作
    多个仓库——每个 git 段的边界 = `git -C <path>` 显式指定的仓，否则取它
    之前最近的 cd（且必须是 git 仓）；无 cd 则用 cwd（需是 git 仓）。
    去重保序，找不到任何边界返回 []。

    **必须与 is_guarded 同源判定**（`_git_side_effect_sub` 归一化后判子命令）：
    此前这里用原始 tokens[0]=="git"，`git -C /repo push`、`FOO=1 git push`、
    `sudo git push` 虽被 is_guarded 命中却解析出 roots=[]，main() 见空直接
    放行——归一化修复在 roots 层被击穿（实测三形态全部静默通过）。
    """
    import re
    command = _flatten_substitutions(command)
    roots: list[Path] = []
    last_cd: Path | None = None
    for seg in re.split(r"&&|\|\||;|\n", command):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"cd\s+(\"[^\"]+\"|'[^']+'|\S+)", seg)
        if m:
            target = Path(m.group(1).strip("\"'"))
            # cd 到非 git 目录（如 workspace 根）后边界失效——回退 cwd（与 shell 语义一致）
            last_cd = target if target.is_dir() and _is_git_repo(target) else None
            continue
        if _git_side_effect_sub(seg) is None:
            continue
        c_path = _git_c_path(seg)
        if c_path is not None:
            root = c_path if c_path.is_dir() and _is_git_repo(c_path) else None
        else:
            root = last_cd or (Path(os.getcwd()) if _is_git_repo(Path(os.getcwd())) else None)
        if root and root not in roots:
            roots.append(root)
    # 有意行为（勿"修掉"）：cd 到非 git 目录后 last_cd=None，git 段回退用
    # 调用方 cwd——与 shell 语义一致（进非仓后 git 在原 cwd 执行）。
    return roots


_ASSIGN_RE = None  # 延迟编译，保持模块零顶层 re 依赖
_ASSIGN_PATTERN = r"^[A-Za-z_][A-Za-z0-9_.-]*="
_BARE_WRAPPERS = ("env", "sudo", "nohup", "command", "time", "nice", "ionice", "setsid", "stdbuf")
# shell 控制结构引导词：`if git push; then` / `for x; do git push; done` 段首是
# 控制词而非 git（`;` 切段后 `do git push…` 同理）——不剥就漏拦（实测四种形态
# 全部静默通过）。只在段首序列出现时剥，不影响普通命令中的同名词。
_SHELL_LEADERS = ("if", "then", "else", "elif", "while", "until", "do", "!")
_GIT_VALUE_FLAGS = ("-C", "-c", "--git-dir", "--work-tree", "--exec-path",
                    "--namespace", "--config-env", "--attr-source")
_GIT_BOOL_FLAGS = ("--no-pager", "--bare", "--literal-pathspecs",
                   "--no-optional-locks", "--shallow-file", "--exec-path")


def _analyze_segment(seg: str) -> tuple[list[str], str | None]:
    """归一化一段 shell 命令：返回 ([prog, sub, …] 形状的 tokens, `git -C` 的仓路径)。

    剥除顺序（与 shell 求值同序）：控制结构引导词 → 环境赋值/env/裸 wrapper 前缀
    → git 全局选项。同时捕获 `-C <path>`——它是该 git 段的显式仓库边界。
    漏检实例（实测静默放行）：`VAR=1 git push` 段首是 `VAR=1`；`git -C path push`
    tokens[1] 是 `sudo`；`if git push; then` 段首是 `if`。剥完后若段首仍非 git
    则返回原 tokens（由调用方判定为非 git 段）。
    能力边界（docstring 如实声明）：带值的 wrapper 参数（`sudo -u root …`）
    不做完整解析，只剥裸 wrapper token。
    """
    import re as _re
    tokens = seg.strip().split()
    i, n = 0, len(tokens)
    while i < n and tokens[i] in _SHELL_LEADERS:
        i += 1
    while True:
        while i < n and _re.match(_ASSIGN_PATTERN, tokens[i]):
            i += 1
        if i < n and tokens[i] == "env":
            i += 1
            continue
        break
    while i < n and tokens[i] in _BARE_WRAPPERS:
        i += 1
    if i >= n:
        return tokens, None
    if tokens[i].strip("\"'") != "git":
        return tokens[i:], None
    i += 1
    c_path: str | None = None
    while i < n:
        tok = tokens[i].strip("\"'")
        if tok in _GIT_BOOL_FLAGS:
            i += 1
            continue
        if tok in _GIT_VALUE_FLAGS:
            if tok == "-C" and i + 1 < n:
                c_path = tokens[i + 1].strip("\"'")
            i += 2
            continue
        if tok.startswith(("-C", "-c", "--git-dir", "--work-tree", "--exec-path")) and len(tok) > 2:
            if tok.startswith("-C") and len(tok) > 2:
                c_path = tok[2:].strip("\"'")
            i += 1
            continue
        break
    # 保留 "git" 作为首 token（调用方按 [prog, sub, …] 形状判定），只剥掉前面的
    # 前缀与后面的全局选项；`git` 裸段（无子命令）返回 ["git"] → len<2 → None。
    root = Path(c_path).resolve() if c_path else None
    return ["git"] + tokens[i:], (root if root else None)


def _normalize_segment(seg: str) -> list[str]:
    """归一化形状（丢弃 -C 捕获）——保持既有调用面。见 _analyze_segment。"""
    tokens, _c = _analyze_segment(seg)
    return tokens


def _git_c_path(seg: str) -> Path | None:
    """该段 `git -C <path>` 显式指定的仓库（相对路径按字面保留，由调用方判定）。"""
    _tokens, c = _analyze_segment(seg)
    return c


def _git_side_effect_sub(seg: str) -> str | None:
    """归一化后，段的子命令为 commit|push 则返回之，否则 None。

    首 token 剥一层包裹引号（`bash -c "git commit …"` 切段后首词是 `"git`）；
    前缀与 git 全局选项见 `_normalize_segment`。
    """
    tokens = _normalize_segment(seg)
    if len(tokens) < 2:
        return None
    first = tokens[0].strip("\"'")
    second = tokens[1].strip("\"'")
    return second if first == "git" and second in ("commit", "push") else None


def _segment_is_git_side_effect(seg: str) -> bool:
    return _git_side_effect_sub(seg) is not None


_SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".mjs", ".js", ".ts")
_INTERPRETERS = ("bash", "sh", "zsh", "python", "python3", "node")


def _command_indirect(command: str) -> bool:
    """间接提交识别：解释器跑的脚本文件 / -c 内联代码里含 git commit|push。

    硬门禁此前只看外层命令文本——`bash runner.sh`（脚本体内 git commit）
    完全绕过拦截，实测用 /tmp runner 连推 4 次全部漏网。这里对一层间接
    做静态扫描：脚本文本按同款分隔符切段后，任一段段首为 git+commit|push
    即命中。更深的 subprocess 拼接不在静态扫描能力内，不夸大承诺。
    """
    import re
    for seg in re.split(r"&&|\|\||;|\n", command):
        tokens = seg.strip().split()
        if not tokens:
            continue
        prog = tokens[0].rsplit("/", 1)[-1]
        if prog not in _INTERPRETERS:
            continue
        rest = tokens[1:]
        if "-c" in rest:
            body = " ".join(rest[rest.index("-c") + 1:])
            if any(_segment_is_git_side_effect(s)
                   for s in re.split(r"&&|\|\||;|\n", body)):
                return True
            continue
        for tok in rest:
            if tok.startswith("-"):
                continue
            target = Path(tok)
            if not target.is_file() or target.suffix not in _SCRIPT_SUFFIXES:
                break
            try:
                if target.stat().st_size > 1_000_000:
                    break
                body = target.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                break
            if any(_segment_is_git_side_effect(s)
                   for s in re.split(r"&&|\|\||;|\n", body)):
                return True
            break
    return False


def _collect_subs(text: str) -> list[str]:
    import re
    text = _flatten_substitutions(text)
    return [
        sub for seg in re.split(r"&&|\|\||;|\n", text)
        if (sub := _git_side_effect_sub(seg))
    ]


def _repo_root_of(p: Path) -> Path | None:
    """从路径向上找 .git 所在的仓库根（纯文件系统，不起进程）。"""
    cur = p if p.is_dir() else p.parent
    for _ in range(10):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def staging_intent(command: str) -> tuple[tuple[str, ...], list[str]]:
    """从命令链推断本次**真正会提交**的文件面（lanes）与 git add 显式路径。

    PostToolUse 语义：PreToolUse 在整条命令执行**之前**触发，链中的 `git add`
    还没跑——必须按命令形态预测执行后的暂存区，同时**不把与本次提交无关的
    工作树 WIP 算进来**（并行会话留在工作树的未暂存改动曾让纯 `git commit`
    被无关文件误拦）：
    - 链中无 git add、commit 无 -a → 只有暂存区会入库 → ("staged",)；
    - `git add -A/-a/-u/--all` 或无路径参数 → 未暂存/未跟踪将一并入库 → 三路；
    - `git add <paths>` → 暂存区 + 这些路径（add 尚未执行，路径可能还没staged）；
    - `git commit -a/-am/--all` → 暂存 + 已跟踪未暂存（git 不收未跟踪）→ 两路。
    能力边界：路径含 glob/`:` 等价语法按字面子处理；相对路径找不到存在性
    对应的仓根文件时由调用方丢弃（宁可少拦不误拦）。
    """
    import re
    all_lanes = ("staged", "unstaged", "untracked")
    lanes: set[str] = {"staged"}
    extra: list[str] = []
    add_paths: list[str] = []
    add_all = False
    add_tracked_only = False
    last_cd: Path | None = None
    text = _flatten_substitutions(command)
    for seg in re.split(r"&&|\|\||;|\n", text):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"cd\s+(\"[^\"]+\"|'[^']+'|\S+)", seg)
        if m:
            target = Path(m.group(1).strip("\"'"))
            last_cd = target if target.is_dir() else None
            continue
        tokens = _normalize_segment(seg)
        if len(tokens) < 2 or tokens[0] != "git":
            continue
        sub, rest = tokens[1], tokens[2:]
        if sub == "add":
            flags = [t for t in rest if t.startswith("-")]
            paths = [t for t in rest if not t.startswith("-")]
            if not rest or any(f in ("-A", "-a", "-u", "--all", "--ignore-removal") for f in flags) \
                    or any(p.strip("\"'") in (".", "./", "*", ":/") for p in paths):
                add_all = True
            elif paths:
                add_paths.extend(p.strip("\"'") for p in paths)
            else:
                add_all = True  # 无法预测形态时按宽口径（宁可多拦）
            if any(f in ("-u", "--update") for f in flags):
                add_tracked_only = True
        elif sub == "commit" and any(t in ("-a", "-am", "--all") for t in rest):
            lanes.update(("staged", "unstaged"))
    if add_all:
        lanes.update(all_lanes)
    elif add_tracked_only:
        lanes.update(("staged", "unstaged"))
    for p in add_paths:
        if Path(p).is_absolute():
            continue
        cand_root = last_cd if last_cd is not None else Path(".")
        # git add 的 pathspec 相对 shell 语境（last_cd 或 cwd）解析成绝对路径，
        # 再换算成**仓库根**相对路径——changed_files 的 paths 全部相对仓根；
        # cd 到仓库子目录（scripts/…）时相对 last_cd 会算错一截。
        try:
            resolved = (cand_root / p).resolve()
        except OSError:
            continue
        repo = _repo_root_of(resolved) or _repo_root_of(Path.cwd())
        if repo is None:
            continue
        try:
            rel = resolved.relative_to(repo)
        except ValueError:
            continue
        extra.append(str(rel))
    ordered = tuple(l for l in all_lanes if l in lanes)
    return ordered, extra


def _guarded_mode(command: str) -> str | None:
    """门禁命中时返回生效的门禁面：commit 或 push（push 优先——两面并存时
    推送面是提交面的超集，按更宽的面检查）；未命中返回 None。

    直接命令段先判定；未命中再走一层解释器间接（脚本/-c 内联）。
    is_guarded 即本函数的存在性判断——面判定与命中判定共用同一套扫描，
    避免"命中了却选错面"的分叉。
    """
    subs = _collect_subs(command)
    if not subs:
        import re
        for seg in re.split(r"&&|\|\||;|\n", command):
            tokens = seg.strip().split()
            if not tokens:
                continue
            prog = tokens[0].rsplit("/", 1)[-1]
            if prog not in _INTERPRETERS:
                continue
            rest = tokens[1:]
            if "-c" in rest:
                body = " ".join(rest[rest.index("-c") + 1:])
                subs = _collect_subs(body)
                if subs:
                    break
                continue
            for tok in rest:
                if tok.startswith("-"):
                    continue
                target = Path(tok)
                if not target.is_file() or target.suffix not in _SCRIPT_SUFFIXES:
                    break
                try:
                    if target.stat().st_size > 1_000_000:
                        break
                    body = target.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    break
                subs = _collect_subs(body)
                break
            if subs:
                break
    if not subs:
        return None
    return "push" if "push" in subs else "commit"


def is_guarded(command: str) -> bool:
    """精确匹配 git commit/push：直接命令 + 一层解释器间接。

    直接：子串匹配会误伤命令文本里的数据（payload、调试脚本内容含
    "git push" 字面量），所以按分隔符切段、git 必须是段首命令词。
    间接：解释器执行的脚本/内联代码按同规则扫一层。
    命中后面（commit/push）由 _guarded_mode 决定，供门禁选 delta 面。
    """
    return _guarded_mode(command) is not None


def main() -> int:
    ensure_user_path()
    payload = read_payload()
    command = extract_command(payload)
    if not command or not is_guarded(command):
        return 0

    # 双副本去重：宿主带事件 id（生产 payload 的 tool_use_id）时第二副本静默；
    # 测试 payload 不带 id → 不去重，保持旧行为。
    event_id = payload.get("tool_use_id")
    if event_id and should_suppress_event(f"pre:{event_id}"):
        return 0

    if os.environ.get("CODEGUARD_SKIP_GATE"):
        record_skip_event("env")
        return 0

    cfg = load_user_config()
    mode = _guarded_mode(command) or "commit"
    roots = resolve_project_roots(command)
    if not roots:
        return 0
    if any(skip_gate_via_git_config(r) for r in roots):
        record_skip_event("skipGate", roots[0])
        return 0

    # 按命令链预测实际提交面（纯 commit → 仅 staged；add -A/-a → 三路），
    # 并入 git add 显式路径（add 尚未执行、暂存区还是旧的）。
    lanes, extra = staging_intent(command)

    # 每个被操作的仓库独立跑：linter 门禁 + 提交内容安全检查
    # （commit 查暂存区；push 查未推送提交的 diff，防已提交未发现的坏文件）
    reports = []
    for project_root in roots:
        # extra 路径按各仓存在性过滤：多仓链里 add 的路径只属于其中一个仓，
        # 幻影路径喂给 {file} 型 linter 会得到"文件不存在"的假失败。
        root_extra = [p for p in extra if (project_root / p).exists()]
        failures, _skipped = run_gate(
            project_root, cfg, mode=mode, lanes=lanes, extra=root_extra,
        )
        if failures:
            reports.append(gate_directive(failures))
        violations = check_commit_safety(project_root, mode)
        if violations:
            reports.append(format_safety_report(violations) + (
                "\n\n**给 AI 的强制指令**：**密钥/凭据类**（.env、*.pem、id_* 等）"
                "立即 git rm --cached 并提醒用户轮换密钥，不能只删了事；"
                "**非密钥类**（依赖/产物目录、仓根 db/log 等）**先与用户确认**"
                "是否为有意入库的第一方代码或合法 fixture——确认属误入库才执行"
                "git rm --cached + .gitignore，确认后重新执行本次 git 命令。"
            ))

    if not reports:
        return 0
    # 硬拦截：stderr 作为工具结果反馈给 AI，AI 修复后重试本命令
    print(("\n\n" + "=" * 20 + " 下一个仓库 " + "=" * 20 + "\n\n").join(reports), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 内部错误 fail-open：traceback 绝不进 AI 上下文/阻断工作流
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
