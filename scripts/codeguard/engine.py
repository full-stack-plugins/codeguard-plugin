"""判定引擎边界：谁签发质量结论，以及各引擎退出码如何翻译成门禁动作。

插件自带的 Legacy Python 引擎随包发布，可以签发 PASS/FAIL。
Rust ``codeguard`` 组件是后续统一内核，但当前对所有质量路径固定返回退出码 3
（检查未完成），能力矩阵全部条目为 ``gap``。在它自行解除未完成状态之前，
不得用它签发任何质量结论。

本模块只做数据与规则，不执行进程：探测结果由调用方注入，便于在不启动外部
工具的情况下验证门禁语义。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EngineId = Literal["legacy", "rust"]
Verdict = Literal["PASS", "FAIL", "UNVERIFIED", "INCOMPLETE"]


@dataclass(frozen=True)
class EngineSpec:
    """一个候选判定引擎的登记信息；权威性是显式事实，不由存在性推导。"""

    id: EngineId
    label: str
    authoritative: bool
    version_command: tuple[str, ...]
    note: str


LEGACY = EngineSpec(
    id="legacy",
    label="Legacy Python 引擎（随插件发布）",
    authoritative=True,
    version_command=("codeguard", "detect"),
    note="可签发 PASS/FAIL；fix、dockerfile、--lang、--ecosystem、--severity 仅此侧存在。",
)

RUST = EngineSpec(
    id="rust",
    label="Rust codeguard 组件（独立内核）",
    authoritative=False,
    version_command=("codeguard", "--version"),
    note=(
        "对所有质量路径固定返回退出码 3（未完成），能力矩阵全部 gap；"
        "只可作只读观察，命令面改用位置参数，无 fix/dockerfile/--lang/--ecosystem/--severity。"
    ),
)

ENGINES: dict[EngineId, EngineSpec] = {LEGACY.id: LEGACY, RUST.id: RUST}


@dataclass(frozen=True)
class GateOutcome:
    """一次引擎执行翻译出的门禁动作。

    ``blocks`` 只表示"是否挡住交付"，与"是否有问题"是两件事：
    UNVERIFIED 与 INCOMPLETE 都没有发现违规，但同样不允许放行。
    """

    engine: EngineId
    exit_code: int
    verdict: Verdict
    blocks: bool
    reason: str


# Legacy：0 通过 / 1 无法验证 / 2 存在违规 / 3 参数错误。
LEGACY_EXIT: dict[int, tuple[Verdict, bool]] = {
    0: ("PASS", False),
    1: ("UNVERIFIED", True),
    2: ("FAIL", True),
    3: ("UNVERIFIED", True),
}

# Rust：0 通过 / 1 违规 / 2 参数错误 / 3 检查未完成 / 4 内部故障 / 130 用户中断。
RUST_EXIT: dict[int, tuple[Verdict, bool]] = {
    0: ("PASS", False),
    1: ("FAIL", True),
    2: ("UNVERIFIED", True),
    3: ("INCOMPLETE", True),
    4: ("INCOMPLETE", True),
    130: ("INCOMPLETE", True),
}

_EXIT_TABLES: dict[EngineId, dict[int, tuple[Verdict, bool]]] = {
    LEGACY.id: LEGACY_EXIT,
    RUST.id: RUST_EXIT,
}


def translate(engine_id: EngineId, exit_code: int) -> GateOutcome:
    """把某引擎的退出码翻译成门禁动作；未知码一律按未验证处理。"""
    spec = ENGINES[engine_id]
    verdict, blocks = _EXIT_TABLES[engine_id].get(
        exit_code, ("UNVERIFIED", True)
    )
    reason = spec.note if not spec.authoritative else "Legacy 退出码语义"
    return GateOutcome(
        engine=engine_id,
        exit_code=exit_code,
        verdict=verdict,
        blocks=blocks,
        reason=reason,
    )


def resolve_authoritative(*, rust_available: bool) -> EngineSpec:
    """选择签发质量结论的引擎。

    Rust 二进制存在并不改变权威性：只要它仍对质量路径返回未完成，签发方就必须
    是 Legacy。``rust_available`` 只影响调用方是否需要提示"检测到新内核"。
    """
    if rust_available and not RUST.authoritative:
        return LEGACY
    return LEGACY if LEGACY.authoritative else RUST
