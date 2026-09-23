"""旧脚本导入兼容入口；按语言检查的唯一实现位于 codeguard.language_check。

Deprecated：此模块是旧导入面的兼容外观，新代码必须从 `codeguard.language_check` 导入；
计划在下一个 major 版本移除。
"""
from __future__ import annotations

from codeguard.language_check import LANG_COMMANDS, _run, run_check, run_fix

__all__ = ["LANG_COMMANDS", "_run", "run_check", "run_fix"]
