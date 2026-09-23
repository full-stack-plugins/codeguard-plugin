"""旧导入路径的兼容层；判定实现仅存在于 codeguard.verdict。

Deprecated：此模块是旧导入面的兼容外观，新代码必须从 `codeguard.verdict` 导入；
计划在下一个 major 版本移除。
"""
from codeguard.verdict import (
    FAIL,
    PASS,
    PLANNED,
    SKIPPED,
    UNVERIFIED,
    exit_status,
    finding_signatures,
    lint_verdict,
    result,
)

__all__ = [
    "FAIL", "PASS", "PLANNED", "SKIPPED", "UNVERIFIED",
    "exit_status", "finding_signatures", "lint_verdict", "result",
]
