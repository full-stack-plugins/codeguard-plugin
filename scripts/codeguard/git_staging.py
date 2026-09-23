"""只读绑定拟暂存范围；Git 负责 pathspec，宿主负责呈现未知边界。"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from git_snapshot import SnapshotError, git

from .git_syntax import _analyze_segment, _flatten_substitutions

_LANES = ("staged", "unstaged", "untracked")


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


def staging_intent(command: str, project_root: Path | None = None) -> tuple[tuple[str, ...], list[str]]:
    """逐段绑定 cd/-C 与仓库；返回 lanes 和已解析的仓根相对字面路径。

    保留旧无 project_root 的调用面；硬门禁必须传目标仓，以免多仓范围串扰。
    不执行 add，不模拟动态 Shell、交互暂存或 pathspec-from-file；不能证明时抛
    SnapshotError，由 Hook 以既有 fail-open 协议明示未验证。
    """
    cwd = Path.cwd().resolve()
    wanted = Path(project_root).resolve() if project_root is not None else None
    lanes = {"staged"}
    extra = set()
    for segment in re.split(r"&&|\|\||;|\n", _flatten_substitutions(command)):
        try:
            words = shlex.split(segment)
        except ValueError as exc:
            raise SnapshotError("暂存意图含未闭合引用，不能准确解析") from exc
        if not words:
            continue
        if words[0] == "cd" and len(words) == 2:
            cwd = (cwd / words[1]).resolve()
            continue
        tokens, c_path = _analyze_segment(segment)
        if len(tokens) < 2 or tokens[0] != "git" or tokens[1] not in ("add", "commit"):
            continue
        sub, rest = tokens[1], tokens[2:]
        if sub == "commit" and not any(flag in ("-a", "-am", "--all") for flag in rest):
            continue
        location = (cwd / c_path).resolve() if c_path is not None else cwd
        repo = repository_root(location)
        if wanted is not None and repo != wanted:
            continue
        if sub == "commit":
            if any(flag in ("-a", "-am", "--all") for flag in rest):
                lanes.add("unstaged")
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
        if paths in (["."], ["./"], [":/"]) and location == repo and not force:
            lanes.update(("staged", "unstaged") if tracked else _LANES)
            continue
        literal = "--literal-pathspecs" in words[:words.index("add")] if "add" in words else False
        extra.update(resolve_pathspecs(location, paths, tracked_only=tracked, force=force, literal=literal))
    return tuple(lane for lane in _LANES if lane in lanes), sorted(extra)
