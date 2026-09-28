"""判定引擎边界：谁签发质量结论，以及各引擎退出码如何翻译成门禁动作。

插件自带的 Legacy Python 引擎随包发布，可以签发 PASS/FAIL。
Rust ``codeguard`` 组件是后续统一内核，其就绪程度**由它自己声明**——
``codeguard capabilities --format json`` 报出的 ``capability_inventory`` 里，
每个「语言 × 平台 × 检查类别」单元的 ``status`` 取 ``implemented`` / ``gap`` /
``not_applicable``。

因此本模块**不写死**内核是否可用：写死会在内核演进后静默过期，让插件对外
给出与事实相反的说法。权威性按类别逐一判断：

- 该类别在内核自报中为 ``implemented`` → 该类别可由 Rust 签发；
- 为 ``gap``、报告不可读、或内核缺席 → 一律仍由 Legacy 签发。

这样交接是数据变化（内核自己把某个类别标为 implemented），而不是插件改代码。

本模块只做数据与规则，不执行进程：探测与能力报告由调用方注入，便于在不启动
外部工具的情况下验证门禁语义。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EngineId = Literal["legacy", "rust"]
Verdict = Literal["PASS", "FAIL", "UNVERIFIED", "INCOMPLETE"]
CapabilityStatus = Literal["implemented", "gap", "not_applicable"]

# 内核能力清单的协议标识；不匹配时视为"不可读"，按 gap 处理。
INVENTORY_REPORT_TYPE = "capability_inventory"


@dataclass(frozen=True)
class EngineSpec:
    """一个候选判定引擎的登记信息。

    ``authoritative`` 是 Legacy 的静态事实（随插件发布即可签发）；
    Rust 的权威性是**逐类别**的，见 :func:`category_authority`。
    """

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
    # Rust 是否有权威性取决于它自报的能力，不在此写死。
    authoritative=False,
    version_command=("codeguard", "--version"),
    note=(
        "就绪程度由内核自报的 capability_inventory 决定；"
        "命令面改用位置参数，无 fix/dockerfile/--lang/--ecosystem/--severity。"
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


@dataclass(frozen=True)
class CategoryAuthority:
    """某个检查类别当前由谁签发，以及依据。"""

    language: str
    platform: str
    category: str
    engine: EngineId
    status: CapabilityStatus | None
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
    verdict, blocks = _EXIT_TABLES[engine_id].get(exit_code, ("UNVERIFIED", True))
    reason = spec.note if not spec.authoritative else "Legacy 退出码语义"
    return GateOutcome(
        engine=engine_id,
        exit_code=exit_code,
        verdict=verdict,
        blocks=blocks,
        reason=reason,
    )


def _iter_cells(inventory: Any):
    """遍历能力清单中的单元，兼容带过滤器的扁平 cells 与未过滤的 languages。"""
    if not isinstance(inventory, dict):
        return
    if isinstance(inventory.get("cells"), list):
        yield from (cell for cell in inventory["cells"] if isinstance(cell, dict))
        return
    for language in inventory.get("languages") or []:
        if not isinstance(language, dict):
            continue
        for platform, categories in (language.get("platforms") or {}).items():
            if not isinstance(categories, dict):
                continue
            for category, cell in categories.items():
                if isinstance(cell, dict):
                    yield {
                        "language": language.get("language"),
                        "platform": platform,
                        "category": category,
                        **cell,
                    }


def category_authority(
    inventory: Any,
    *,
    language: str,
    platform: str,
    category: str,
) -> CategoryAuthority:
    """判断某个「语言 × 平台 × 类别」当前应由谁签发。

    只有当内核自报该单元 ``implemented`` 时才交给 Rust；其余情况（gap、
    not_applicable、清单不可读、找不到该单元、内核缺席）一律留在 Legacy。
    读不到声明不等于通过——这是 fail closed。
    """
    readable = (
        isinstance(inventory, dict)
        and inventory.get("report_type") == INVENTORY_REPORT_TYPE
    )
    if not readable:
        return CategoryAuthority(
            language=language, platform=platform, category=category,
            engine=LEGACY.id, status=None,
            reason="内核能力清单不可读或协议不匹配，权威性留在 Legacy",
        )

    for cell in _iter_cells(inventory):
        if (cell.get("language") == language and cell.get("platform") == platform
                and cell.get("category") == category):
            status = cell.get("status")
            if status == "implemented":
                return CategoryAuthority(
                    language=language, platform=platform, category=category,
                    engine=RUST.id, status="implemented",
                    reason="内核自报该检查类别已实现",
                )
            return CategoryAuthority(
                language=language, platform=platform, category=category,
                engine=LEGACY.id,
                status=status if status in ("gap", "not_applicable") else None,
                reason=f"内核自报该类别为 {status or '未知'}，权威性留在 Legacy",
            )

    return CategoryAuthority(
        language=language, platform=platform, category=category,
        engine=LEGACY.id, status=None,
        reason="内核能力清单中无该单元，按未证明处理",
    )


def resolve_authoritative(*, rust_available: bool) -> EngineSpec:
    """在**没有任何类别**自报为 implemented 时选择签发方。

    逐类别交接请用 :func:`category_authority`；本函数只回答全局兜底问题：
    二进制存在本身不构成权威。
    """
    if rust_available and not RUST.authoritative:
        return LEGACY
    return LEGACY if LEGACY.authoritative else RUST
