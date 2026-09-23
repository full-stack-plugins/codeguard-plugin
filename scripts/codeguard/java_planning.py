"""Java 检查命令的纯策略；不负责文件解析、工具探测或执行。"""
from __future__ import annotations

from collections.abc import Sequence


def default_commands(system: str, executable: str, affected: Sequence[str], *,
                     full: bool, bump_only: bool) -> list[dict]:
    """保留默认 skipTests/check -x test、模块范围与有证据的纯版本轻量检查。"""
    if not affected:
        return []
    if system == "maven":
        argv = [executable, "-B"]
        if not full and "." not in affected:
            argv += ["-pl", ",".join(sorted(affected)), "-am"]
        argv += ["-DskipTests", "validate" if bump_only else "verify"]
    elif system == "gradle":
        targets = (["help"] if bump_only else ["check"] if full or "." in affected else
                   [":" + path.replace("/", ":") + ":check" for path in sorted(affected)])
        argv = [executable, *targets]
        if not bump_only:
            argv += ["-x", "test"]
    else:
        raise ValueError(f"未知 Java 构建系统: {system}")
    return [{"kind": "verify", "argv": argv}]


def configured_commands(value: object) -> list[dict]:
    """校验后复制 argv；显式声明原样优先，不添加 skipTests 或其它默认参数。"""
    if not isinstance(value, list) or not value or any(
            not isinstance(command, list) or not command or
            any(not isinstance(arg, str) or not arg or "\0" in arg for arg in command) for command in value):
        raise ValueError("java.commands 必须是非空 argv 数组列表")
    return [{"kind": "configured", "argv": list(command)} for command in value]
