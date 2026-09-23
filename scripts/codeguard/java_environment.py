"""Java 执行环境观察：wrapper 选择和宿主 JDK 定位，不运行构建或安装工具。"""
from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .execution import execute
from .java_build import inside


def build_executable(root: Path, system: str) -> str:
    """优先项目 wrapper；存在但不可执行时明确拒绝，不能静默退回不兼容版本。"""
    root = Path(root).resolve()
    wrapper = "mvnw" if system == "maven" else "gradlew"
    if os.name == "nt":
        wrapper += ".cmd" if system == "maven" else ".bat"
    path = inside(root, root / wrapper)
    if path.exists() and os.name != "nt" and not os.access(path, os.X_OK):
        raise ValueError(f"wrapper 不可执行: {wrapper}")
    return "./" + wrapper if path.is_file() else "mvn" if system == "maven" else "gradle"


def resolve_java_home(root: Path) -> tuple[str | None, str | None]:
    """只解析根 POM 显式版本及属性引用，按宿主已安装 JDK 定位；不修改 os.environ。"""
    root = Path(root).resolve()
    pom = inside(root, root / "pom.xml")
    if not pom.is_file():
        return None, None
    try:
        document = ET.parse(pom).getroot()
        properties = document.find("{*}properties")
        values = {node.tag.split("}")[-1]: (node.text or "").strip() for node in properties} if properties is not None else {}
        version = (values.get("java.version") or values.get("maven.compiler.release") or
                   document.findtext("{*}java.version") or document.findtext("{*}maven.compiler.release"))
        if not version:
            return None, None
        for _ in range(10):
            expanded = re.sub(r"\$\{([^}]+)\}", lambda match: values.get(match[1], match[0]), version)
            if expanded == version:
                break
            version = expanded
        major = re.fullmatch(r"(?:1\.)?(\d+)(?:[.\-+_][0-9A-Za-z._+\-]*)?", version.strip())
        if not major:
            return None, f"无法静态解析 JDK 版本: {version}"
        required = int(major[1])
    except (OSError, ValueError, ET.ParseError) as exc:
        return None, f"无法解析 JDK 声明: {exc}"

    if sys.platform == "darwin":
        result = execute(["/usr/libexec/java_home", "-v", str(required)], root, 5, stdin_null=True)
        if not result.returncode and result.stdout.strip() and "\ufffd" not in result.stdout:
            return result.stdout.strip(), None
    elif sys.platform == "linux":
        result = execute(["update-alternatives", "--list", "java"], root, 5, stdin_null=True)
        if not result.returncode:
            for line in result.stdout.splitlines():
                match = re.search(r"java[-.](\d+)", line)
                if match and int(match[1]) == required:
                    return str(Path(line.strip()).parent.parent), None
    return None, f"需要 JDK {required}，当前环境无匹配版本"
