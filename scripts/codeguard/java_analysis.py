"""Java 只读分析应用：装配描述、影响策略、命令与环境；不执行构建。"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .config import get_overrides
from .java_build import inside, read_gradle, read_maven
from .java_changes import is_version_bump_only
from .java_environment import build_executable, resolve_java_home
from .java_impact import select_impact
from .java_planning import configured_commands, default_commands


def _explicit_commands(root: Path) -> list[dict] | None:
    path = inside(root, root / "codeguard.json")
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    java = data.get("java", {})
    if not isinstance(java, dict):
        raise TypeError("codeguard.json java 必须为对象")
    value = java.get("commands")
    return configured_commands(value) if value is not None else None


def analyze(project_root: str | Path, changed: list[str] | None = None) -> dict:
    """保留 CLI/MCP 计划信封；PLANNED 是尚未执行，不能冒充验证通过。"""
    root = Path(project_root).resolve()
    plan = {"status": "UNVERIFIED", "root": str(root), "build_system": None,
            "changed_paths": changed, "analysis_level": "module", "modules": [],
            "affected_modules": [], "commands": [], "conservative": False, "reasons": [],
            "gaps": ["模块依赖图不是完整符号/业务语义分析"]}
    try:
        get_overrides(root)
        normalized = None if changed is None else [inside(root, root / name).relative_to(root).as_posix()
                                                   for name in changed]
        if (root / "pom.xml").is_file():
            system, (modules, reasons) = "maven", read_maven(root)
        elif any((root / name).is_file() for name in ("build.gradle", "build.gradle.kts",
                                                     "settings.gradle", "settings.gradle.kts")):
            system, (modules, reasons) = "gradle", read_gradle(root)
        else:
            raise ValueError("未找到 Maven/Gradle 构建描述")
        plan.update(build_system=system, modules=list(modules.values()))
        executable = build_executable(root, system)
        plan["executable"] = executable
        affected, full = select_impact(modules, normalized, conservative=bool(reasons))
        commands = []
        if affected:
            commands = _explicit_commands(root)
            if commands is not None:
                reasons.append("使用 codeguard.json 明确声明的权威检查命令")
            else:
                bump_only = is_version_bump_only(root, normalized)
                commands = default_commands(system, executable, affected, full=full, bump_only=bump_only)
                if bump_only:
                    reasons.append("已比对 Git HEAD 与当前构建描述：仅项目版本变化，采用轻量检查")
        plugins = {plugin for module in modules.values() for plugin in module["plugins"]}
        if not plugins.intersection({"maven-checkstyle-plugin", "maven-pmd-plugin", "spotbugs-maven-plugin"}):
            plan["gaps"].append("未确认静态规则已绑定生命周期；verify/check 成功不代表 Checkstyle/PMD 全覆盖")
        home, reason = resolve_java_home(root)
        if home:
            for command in commands:
                command["env"] = {"JAVA_HOME": home}
            reasons.append(f"JAVA_HOME={home}")
        elif reason:
            reasons.append(reason)
        plan.update(status="PLANNED" if commands else "SKIPPED", commands=commands,
                    affected_modules=affected, conservative=bool(full and normalized is not None),
                    reasons=reasons or ["按构建模块及反向依赖闭包选择；命令尚未执行"])
    except (OSError, ValueError, TypeError, ET.ParseError) as exc:
        plan.update(status="UNVERIFIED", commands=[], reasons=[str(exc)])
    return plan
