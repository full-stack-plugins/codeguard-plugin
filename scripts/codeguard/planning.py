"""把已选工具与明确范围物化为执行计划，不选择语言或运行检查。"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from scope import scope_cmd

from .models import CheckPlan, CheckScope, Command


def scoped_plan(argv: Sequence[str], root: Path, *, scope: CheckScope,
                files: Sequence[str] | None = None, append_files: bool = True) -> CheckPlan:
    """复用既有 scope 配置/排除规则；空 delta 不能意外退化为全仓执行。

    Java 权威命令由原生规划器直接构造 CheckPlan，不能走通用文件追加。
    save 必须恰有一个文件，repo 不接受文件列表，调用方先处理空范围状态。
    """
    if scope == "repo":
        if files is not None:
            raise ValueError("repo 计划不能携带局部文件列表")
    elif scope in ("delta", "save"):
        if not files or (scope == "save" and len(files) != 1):
            raise ValueError("delta 需要非空文件列表；save 必须恰有一个文件")
    else:
        raise ValueError(f"未知检查范围: {scope}")
    if not argv:
        raise ValueError("检查命令不能为空")
    if "{file}" in " ".join(argv):
        if files is None:
            raise ValueError("单文件命令需要明确文件列表")
        commands = [scope_cmd(list(argv), root, single_file=f) for f in files]
    elif scope == "save":
        commands = [scope_cmd(list(argv), root, single_file=files[0], append_files=append_files)]
    else:
        commands = [scope_cmd(list(argv), root, files=list(files) if files is not None else None,
                              full_excludes=scope == "repo", append_files=append_files)]
    return CheckPlan(root, scope, tuple(Command(tuple(cmd)) for cmd in commands))
