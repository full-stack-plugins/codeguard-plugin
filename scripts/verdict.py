"""旧导入路径的兼容层；判定实现仅存在于 codeguard.verdict。"""
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
