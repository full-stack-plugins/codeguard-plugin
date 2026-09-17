"""detect_lang.py：项目语言检测 + 用户配置加载 + linter 命令表。

被 hooks/、commands/、skills/ 共享。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional


# === 文件扩展名 → 语言 ===
EXT_LANG_MAP = {
    ".java": "java",
    ".rs": "rust",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
}


# === 项目标识文件 → 语言 ===
PROJECT_MARKERS = {
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "Cargo.toml": "rust",
    "package.json": "typescript",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
}


# === 每种语言的 linter 命令 ===
LANG_COMMANDS = {
    "java": {
        "lint": ["mvn", "-q", "javadoc:jar", "-DskipTests"],
        "format": ["mvn", "-q", "spotless:apply"],
    },
    "rust": {
        "lint": ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"],
        "format": ["cargo", "fmt"],
    },
    "typescript": {
        "lint": ["npx", "eslint", ".", "--max-warnings", "0"],
        "format": ["npx", "eslint", ".", "--fix"],
    },
    "python": {
        "lint": ["ruff", "check", "."],
        "format": ["ruff", "check", ".", "--fix"],
    },
}


def detect_language(file_path: str | Path) -> Optional[str]:
    """根据文件扩展名判断语言；非代码文件返回 None"""
    suffix = Path(file_path).suffix.lower()
    return EXT_LANG_MAP.get(suffix)


def find_project_root(start: str | Path) -> Optional[Path]:
    """从 start 路径向上找项目根（识别到 pom.xml/Cargo.toml/.git 即停）"""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for _ in range(10):
        if (p / ".git").exists():
            return p
        for marker in PROJECT_MARKERS:
            if (p / marker).exists():
                return p
        if p.parent == p:
            return None
        p = p.parent
    return None


def detect_languages(project_root: Path) -> list[str]:
    """检测项目根中存在的语言（看标记文件 + 扫描源码目录）"""
    langs: set[str] = set()
    # 标记文件
    for marker, lang in PROJECT_MARKERS.items():
        if (project_root / marker).exists():
            langs.add(lang)
    # 源码目录（浅扫描）
    src_dirs = ["src", "src/main/java", "src/main", "lib", "pkg", "tests"]
    for d in src_dirs:
        if not (project_root / d).is_dir():
            continue
        for f in (project_root / d).rglob("*"):
            if f.is_file():
                lang = detect_language(f)
                if lang:
                    langs.add(lang)
                    break
        else:
            continue
        if len(langs) >= 2:
            break
    # 排序保证稳定输出
    return sorted(langs)


def load_user_config() -> dict:
    """从 ~/.zcode/settings.local.yaml 读插件配置（简化版）"""
    cfg_path = Path.home() / ".zcode" / "settings.local.yaml"
    if not cfg_path.exists():
        return {
            "enabled_languages": [],
            "strict_mode": True,
            "auto_fix_on_save": True,
            "lint_timeout_seconds": 120,
        }
    # 简化：用正则抠 codelint 块，避免依赖 yaml 库
    try:
        text = cfg_path.read_text()
    except OSError:
        return _defaults()
    cfg = _defaults()
    # 抓 codelint: {...} 块
    m = re.search(r"codelint:\s*(\{.*?\n\})", text, re.DOTALL)
    if not m:
        return cfg
    block = m.group(1)
    for key in ("strict_mode", "auto_fix_on_save"):
        mm = re.search(rf"{key}:\s*(true|false)", block)
        if mm:
            cfg[key] = mm.group(1) == "true"
    mm = re.search(r"lint_timeout_seconds:\s*(\d+)", block)
    if mm:
        cfg["lint_timeout_seconds"] = int(mm.group(1))
    mm = re.search(r"enabled_languages:\s*\[([^\]]*)\]", block)
    if mm:
        items = [s.strip().strip('"\'') for s in mm.group(1).split(",") if s.strip()]
        cfg["enabled_languages"] = items if items else []
    return cfg


def _defaults() -> dict:
    return {
        "enabled_languages": [],
        "strict_mode": True,
        "auto_fix_on_save": True,
        "lint_timeout_seconds": 120,
    }


if __name__ == "__main__":
    # CLI：python3 detect_lang.py
    import sys
    pr = find_project_root(sys.argv[1] if len(sys.argv) > 1 else ".")
    if pr:
        print(json.dumps(detect_languages(pr), ensure_ascii=False))
    else:
        print("[]")
