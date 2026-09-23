"""只读绑定拟暂存范围；Git 负责 pathspec，宿主负责呈现未知边界。"""
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from git_snapshot import SnapshotError, git

from .git_syntax import _analyze_segment, _flatten_substitutions, split_shell_segments

_LANES = ("staged", "unstaged", "untracked")


@dataclass(frozen=True)
class _StagingAction:
    """已绑定仓库的静态暂存事件；投影阶段再决定是否影响拟提交面。"""

    kind: str
    root: Path
    location: Path
    flags: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    literal: bool = False


def repository_root(cwd: Path) -> Path:
    """Git 返回真实 worktree 根，不将仓内子目录当仓库身份。"""
    return Path(os.fsdecode(git(cwd, "rev-parse", "--show-toplevel")).strip()).resolve()


def resolve_pathspecs(cwd: Path, paths: list[str], *, tracked_only=False,
                     force=False, literal=False) -> list[str]:
    """一批 Git pathspec 一次查询，保留 exclude 的集合语义与 NUL 文件名。"""
    args = ["--literal-pathspecs"] if literal else []
    args += ["ls-files", "--full-name", "--cached", "-z"]
    if not tracked_only:
        args.append("--others")
    if not force:
        args.append("--exclude-standard")
    return sorted({os.fsdecode(name) for name in git(cwd, *args, "--", *paths).split(b"\0") if name})


def staging_intent(command: str, project_root: Path | None = None, *,
                   cwd: Path | None = None,
                   through_last_commit: bool = False) -> tuple[tuple[str, ...], list[str]]:
    """逐段绑定 cd/-C 与仓库；返回 lanes 和已解析的仓根相对字面路径。

    保留旧无 project_root 的调用面；硬门禁必须传目标仓，以免多仓范围串扰。
    不执行 add，不模拟动态 Shell、交互暂存或 pathspec-from-file；不能证明时抛
    SnapshotError，由 Hook 以既有 fail-open 协议明示未验证。
    through_last_commit 仅供无间接脚本的硬门禁使用：同仓最后一次 commit
    之后的 add 不属于本次拟提交内容。默认保持旧的完整暂存意图调用面。
    """
    current_dir = (cwd or Path.cwd()).resolve()
    wanted = Path(project_root).resolve() if project_root is not None else None
    if through_last_commit and wanted is None:
        raise ValueError("按提交顺序投影暂存面需要明确目标仓")
    actions: list[_StagingAction] = []
    for segment, _separator in split_shell_segments(_flatten_substitutions(command)):
        try:
            words = shlex.split(segment)
        except ValueError as exc:
            raise SnapshotError("暂存意图含未闭合引用，不能准确解析") from exc
        if not words:
            continue
        if words[0] == "cd" and len(words) == 2:
            current_dir = (current_dir / words[1]).resolve()
            continue
        tokens, c_path = _analyze_segment(segment)
        if len(tokens) < 2 or tokens[0] != "git" or tokens[1] not in ("add", "commit"):
            continue
        sub, rest = tokens[1], tokens[2:]
        location = (current_dir / c_path).resolve() if c_path is not None else current_dir
        repo = repository_root(location)
        if wanted is not None and repo != wanted:
            continue
        if sub == "commit":
            actions.append(_StagingAction("commit", repo, location,
                                          flags=tuple(flag for flag in rest
                                                      if flag in ("-a", "-am", "--all"))))
            continue
        flags, paths = [], []
        positional = False
        for item in rest:
            if item == "--" and not positional:
                positional = True
            elif item.startswith("-") and not positional:
                flags.append(item)
            else:
                paths.append(item)
        literal = "--literal-pathspecs" in words[:words.index("add")] if "add" in words else False
        actions.append(_StagingAction("add", repo, location, tuple(flags), tuple(paths), literal))

    cutoff = len(actions)
    if through_last_commit:
        cutoff = max((index + 1 for index, action in enumerate(actions)
                      if action.kind == "commit"), default=0)
    lanes = {"staged"}
    extra = set()
    for action in actions[:cutoff]:
        if action.kind == "commit":
            if action.flags:
                lanes.add("unstaged")
            continue
        flags, paths = action.flags, action.paths
        if any(flag not in ("-A", "--all", "-u", "--update", "-f", "--force", "-v", "--verbose") for flag in flags):
            raise SnapshotError("不支持的 git add 选项，需要独立验证暂存面")
        if any("$" in path or "`" in path for path in paths):
            raise SnapshotError("动态 git add 路径需要独立验证")
        tracked = any(flag in ("-u", "--update") for flag in flags)
        force = any(flag in ("-f", "--force") for flag in flags)
        all_files = any(flag in ("-A", "--all") for flag in flags)
        if not paths:
            if tracked:
                lanes.add("unstaged")
            elif all_files:
                lanes.update(_LANES)
            continue
        if paths in ((".",), ("./",), (":/",)) and action.location == action.root and not force:
            lanes.update(("staged", "unstaged") if tracked else _LANES)
            continue
        extra.update(resolve_pathspecs(action.location, list(paths), tracked_only=tracked,
                                       force=force, literal=action.literal))
    return tuple(lane for lane in _LANES if lane in lanes), sorted(extra)
