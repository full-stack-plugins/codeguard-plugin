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
from scope import changed_files

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


def _fallback_roots(cwd: Path) -> list[Path]:
    """cwd 不是 git 仓时，扫 cwd 一层子目录找 git 仓作兜底（monorepo 模式）。

    返回去重后保序的 git 仓列表（不含 cwd 自身）。

    实现注：`_is_git_repo(p)` 调 `git -C p rev-parse --git-dir` —— git 在
    p 不是仓时会沿父目录递归找 .git 并返回成功；这会让 cwd 是任何子目录时
    全部子目录被错判为 git 仓。fallback 必须用更严格的"仓内 .git 存在"判定：
    `(child / ".git").exists()`。`_is_git_repo` 在主流程只在 cwd 自身或显式
    cd 后的目标目录上调用，子目录递归副作用在主流程可控；这里只暴露 cwd
    自身的判定语义，故 fallback 走自己独立的"子目录级 .git 存在"检查。
    """
    if not cwd.is_dir():
        return []
    cwd_resolved = cwd.resolve()
    found: list[Path] = []
    for child in sorted(cwd.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        child_resolved = child.resolve()
        if child_resolved == cwd_resolved:
            continue
        # 严格子目录级检查：仓根的 .git 必须真在该子目录里
        if (child / ".git").exists():
            found.append(child_resolved)
    return found


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


# 全小写比较集：git config 键名大小写不敏感（codeguard.skipGate ≡ codeguard.skipgate）
_SKIP_GATE_ASSIGN = ("codeguard.skipgate=true", "codeguard.skipgate=1", "codeguard.skipgate=yes")

# git 全局参数里带一个独立值的 flag（`git -C <path> config …` 的 <path> 是 flag
# 值不是子命令）；带 `=` 形式（--git-dir=/x）无独立值。
_GIT_GLOBAL_VALUE_FLAGS = frozenset(
    ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--exec-path"))

# git config 查询/删除形态——只读/清理动作，不构成豁免意图
_QUERY_CONFIG_FLAGS = ("--get", "--get-all", "--get-regexp", "--unset", "--unset-all",
                       "--list", "-l")


def _git_seg_parts(tokens: list[str]) -> tuple[str, int, list[str]] | None:
    """按 git 全局参数语法切分单个命令段：返回 (子命令, 子命令下标, 子命令前全局参数)。

    git 语法 = `git [全局 flag [值]]* <子命令> [参数…]`。**子命令之后的 token
    一律不是全局配置**——`git commit -m "… -c codeguard.skipGate=true …"` 的
    消息文本、`git commit -m "config codeguard.skipGate true"` 都不构成豁免
    意图（防的是危险方向的误判：文本里出现豁免短语 → 门禁被静默关掉）。
    找不到子命令（纯 `git` / 全是 flag）返回 None。
    """
    if len(tokens) < 2 or tokens[0] != "git":
        return None
    i, pre = 1, []
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("-"):
            pre.append(tok)
            i += 1
            if (tok.split("=", 1)[0] in _GIT_GLOBAL_VALUE_FLAGS and "=" not in tok
                    and i < len(tokens)):
                pre.append(tokens[i])
                i += 1
            continue
        return tok, i, pre
    return None


def inline_skip_gate(command: str) -> bool:
    """`git -c codeguard.skipGate=true …`（全局参数位）= **显式单次豁免意图**。

    `git config` 豁免是仓库级、需手动 unset（忘记 unset = 门禁永久静默失效，
    stop_summary 已在提醒）；`-c` 内联是单次、随命令消亡、不留配置残留——
    更适合"这一条命令我知道有环境问题，放行"的场景。此前 `-c k=v` 被
    `_analyze_segment` 剥掉后 matcher 反而漏拦（守卫绕过口），本函数把该形态
    识别为**有审计的正门**：调用方放行时必须记 record_skip_event("inline-skipGate")。

    只认子命令之前的 `-c` 全局参数位（git 语法本义），消息文本/脚本参数里的
    同名字符串不构成豁免；value 精确匹配 _SKIP_GATE_ASSIGN。
    """
    text = _flatten_substitutions(command)
    import re as _re
    for seg in _re.split(r"&&|\|\||;|\n", text):
        tokens = [t.strip("\"'") for t in seg.strip().split()]
        parts = _git_seg_parts(tokens)
        if parts is None:
            continue
        _, _, pre = parts
        for i, tok in enumerate(pre):
            if tok == "-c" and i + 1 < len(pre) and pre[i + 1].lower() in _SKIP_GATE_ASSIGN:
                return True
    return False


def chain_skip_gate(command: str) -> bool:
    """命令链里含 `git config codeguard.skipGate <true|1|yes>` **设置**段 = 显式豁免意图。

    文档推荐的仓库级豁免是「set → 提交 → unset」，天然会被写进同一条链命令
    （`git config codeguard.skipGate true && git commit … && git config --unset …`）。
    此前链里只要有一个 git commit/push 段就整链被拦——set 段自己都没跑成，
    文档绕过首用必败。识别为显式豁免意图放行，并记 "chain-skipGate" 审计。

    只认子命令就是 `config` 的**设置**形态（--get/--unset/--list 查询不算），
    key 精确匹配 codeguard.skipGate（大小写不敏感）、value 须为真值；消息文本
    里出现的同名字符串不构成豁免（见 _git_seg_parts 的子命令边界）。
    """
    text = _flatten_substitutions(command)
    import re as _re
    for seg in _re.split(r"&&|\|\||;|\n", text):
        tokens = [t.strip("\"'") for t in seg.strip().split()]
        parts = _git_seg_parts(tokens)
        if parts is None:
            continue
        sub, si, _pre = parts
        if sub != "config":
            continue
        rest = tokens[si + 1:]
        if any(t in _QUERY_CONFIG_FLAGS for t in rest):
            continue
        args = [t for t in rest if not t.startswith("-")]
        if len(args) < 2:
            continue
        key, value = args[0], args[1]
        if key.lower() == "codeguard.skipgate" and value.lower() in ("true", "1", "yes"):
            return True
    return False


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
            if paths and not any(p.strip("\"'") in (".", "./", "*", ":/") for p in paths):
                add_paths.extend(p.strip("\"'") for p in paths)
            elif any(f in ("-u", "--update") for f in flags):
                add_tracked_only = True
            else:
                add_all = True
        elif sub == "commit" and any(t in ("-a", "-am", "--all") for t in rest):
            lanes.update(("staged", "unstaged"))
    if add_all:
        lanes.update(all_lanes)
    elif add_tracked_only:
        lanes.update(("staged", "unstaged"))
    for p in add_paths:
        if Path(p).is_absolute():
            continue
        cand_root = last_cd if last_cd is not None else Path.cwd()
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
    ordered = tuple(lane for lane in all_lanes if lane in lanes)
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


def _filter_fallback_roots(roots: list[Path], mode: str,
                           lanes: tuple[str, ...] | list[str] | None) -> list[Path]:
    """monorepo 兜底面收窄：只保留本次提交面非空的仓。

    会话实测：openclaw 提交时，兜底把 workspace 下所有子仓连同根上散落脚本
    一起纳入检测面——无关仓的存量违规也变成拦路面（误伤与提交完全无关的
    仓库）。无提交面的仓跳过；全部为空返回 []（调用方审计后放行）。

    lanes-only：兜底场景没有显式 cd，`git add <相对路径>` 的 extra 属于
    会话根而非任何子仓，不参与归属判定。
    """
    return [r for r in roots if changed_files(r, mode=mode, lanes=lanes)]


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
    # 静默跳过漏报修复：roots=[] 时扫描 cwd 一层子目录找 git 仓作兜底
    # （monorepo 模式：workspace 根目录下多仓时，从根目录直跑 git push 不
    # 经 cd 也能被覆盖）。找不到则向 #2 抛错，让 Agent 知晓绕过发生。
    fallback_note: str | None = None
    if not roots:
        fallback = _fallback_roots(Path(os.getcwd()))
        if fallback:
            roots = fallback
            fallback_note = (
                f"未检测到显式 cd 仓；兜底扫描 cwd 一层子目录找到 {len(fallback)} 个 git 仓"
            )
        else:
            # 输出明确错误而非静默 exit 0：避免 Agent/用户误以为门禁执行过。
            print(
                f"[codeguard] 未检测到任何 git 仓：cwd={os.getcwd()} 且命令链中无 cd <仓>。"
                f"请在 git push 前先 cd <仓路径>，或在仓库根设置 git config codeguard.skipGate true。"
                f"（已用兜底扫描 cwd 一层子目录，无 git 仓。）",
                file=sys.stderr,
            )
            return 2
    if fallback_note:
        # 兜底面收窄（会话实测误拦：无关仓存量违规连带拦提交）。全空 = 本次
        # 无可拦对象，审计后放行。
        before = len(roots)
        roots = _filter_fallback_roots(roots, mode, None)
        fallback_note += f"；提交面收窄 {before}→{len(roots)} 个仓"
        if not roots:
            record_skip_event("monorepo-fallback-empty", detail=fallback_note)
            return 0
        # 兜底走通：仅在会话状态记录（不进 stderr，避免噪音），Stop 摘要可见
        record_skip_event("monorepo-fallback", roots[0], detail=fallback_note)
    if any(skip_gate_via_git_config(r) for r in roots):
        record_skip_event("skipGate", roots[0])
        return 0
    # 单次内联豁免：`git -c codeguard.skipGate=true …` 是显式意图（不落配置、
    # 无残留），放行并留审计明细——比仓库级 config 更不易"忘记恢复"。
    if inline_skip_gate(command):
        record_skip_event("inline-skipGate", roots[0])
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext":
            "codeguard: 已通过内联豁免 `-c codeguard.skipGate` 放行本次提交"
            "（已审计记录，Stop 摘要可见）。"}}
        ))
        return 0
    # 链内设置豁免：`git config codeguard.skipGate true && … && git config --unset …`
    # 是文档推荐的自清理写法；此前整链被拦连 set 段都没跑成（首用必败）。
    if chain_skip_gate(command):
        record_skip_event("chain-skipGate", roots[0])
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext":
            "codeguard: 已通过链式豁免（set→提交→unset 同链）放行本次提交"
            "（已审计记录，Stop 摘要可见）。"}}
        ))
        return 0

    # 按命令链预测实际提交面（纯 commit → 仅 staged；add -A/-a → 三路），
    # 并入 git add 显式路径（add 尚未执行、暂存区还是旧的）。
    lanes, extra = staging_intent(command)
    pending_commit = "commit" in _collect_subs(command)

    # 每个被操作的仓库独立跑：linter 门禁 + 提交内容安全检查
    # （commit 查暂存区；push 查未推送提交的 diff，防已提交未发现的坏文件）
    reports = []
    for project_root in roots:
        # 保留删除路径用于影响分析；单文件 linter 自行过滤不存在的文件。
        root_extra = list(extra)
        failures, _skipped = run_gate(
            project_root, cfg, mode=mode, lanes=lanes, extra=root_extra,
            exact=True, pending_commit=pending_commit,
        )
        if failures:
            # 版本自标识由 gate_directive 首行综述之后的第二行承担——
            # 此处不再前置横幅：stderr 首行必须是综述（三个契约测试锁定）。
            reports.append(gate_directive(failures, project_root=project_root))
        unknown = [s for s in _skipped if "本次改动未涉及" not in s and " SKIPPED:" not in s
                   and "markdown 风格告警" not in s]
        if unknown:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "additionalContext":
                "codeguard: 存在未验证项，不能宣称全部通过：" + "；".join(unknown),
            }}, ensure_ascii=False))
        violations = check_commit_safety(project_root, mode, lanes=lanes, extra=root_extra,
                                         pending_commit=pending_commit)
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
