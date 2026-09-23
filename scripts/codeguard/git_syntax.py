"""Git 命令的静态语法识别；不读取仓库、执行进程或依赖 Hook 协议。"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

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


# 全小写比较集：git config 键名大小写不敏感（codeguard.skipGate ≡ codeguard.skipgate）
_SKIP_GATE_ASSIGN = ("codeguard.skipgate=true", "codeguard.skipgate=1", "codeguard.skipgate=yes")

# git 全局参数里带一个独立值的 flag（`git -C <path> config …` 的 <path> 是 flag
# 值不是子命令）；带 `=` 形式（--git-dir=/x）无独立值。
_GIT_GLOBAL_VALUE_FLAGS = frozenset(
    ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--exec-path"))

# git config 查询/删除形态——只读/清理动作，不构成豁免意图
_QUERY_CONFIG_FLAGS = ("--get", "--get-all", "--get-regexp", "--unset", "--unset-all",
                       "--list", "-l")


_HEREDOC_START = re.compile(
    r"(?<![<])<<(?!<)-?\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_]*))"
)
_SHELL_INTERPRETER_NAMES = ("bash", "sh", "zsh", "dash", "ksh")
_NON_SHELL_INTERPRETER_NAMES = ("python", "python3", "node")


def _heredoc_owner_program(command: str, start: int) -> str:
    """heredoc 重定向所在段的程序名（回溯到最近的控制符边界）。"""
    seg_start = 0
    for i in range(start - 1, -1, -1):
        if command[i] in (";", "\n"):
            seg_start = i + 1
            break
        if i >= 1 and command[i - 1:i + 1] in ("&&", "||"):
            seg_start = i + 1
            break
    head = command[seg_start:start]
    tokens = head.replace("&&", " ").split()
    return tokens[0].rsplit("/", 1)[-1].strip("\"'") if tokens else ""


def mask_heredoc_bodies(command: str) -> str:
    """heredoc 正文按语义遮蔽为保留换行的空白（fix-release-chain 遗留敞口）。

    三类语义（2026-09-23 实测区分，别混）：
    - 数据程序 + 引号定界符（`cat <<'EOF'`）：正文全字面量 → 全遮蔽——
      模板字符串/帮助文本/文档样例的 git 字面量曾被切段误伤成真实副作用；
    - 数据程序 + 无引号（`cat <<EOF`）：正文会做命令替换展开，
      `$(git push)`/反引号**会被外层真实执行**（既有实测静默放行向量）——
      遮蔽正文但保留替换跨度，交给 _flatten_substitutions 展开扫描；
    - 解释器定界：bash/sh 正文是内层 shell 代码（不遮蔽，保留切段建模）；
      python/node 正文不是 shell 语法（全遮蔽杀误报；其 subprocess 调用形态
      由 dynamic_git_effects 在脚本文件路径上归因，stdin 形态为已声明边界）。
    幂等：已遮蔽的正文不再含定界符结构。
    """
    out = list(command)
    for match in _HEREDOC_START.finditer(command):
        delim = match.group(1) or match.group(2) or match.group(3)
        owner = _heredoc_owner_program(command, match.start())
        if owner in _SHELL_INTERPRETER_NAMES:
            continue
        body_start = command.find("\n", match.end())
        if body_start < 0:
            continue
        end_match = re.compile(rf"(?m)^[ \t]*{re.escape(delim)}[ \t]*$").search(
            command, body_start + 1)
        body_end = end_match.start() if end_match else len(command)
        keep_subs = (match.group(1) is None and match.group(2) is None
                     and owner not in _NON_SHELL_INTERPRETER_NAMES)
        if keep_subs:
            # 无引号数据正文：保留 $(...) 与反引号跨度（其内层文本会被真实执行）
            i = body_start + 1
            while i < body_end:
                if command[i:i + 2] == "$(":
                    depth, j = 1, i + 2
                    while j < body_end and depth:
                        if command[j] == "(":
                            depth += 1
                        elif command[j] == ")":
                            depth -= 1
                        j += 1
                    i = j
                    continue
                if command[i] == "`":
                    j = command.find("`", i + 1, body_end)
                    i = (j + 1) if j >= 0 else body_end
                    continue
                if out[i] != "\n":
                    out[i] = " "
                i += 1
        else:
            for i in range(body_start + 1, body_end):
                if out[i] != "\n":
                    out[i] = " "
    return "".join(out)


def split_shell_segments(command: str) -> list[tuple[str, str | None]]:
    """只按未引用、未转义的 Shell 控制符切段，保留前置分隔符。

    这不是完整 Shell 解释器；嵌套替换由 `_flatten_substitutions` 另行展开。
    引号内的 `;`/`&&` 和 `\\;` 是参数数据，不能合成 git config 豁免。
    """
    command = mask_heredoc_bodies(command)
    segments: list[tuple[str, str | None]] = []
    start = 0
    before: str | None = None
    quote: str | None = None
    escaped = False
    i = 0
    while i < len(command):
        char = command[i]
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif quote is not None:
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char in (";", "\n") or command[i:i + 2] in ("&&", "||"):
            separator = command[i:i + 2] if command[i:i + 2] in ("&&", "||") else char
            segment = command[start:i].strip()
            if segment:
                segments.append((segment, before))
            before = separator
            i += len(separator)
            start = i
            continue
        i += 1
    segment = command[start:].strip()
    if segment:
        segments.append((segment, before))
    return segments



def _flatten_substitutions(command: str) -> str:
    """把 `$(...)` 与反引号的内层文本并入待扫面（按 shell 语义它们会真的执行）。

    漏检实例（实测静默放行）：`ro=$(git push origin b 2>&1)`、`` x=`git commit` ``
    ——段首是赋值词/反引号而非 git，切段扫描永远看不到子命令。内层可能还有
    内层（`$(echo $(git push))`），工作队列递归展开，深度上限防畸形输入死循环。
    能力边界：单引号内的字面量（`'$(git push)'` 不执行）不做引号语义区分，
    宁可多拦不漏拦——误拦方向由 lint 门禁自身的 delta 面兜底（不改文件不红）。
    """
    command = mask_heredoc_bodies(command)
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


def _strip_command_prefix(tokens: list[str]) -> list[str]:
    """为直接 Git 和一层解释器共用裸 wrapper/环境前缀语义。"""
    i = 0
    while i < len(tokens) and tokens[i] in _SHELL_LEADERS:
        i += 1
    while i < len(tokens):
        if re.match(_ASSIGN_PATTERN, tokens[i]) or tokens[i] in _BARE_WRAPPERS:
            i += 1
            continue
        break
    return tokens[i:] if i < len(tokens) else tokens


def _segment_tokens(segment: str) -> list[str]:
    """复用分词与裸前缀归一化；畸形引号维持旧接口的保守切词。"""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.strip().split()
    return _strip_command_prefix(tokens)


def _analyze_segment(seg: str) -> tuple[list[str], Path | None]:
    """归一化一段 shell 命令：返回 ([prog, sub, …] 形状的 tokens, `git -C` 的仓路径)。

    剥除顺序（与 shell 求值同序）：控制结构引导词 → 环境赋值/env/裸 wrapper 前缀
    → git 全局选项。同时捕获 `-C <path>`——它是该 git 段的显式仓库边界。
    漏检实例（实测静默放行）：`VAR=1 git push` 段首是 `VAR=1`；`git -C path push`
    tokens[1] 是 `sudo`；`if git push; then` 段首是 `if`。剥完后若段首仍非 git
    则返回剥除前缀后的 tokens，供解释器检测复用。
    能力边界（docstring 如实声明）：带值的 wrapper 参数（`sudo -u root …`）
    不做完整解析，只剥裸 wrapper token。
    """
    tokens = _segment_tokens(seg)
    if not tokens:
        return tokens, None
    if tokens[0].strip("\"'") != "git":
        return tokens, None
    i, n = 1, len(tokens)
    c_path: str | None = None
    while i < n:
        tok = tokens[i].strip("\"'")
        if tok in _GIT_BOOL_FLAGS:
            i += 1
            continue
        if tok in _GIT_VALUE_FLAGS:
            if tok == "-C" and i + 1 < n:
                c_path = str(Path(c_path or "") / tokens[i + 1])
            i += 2
            continue
        if tok.startswith(("-C", "-c", "--git-dir", "--work-tree", "--exec-path")) and len(tok) > 2:
            if tok.startswith("-C") and len(tok) > 2:
                c_path = str(Path(c_path or "") / tok[2:])
            i += 1
            continue
        break
    # 保留 "git" 作为首 token（调用方按 [prog, sub, …] 形状判定），只剥掉前面的
    # 前缀与后面的全局选项；`git` 裸段（无子命令）返回 ["git"] → len<2 → None。
    root = Path(c_path) if c_path else None
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
    for seg, _separator in split_shell_segments(text):
        tokens = [t.strip("\"'") for t in _segment_tokens(seg)]
        parts = _git_seg_parts(tokens)
        if parts is None:
            continue
        _, _, pre = parts
        for i, tok in enumerate(pre):
            if tok == "-c" and i + 1 < len(pre) and pre[i + 1].lower() in _SKIP_GATE_ASSIGN:
                return True
    return False


def skip_gate_config_change(segment: str) -> bool | None:
    """解析单段仓库级豁免变更；True 为设置，False 为取消，None 为无关。"""
    tokens = [token.strip("\"'") for token in _segment_tokens(segment)]
    parts = _git_seg_parts(tokens)
    if parts is None:
        return None
    sub, index, _pre = parts
    if sub != "config":
        return None
    rest = tokens[index + 1:]
    # 其它文件或跨仓配置作用域不是当前仓库的可证明本地豁免。
    if any(token in ("-f", "--file", "--global", "--system", "--blob")
           or token.startswith(("-f", "--file=", "--blob=")) for token in rest):
        return None
    if "--unset" in rest or "--unset-all" in rest:
        return False if any(token.lower() == "codeguard.skipgate" for token in rest) else None
    if any(token in _QUERY_CONFIG_FLAGS for token in rest):
        return None
    args = [token for token in rest if not token.startswith("-")]
    if len(args) < 2 or args[0].lower() != "codeguard.skipgate":
        return None
    if args[1].lower() in ("true", "1", "yes"):
        return True
    if args[1].lower() in ("false", "0", "no"):
        return False
    return None


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
    return any(skip_gate_config_change(seg) is True
               for seg, _separator in split_shell_segments(text))


_DYNAMIC_GIT_CALL = re.compile(
    r"(?:^|[^\w.])(?:os\.(?:system|popen)|subprocess\.(?:run|call|Popen|check_call|check_output)"
    r"|(?:exec|execFile|execSync|execFileSync|spawn|spawnSync))\s*\(\s*\[?\s*[\"\'\x60]git(?:[\"\'\x60]|\s)"
)
_DYNAMIC_GIT_WINDOW = 200
_DYNAMIC_SUB_QUOTED = re.compile(r"[\"\'\x60\[\s,](commit|push|add|config)[\"\'\x60\],\s]")
_DYNAMIC_SUB_TEXT = re.compile(r"\bgit\s+(commit|push|add|config)\b")


def dynamic_git_effects(text: str) -> tuple[list[str], bool | None]:
    """非 Shell 源码正文中 git 副作用的高精度识别：只认调用形态。

    `execFileSync("git", …)`、`subprocess.run(["git", …])`、`os.system("…")`
    这类调用点才是可归因信号；帮助文本/模板字符串里的 git 字面量样例不是调用
    （bump-plugin.mjs 帮助文本实测被 shell 切段误报）。命中调用点后在邻近窗口
    收集子命令与 skipGate 配置变更。不承诺分析动态拼接的 subprocess。
    """
    subs: list[str] = []
    skip: bool | None = None
    for match in _DYNAMIC_GIT_CALL.finditer(text):
        window = text[match.start(): match.start() + _DYNAMIC_GIT_WINDOW]
        found = set(_DYNAMIC_SUB_TEXT.findall(window)) | set(_DYNAMIC_SUB_QUOTED.findall(window))
        for name in ("commit", "push", "add"):
            if name in found and name not in subs:
                subs.append(name)
        if "config" in found and re.search(r"codeguard\.skipgate", window, re.IGNORECASE):
            skip = not re.search(r"--unset", window)
    return subs, skip


def _segment_is_git_side_effect(seg: str) -> bool:
    return _git_side_effect_sub(seg) is not None


def _collect_subs(text: str) -> list[str]:
    text = _flatten_substitutions(text)
    return [
        sub for seg, _separator in split_shell_segments(text)
        if (sub := _git_side_effect_sub(seg))
    ]
