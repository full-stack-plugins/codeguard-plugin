"""Java 模块级影响策略；输入已归一化的相对路径，不读取文件或启动进程。"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath

BUILD_FILES = frozenset({"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
                         "settings.gradle.kts", "gradle.properties", "mvnw", "gradlew",
                         "mvnw.cmd", "gradlew.bat", "codeguard.json"})


def is_build_path(path: str) -> bool:
    return PurePosixPath(path).name in BUILD_FILES or path.startswith((".mvn/", "gradle/"))


def relevant_paths(changed: Sequence[str] | None) -> list[str] | None:
    """None 为全量，空数组为无适用变更；资源和删除的源码仍参与影响计算。"""
    if changed is None:
        return None
    return [path for path in changed if path.endswith((".java", ".kt", ".groovy", ".scala"))
            or "/src/" in "/" + path or is_build_path(path)]


def select_impact(modules: Mapping[str, dict], changed: Sequence[str] | None, *,
                  conservative: bool) -> tuple[list[str], bool]:
    """以反向邻接表计算闭包；循环依赖有限终止，输入图不被修改。"""
    relevant = relevant_paths(changed)
    full = relevant is None or conservative or any(is_build_path(path) for path in relevant or [])
    if relevant == []:
        return [], full
    if full:
        return sorted(modules), True
    reverse: dict[str, set[str]] = {name: set() for name in modules}
    for name, module in modules.items():
        for dependency in module["dependencies"]:
            if dependency in reverse:
                reverse[dependency].add(name)
    affected = set()
    for path in relevant or []:
        owners = [name for name in modules if name == "." or path.startswith(name + "/")]
        if owners:
            affected.add(max(owners, key=len))
    pending = deque(affected)
    while pending:
        for consumer in reverse[pending.popleft()]:
            if consumer not in affected:
                affected.add(consumer)
                pending.append(consumer)
    return sorted(affected), False
