"""Maven/Gradle 只读描述适配器；不执行构建，不选择检查命令。"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


def inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"构建路径在仓外: {path}")
    return resolved


def _text(node, path: str, default="") -> str:
    return node.findtext(path, default=default).strip()


def read_maven(root: Path) -> tuple[dict, list[str]]:
    root = Path(root).resolve()
    modules: dict = {}
    reasons: list[str] = []

    def visit(directory: Path, inherited: dict):
        directory = inside(root, directory)
        name = directory.relative_to(root).as_posix()
        if name in modules:
            return
        doc = ET.parse(inside(root, directory / "pom.xml")).getroot()
        props = dict(inherited)
        properties = doc.find("{*}properties")
        if properties is not None:
            props.update({p.tag.split("}")[-1]: (p.text or "").strip() for p in properties})

        def expand(value: str) -> str:
            for _ in range(10):
                newer = re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m[1], m[0]), value)
                if newer == value:
                    break
                value = newer
            if "${" in value:
                reasons.append(f"{name}: 无法静态解析 {value}，回退全模块")
            return value

        group = expand(_text(doc, "{*}groupId") or _text(doc, "{*}parent/{*}groupId")
                       or props.get("project.groupId", ""))
        artifact = expand(_text(doc, "{*}artifactId"))
        if not artifact:
            raise ValueError(f"{name}: 缺少 artifactId")
        props.update({"project.groupId": group, "pom.groupId": group,
                      "project.artifactId": artifact})
        dependencies = []
        for dep in doc.findall("{*}dependencies/{*}dependency"):
            dependencies.append((expand(_text(dep, "{*}groupId")), expand(_text(dep, "{*}artifactId"))))
        plugins = [p.text or "" for p in doc.findall("{*}build/{*}plugins/{*}plugin/{*}artifactId")]
        modules[name] = {"path": name, "coordinate": (group, artifact),
                         "raw_dependencies": dependencies, "dependencies": [], "plugins": plugins}
        if doc.find("{*}profiles") is not None:
            reasons.append(f"{name}: Maven profiles 可能改变模块/依赖，回退根 verify")
        if dependencies and doc.findall("{*}modules/{*}module"):
            reasons.append(f"{name}: 聚合父 POM 依赖可能被子模块继承，回退根 verify")
        for child in doc.findall("{*}modules/{*}module"):
            visit(directory / expand((child.text or "").strip()), props)

    visit(root, {})
    coordinates = {}
    for name, module in modules.items():
        coordinate = module["coordinate"]
        if coordinate in coordinates:
            reasons.append("模块坐标不唯一，回退全模块")
        coordinates[coordinate] = name
    for module in modules.values():
        module["dependencies"] = sorted({coordinates[d] for d in module.pop("raw_dependencies") if d in coordinates})
        module.pop("coordinate")
    return modules, reasons


def read_gradle(root: Path) -> tuple[dict, list[str]]:
    root = Path(root).resolve()
    reasons = []
    modules = {".": {"path": ".", "dependencies": [], "plugins": []}}
    settings = next((p for p in (root / "settings.gradle.kts", root / "settings.gradle") if p.exists()), None)
    if settings:
        body = inside(root, settings).read_text()
        includes = re.findall(r"\binclude\s*(\([^)]*\)|[^\n]+)", body)
        for expression in includes:
            literals = re.findall(r"['\"](:?[\w:-]+)['\"]", expression)
            residue = re.sub(r"['\"](:?[\w:-]+)['\"]|[\s,()]", "", expression)
            if not literals or residue:
                reasons.append("Gradle include 使用动态表达式，回退根 check")
            for literal in literals:
                name = literal.lstrip(":").replace(":", "/")
                inside(root, root / name)
                modules[name] = {"path": name, "dependencies": [], "plugins": []}
        if re.search(r"includeBuild|projectDir|apply\s|\bfor\s*\(|\.each\b", body):
            reasons.append("Gradle settings 存在动态/复合构建，回退根 check")
    for name, module in modules.items():
        directory = inside(root, root / name)
        build = next((p for p in (directory / "build.gradle.kts", directory / "build.gradle") if p.exists()), None)
        if not build:
            reasons.append(f"{name}: 没有可读取的 Gradle 构建描述，回退根 check")
            continue
        body = inside(root, build).read_text()
        references = re.findall(r"\bproject\s*\(\s*(?:path\s*[:=]\s*)?['\"](:[\w:-]+)['\"]\s*\)", body)
        module["dependencies"] = sorted({r.lstrip(":").replace(":", "/") for r in references})
        if any(d not in modules for d in module["dependencies"]):
            reasons.append(f"{name}: 引用了未声明项目，回退根 check")
        if len(re.findall(r"\bproject\s*\(", body)) != len(references) or re.search(
                r"apply\s+from|apply\s*\(\s*from|subprojects|allprojects|buildSrc|\bprojects\.|\bif\s*\(|\bfor\s*\(", body):
            reasons.append(f"{name}: Gradle 动态构建无法可靠缩小范围，回退根 check")
    if (root / "buildSrc").exists():
        reasons.append("存在 buildSrc 构建逻辑，回退根 check")
    return modules, reasons
