"""只读 Git 基线与版本变更证据；无法证明仅项目版本变化时不降低检查等级。"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .execution import execute
from .java_build import inside

_VERSION = re.compile(r"[0-9][0-9A-Za-z._+-]*")


def _pom_without_release(body: str) -> tuple:
    document = ET.fromstring(body, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    version = document.find("{*}version")
    revision = document.find("{*}properties/{*}revision")
    if revision is not None:
        # revision 用于外部依赖、插件或任意配置时不能作为项目版本豁免。
        for node in document.iter():
            if ((node is not version and "${revision}" in (node.text or "")) or
                    any("${revision}" in value for value in node.attrib.values())):
                raise ValueError("revision 并非仅项目版本")
    versions = []
    for node in (version, revision):
        if node is not None and _VERSION.fullmatch((node.text or "").strip()):
            versions.append(node.text)
            node.text = "<project-release>"

    def shape(node):
        # 插件的任意嵌入脚本文本可能对空白敏感，不能把 strip 后相等当成只改版本。
        return (node.tag, tuple(sorted(node.attrib.items())), node.text or "",
                node.tail or "", tuple(shape(child) for child in node))

    return shape(document), tuple(versions)


def _gradle_without_release(body: str) -> tuple[str, tuple[str, ...]]:
    # 只接受独占顶层行的字面版本赋值；Groovy/Kotlin 动态语法不能靠 diff 关键词证明安全。
    # 先保守排除多行字符串/注释；其余逐字符处理引号、注释和大括号，避免误认插件块里的 version。
    if any(token in body for token in ('"""', "'''", "/*", "$/")):
        raise ValueError("Gradle 版本来源不支持静态确认")
    depth = 0
    output = []
    versions = []
    assignment = re.compile(r"\s*version\s*=\s*(['\"])([0-9][0-9A-Za-z._+-]*)\1\s*;?\s*(?://[^\n]*)?$")
    for line in body.splitlines(keepends=True):
        match = assignment.fullmatch(line.rstrip("\r\n")) if depth == 0 else None
        if match:
            versions.append(match[2])
            line = line[:match.start(2)] + "<project-release>" + line[match.end(2):]
        output.append(line)
        quote = None
        escaped = False
        for index, char in enumerate(line):
            if escaped:
                escaped = False
            elif quote:
                if char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in ("'", '"'):
                quote = char
            elif line[index:index + 2] == "//":
                break
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
        if quote or depth < 0:
            raise ValueError("Gradle 语法无法静态确认")
    if depth:
        raise ValueError("Gradle 作用域未闭合")
    return "".join(output), tuple(versions)


def is_version_bump_only(root: Path, changed: list[str] | None) -> bool:
    """比较成功读取的完整描述；无 Git 基线、删除、未知语法或混合变更均不降级。"""
    root = Path(root).resolve()
    if not changed or any(Path(name).name not in {"pom.xml", "build.gradle", "build.gradle.kts"}
                          for name in changed):
        return False
    different = False
    try:
        for name in changed:
            file = inside(root, root / name)
            # Git 对 HEAD:./path 按 cwd 解析；模块根可能不是 Git 顶层，不能误读父仓同名 POM。
            before = execute(["git", "show", f"HEAD:./{file.relative_to(root).as_posix()}"], root, 5,
                             stdin_null=True)
            if before.returncode or before.failure or "\ufffd" in before.stdout:
                return False
            current = file.read_text(encoding="utf-8")
            normalize = _pom_without_release if file.name == "pom.xml" else _gradle_without_release
            old_shape, old_versions = normalize(before.stdout)
            new_shape, new_versions = normalize(current)
            if old_shape != new_shape:
                return False
            different |= old_versions != new_versions
    except (OSError, ValueError, ET.ParseError):
        return False
    return different
