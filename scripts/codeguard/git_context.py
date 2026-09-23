"""将静态 Git 意图绑定到本地仓库；负责文件/进程观察，不产生宿主输出。"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from scope import changed_files

from .execution import execute
from .git_staging import (
    repository_root,
    staging_intent,  # noqa: F401 — 原导入面兼容
)
from .git_syntax import (
    _analyze_segment,
    _collect_subs,
    _flatten_substitutions,
    _git_c_path,
    _git_side_effect_sub,
    _segment_is_git_side_effect,
    _strip_command_prefix,
    dynamic_git_effects,
    inline_skip_gate,
    skip_gate_config_change,
    split_shell_segments,
)

_SCRIPT_SUFFIXES = (".sh", ".bash", ".zsh", ".py", ".mjs", ".js", ".ts")
_INTERPRETERS = ("bash", "sh", "zsh", "python", "python3", "node")
_SHELL_INTERPRETERS = ("bash", "sh", "zsh")


class GitIntentError(ValueError):
    """静态命令意图无法可靠归属时拒绝猜测。"""


class GitTargetError(GitIntentError):
    """显式 Git 目标无法绑定时拒绝猜测其它仓库。"""


@dataclass(frozen=True)
class GitOperation:
    """一个静态 Git 副作用及其实际仓库；门禁面不能跨仓传播。"""

    root: Path
    mode: str
    bypass: str | None = None
    config_state: bool | None = None
    source_command: str | None = None
    source_cwd: Path | None = None


def _is_git_repo(p: Path) -> bool:
    """只读查询 Git 仓边界；工具不可用时交由调用者降级。"""
    return execute(["git", "-C", str(p), "rev-parse", "--git-dir"], Path.cwd(), 10).returncode == 0


def resolve_git_operations(command: str, cwd: Path | None = None, *,
                           _depth: int = 0) -> list[GitOperation]:
    """顺序扫描命令链，将每个 git commit/push 绑定到自己的仓库。

    链式发布（cd plugins && git commit && cd minimax && git push）操作
    多个仓库——每个 git 段的边界 = `git -C <path>` 显式指定的仓，否则取它
    之前最近的 cd（且必须是 git 仓）；无 cd 才用 cwd（需是 git 仓）。
    保留操作顺序，找不到任何边界返回 []。

    **必须与 is_guarded 同源判定**（`_git_side_effect_sub` 归一化后判子命令）：
    此前这里用原始 tokens[0]=="git"，`git -C /repo push`、`FOO=1 git push`、
    `sudo git push` 虽被 is_guarded 命中却解析出 roots=[]，main() 见空直接
    放行——归一化修复在 roots 层被击穿（实测三形态全部静默通过）。
    """
    command = _flatten_substitutions(command)
    operations: list[GitOperation] = []
    chain_skip_states: dict[Path, bool] = {}
    uncertain_roots: set[Path] = set()
    unresolved_indirect_add = False
    last_cd: Path | None = None
    explicit_cd = False
    caller_dir = (cwd or Path.cwd()).resolve()
    current_dir = caller_dir
    for seg, separator in split_shell_segments(command):
        if separator in ("||", ";", "\n"):
            uncertain_roots.update(chain_skip_states)
            chain_skip_states.clear()
        m = re.match(r"cd\s+(\"[^\"]+\"|'[^']+'|\S+)", seg)
        if m:
            target = (current_dir / m.group(1).strip("\"'")).resolve()
            current_dir = target
            explicit_cd = True
            last_cd = target if target.is_dir() and _is_git_repo(target) else None
            continue
        indirect = _indirect_body(seg, current_dir)
        if indirect is not None:
            body, is_shell = indirect
            if is_shell:
                body_segments = split_shell_segments(_flatten_substitutions(body))
                if any(skip_gate_config_change(part) is not None
                       for part, _separator in body_segments):
                    raise GitIntentError("间接脚本修改 skipGate，无法证明后续配置状态；请拆分命令")
                body_effects = _collect_subs(body)
                if not body_effects and any(_analyze_segment(part)[0][:2] == ["git", "add"]
                                            for part, _separator in body_segments):
                    unresolved_indirect_add = True
            else:
                # 非 Shell 正文不做 shell 切段：模板字符串/帮助文本里的 git 字面量
                # 不是调用（bump-plugin.mjs 帮助文本实测误报）。只认 exec/subprocess
                # 调用形态，命中仍按「不可建模」阻断——方向安全不放松。
                dynamic_subs, dynamic_skip = dynamic_git_effects(body)
                if dynamic_skip is not None:
                    raise GitIntentError("间接脚本修改 skipGate，无法证明后续配置状态；请拆分命令")
                if "add" in dynamic_subs and not any(
                        name in dynamic_subs for name in ("commit", "push")):
                    unresolved_indirect_add = True
                body_effects = [name for name in dynamic_subs if name in ("commit", "push")]
            if body_effects:
                if unresolved_indirect_add and "commit" in body_effects:
                    raise GitIntentError("间接脚本暂存与后续提交跨越解释器边界；请拆分命令")
                if not is_shell or _depth:
                    raise GitIntentError("间接 Git 操作不能可靠建模；请单独执行并验证")
                inner = resolve_git_operations(body, cwd=current_dir, _depth=1)
                if not inner:
                    raise GitIntentError("间接 Git 操作无法绑定仓库；请单独执行并验证")
                for operation in inner:
                    if operation.root in uncertain_roots:
                        raise GitIntentError("间接 Git 操作跨越不确定的 skipGate 控制流")
                    inherited = chain_skip_states.get(operation.root)
                    state = operation.config_state if operation.config_state is not None else inherited
                    bypass = operation.bypass or ("chain-skipGate" if state else None)
                    operations.append(GitOperation(
                        operation.root, operation.mode, bypass, state, body, current_dir,
                    ))
            continue
        mode = _git_side_effect_sub(seg)
        if mode == "commit" and unresolved_indirect_add:
            raise GitIntentError("间接脚本暂存与后续提交跨越解释器边界；请拆分命令")
        skip_change = skip_gate_config_change(seg) if mode is None else None
        if mode is None and skip_change is None:
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
            repo = repository_root(root)
            if skip_change is not None:
                chain_skip_states[repo] = skip_change
                uncertain_roots.discard(repo)
            else:
                if repo in uncertain_roots:
                    raise GitIntentError(
                        f"{repo} 的链式 skipGate 跨越非 && 分隔符，配置是否生效无法证明；"
                        "请拆分命令后重试"
                    )
                bypass = ("inline-skipGate" if inline_skip_gate(seg) else
                          "chain-skipGate" if chain_skip_states.get(repo) else None)
                operations.append(GitOperation(repo, mode, bypass, chain_skip_states.get(repo)))
    return operations


def resolve_project_roots(command: str, cwd: Path | None = None) -> list[Path]:
    """兼容旧导入面：返回 Git 副作用涉及的仓根，去重且保序。"""
    return list(dict.fromkeys(op.root for op in resolve_git_operations(command, cwd)))


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


def _indirect_body(segment: str, invocation_dir: Path) -> tuple[str, bool] | None:
    """取得一段解释器实际收到的 -c 文本或脚本正文；不执行脚本。"""
    try:
        tokens = _strip_command_prefix(shlex.split(segment))
    except ValueError:
        return None
    if not tokens:
        return None
    program = tokens[0].rsplit("/", 1)[-1]
    if program not in _INTERPRETERS:
        return None
    rest = tokens[1:]
    is_shell = program in _SHELL_INTERPRETERS
    script: str | None = None
    for index, option in enumerate(rest):
        if option == "--":
            script = rest[index + 1] if index + 1 < len(rest) else None
            break
        if option == "-c" or (is_shell and option.startswith("-") and not option.startswith("--")
                              and option[1:].isalpha() and "c" in option[1:]):
            return (rest[index + 1], is_shell) if index + 1 < len(rest) else None
        if option.startswith("-"):
            continue
        script = option
        break
    if script is not None:
        target = (invocation_dir / script).resolve()
        if not target.is_file() or target.suffix not in _SCRIPT_SUFFIXES:
            return None
        try:
            if target.stat().st_size <= 1_000_000:
                return target.read_text(encoding="utf-8", errors="ignore"), is_shell
        except OSError:
            return None
    return None


def _indirect_bodies(command: str, cwd: Path | None = None):
    """按外层 cd 顺序取得一层解释器正文，供兼容检测接口复用。"""
    current_dir = (cwd or Path.cwd()).resolve()
    for segment, _separator in split_shell_segments(command):
        match = re.match(r"cd\s+(\"[^\"]+\"|'[^']+'|\S+)", segment)
        if match:
            current_dir = (current_dir / match.group(1).strip("\"'")).resolve()
            continue
        indirect = _indirect_body(segment, current_dir)
        if indirect is not None:
            yield indirect


def _command_indirect(command: str) -> bool:
    """兼容一层间接识别；不执行脚本，不承诺分析动态拼接的 subprocess。"""
    for body, is_shell in _indirect_bodies(command):
        if is_shell:
            if any(_segment_is_git_side_effect(segment)
                   for segment, _separator in split_shell_segments(body)):
                return True
        else:
            subs, _skip = dynamic_git_effects(body)
            if any(name in subs for name in ("commit", "push")):
                return True
    return False


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




def _guarded_mode(command: str, cwd: Path | None = None) -> str | None:
    """门禁命中时返回兜底门禁面：commit 或 push（同一仓两面并存时推送面
    携带 pending_commit 可覆盖两面）；未命中返回 None。

    同时汇总直接命令段与一层解释器间接正文（脚本/-c 内联）。
    is_guarded 即本函数的存在性判断——面判定与命中判定共用同一套扫描，
    避免"命中了却选错面"的分叉。可直接解析的命令由 GitOperation 按仓
    分别选择门禁面，不能把这里的整链模式传播到其它仓。
    """
    subs = _collect_subs(command)
    for body, is_shell in _indirect_bodies(command, cwd):
        if is_shell:
            subs.extend(_collect_subs(body))
        else:
            dynamic_subs, _skip = dynamic_git_effects(body)
            subs.extend(name for name in dynamic_subs if name in ("commit", "push"))
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
