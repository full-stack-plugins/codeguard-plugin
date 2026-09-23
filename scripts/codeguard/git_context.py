"""将静态 Git 意图绑定到本地仓库；负责文件/进程观察，不产生宿主输出。"""
from __future__ import annotations

import shlex
from pathlib import Path

from scope import changed_files

from .execution import execute
from .git_staging import (
    repository_root,
    staging_intent,  # noqa: F401 — 原导入面兼容
)
from .git_syntax import (
    _collect_subs,
    _flatten_substitutions,
    _git_c_path,
    _git_side_effect_sub,
    _segment_is_git_side_effect,
)

_SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".mjs", ".js", ".ts")
_INTERPRETERS = ("bash", "sh", "zsh", "python", "python3", "node")


class GitTargetError(ValueError):
    """显式 Git 目标无法绑定时拒绝猜测其它仓库。"""


def _is_git_repo(p: Path) -> bool:
    """只读查询 Git 仓边界；工具不可用时交由调用者降级。"""
    return execute(["git", "-C", str(p), "rev-parse", "--git-dir"], Path.cwd(), 10).returncode == 0


def resolve_project_roots(command: str, cwd: Path | None = None) -> list[Path]:
    """顺序扫描命令链，收集每个 git commit/push 段各自的仓库边界。

    链式发布（cd plugins && git commit && cd minimax && git push）操作
    多个仓库——每个 git 段的边界 = `git -C <path>` 显式指定的仓，否则取它
    之前最近的 cd（且必须是 git 仓）；无 cd 才用 cwd（需是 git 仓）。
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
    explicit_cd = False
    caller_dir = (cwd or Path.cwd()).resolve()
    current_dir = caller_dir
    for seg in re.split(r"&&|\|\||;|\n", command):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r"cd\s+(\"[^\"]+\"|'[^']+'|\S+)", seg)
        if m:
            target = (current_dir / m.group(1).strip("\"'")).resolve()
            current_dir = target
            explicit_cd = True
            last_cd = target if target.is_dir() and _is_git_repo(target) else None
            continue
        if _git_side_effect_sub(seg) is None:
            continue
        c_path = _git_c_path(seg)
        if c_path is not None:
            c_path = (current_dir / c_path).resolve()
        if c_path is not None:
            root = c_path if c_path.is_dir() and _is_git_repo(c_path) else None
            if root is None:
                raise GitTargetError(f"git -C 显式目标不是可解析的 Git 工作树：{c_path}")
        else:
            if explicit_cd and last_cd is None:
                raise GitTargetError(f"cd 显式目标不是可解析的 Git 工作树：{current_dir}")
            root = last_cd if explicit_cd else (caller_dir if _is_git_repo(caller_dir) else None)
        if root:
            root = repository_root(root)
            if root not in roots:
                roots.append(root)
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


def _indirect_bodies(command: str):
    """只读取得一层解释器脚本/内联文本，共享大小上限与读取失败边界。"""
    import re
    for seg in re.split(r"&&|\|\||;|\n", command):
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.strip().split()
        if not tokens:
            continue
        prog = tokens[0].rsplit("/", 1)[-1]
        if prog not in _INTERPRETERS:
            continue
        rest = tokens[1:]
        if "-c" in rest:
            yield " ".join(rest[rest.index("-c") + 1:])
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
            yield body
            break


def _command_indirect(command: str) -> bool:
    """兼容一层间接识别；不执行脚本，不承诺分析动态拼接的 subprocess。"""
    import re
    return any(_segment_is_git_side_effect(segment)
               for body in _indirect_bodies(command)
               for segment in re.split(r"&&|\|\||;|\n", body))


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




def _guarded_mode(command: str) -> str | None:
    """门禁命中时返回生效的门禁面：commit 或 push（push 优先——两面并存时
    推送面是提交面的超集，按更宽的面检查）；未命中返回 None。

    直接命令段先判定；未命中再走一层解释器间接（脚本/-c 内联）。
    is_guarded 即本函数的存在性判断——面判定与命中判定共用同一套扫描，
    避免"命中了却选错面"的分叉。
    """
    subs = _collect_subs(command)
    if not subs:
        for body in _indirect_bodies(command):
            subs = _collect_subs(body)
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
