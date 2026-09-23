"""与宿主、注册表和进程无关的不可变执行契约。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CheckScope = Literal["repo", "delta", "save"]


@dataclass(frozen=True)
class Command:
    """已物化的命令；环境只保存该命令的覆盖，不复制宿主凭据。"""

    argv: tuple[str, ...]
    env: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "argv", tuple(self.argv))
        object.__setattr__(self, "env", tuple(tuple(pair) for pair in self.env))
        if not self.argv or not self.argv[0]:
            raise ValueError("检查命令不能为空")


@dataclass(frozen=True)
class CheckPlan:
    """显式范围与顺序命令；规划完成后可原样复检，不重新扩大范围。"""

    cwd: Path
    scope: CheckScope
    commands: tuple[Command, ...]

    def __post_init__(self):
        object.__setattr__(self, "cwd", Path(self.cwd))
        object.__setattr__(self, "commands", tuple(self.commands))
        if self.scope not in ("repo", "delta", "save") or not self.commands:
            raise ValueError("执行计划必须有明确范围和至少一条命令")


@dataclass(frozen=True)
class ProcessResult:
    """一次调用的不可变证据；非零退出不自动等于代码违规。"""

    argv: tuple[str, ...]
    cwd: Path
    returncode: int
    stdout: str = ""
    stderr: str = ""
    failure: Literal["timeout", "not_found", "os_error", "output_limit"] | None = None

    def as_tuple(self) -> tuple[int, str, str]:
        """兼容旧脚本的 (rc, stdout, stderr) 返回约定。"""
        return self.returncode, self.stdout, self.stderr


@dataclass(frozen=True)
class PlanExecution:
    """已实际执行的有序证据，不包含尚未运行的计划项。"""

    attempts: tuple[ProcessResult, ...]

    @property
    def terminal(self) -> ProcessResult:
        """首个非零结果，或全部执行成功时的最后一项。"""
        return self.attempts[-1]


@dataclass(frozen=True)
class GateDecision:
    """已执行检查的审计数据，由调用线程附加原仓与会话身份。"""

    argv: tuple[str, ...]
    returncode: int
    status: str
    reason: str


@dataclass(frozen=True)
class GateOutcome:
    """单语言的独立结果；并发 worker 不共享备注列表或写审计。"""

    failure: tuple[str, str, str, str] | None = None
    notes: tuple[str, ...] = ()
    decisions: tuple[GateDecision, ...] = ()
