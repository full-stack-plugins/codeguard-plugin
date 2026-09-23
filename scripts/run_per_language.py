"""旧脚本导入兼容入口；按语言检查的唯一实现位于 codeguard.language_check。"""
from __future__ import annotations

from codeguard.language_check import LANG_COMMANDS, _run, run_check, run_fix

__all__ = ["LANG_COMMANDS", "_run", "run_check", "run_fix"]
