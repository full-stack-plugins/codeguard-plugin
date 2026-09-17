"""detect_lang.py：项目语言检测 + 用户配置加载 + linter 命令表。

语言支持与 codegraph（https://github.com/colbymchenry/codegraph#supported-languages）对齐：
扩展名识别覆盖全部 32 种语言；linter 命令覆盖 11 种主流语言（其余随版本路线逐步启用，
见 docs/LANGUAGES.md 的状态列）。

被 hooks/、commands/、skills/ 共享。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# === 文件扩展名 → 语言（与 codegraph supported-languages 对齐，32 种） ===
EXT_LANG_MAP = {
    # TypeScript / JavaScript 生态
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".ets": "arkts",
    # Python
    ".py": "python",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # JVM
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".sc": "scala",
    # .NET
    ".cs": "csharp",
    ".vb": "vbnet",
    # PHP / Ruby
    ".php": "php",
    ".rb": "ruby",
    # C 家族
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".m": "objc",
    ".mm": "objc",
    ".metal": "metal",
    ".cu": "cuda",
    ".cuh": "cuda",
    # Swift / Dart
    ".swift": "swift",
    ".dart": "dart",
    # 前端框架
    ".svelte": "svelte",
    ".vue": "vue",
    ".astro": "astro",
    ".liquid": "liquid",
    # Pascal / Lua / R
    ".pas": "pascal",
    ".dpr": "pascal",
    ".dpk": "pascal",
    ".lpr": "pascal",
    ".lua": "lua",
    ".luau": "luau",
    ".r": "r",
    # 冷门企业语言
    ".cfc": "cfml",
    ".cfm": "cfml",
    ".cfs": "cfml",
    ".cbl": "cobol",
    ".cob": "cobol",
    ".cpy": "cobol",
    ".erl": "erlang",
    ".hrl": "erlang",
    # Web3 / IaC / Nix
    ".sol": "solidity",
    ".tf": "terraform",
    ".tfvars": "terraform",
    ".tofu": "terraform",
    ".nix": "nix",
}


# === 项目标识文件 → 语言（固定文件名，可靠标记） ===
PROJECT_MARKERS = {
    "pom.xml": "java",
    "build.gradle": "java",
    "Cargo.toml": "rust",
    "package.json": "typescript",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "go.mod": "go",
    "composer.json": "php",
    "Gemfile": "ruby",
    "build.sbt": "scala",
    "Package.swift": "swift",
}


# === 每种语言的 linter 命令（lint=检查，format=自动修复） ===
# 未列入的语言处于 planned 状态：钩子检测到后会安全跳过（LANGUAGES.md 状态列）。
LANG_COMMANDS = {
    # ---- Stable（V0.1 起） ----
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
    # ---- Beta（V0.2 起） ----
    "go": {
        "lint": ["go", "vet", "./..."],
        "format": ["gofmt", "-w", "."],
    },
    "csharp": {
        "lint": ["dotnet", "format", "--verify-no-changes"],
        "format": ["dotnet", "format"],
    },
    "kotlin": {
        "lint": ["./gradlew", "detekt"],
        "format": ["./gradlew", "ktlintFormat"],
    },
    "swift": {
        "lint": ["swiftlint"],
        "format": ["swiftlint", "--fix"],
    },
    "php": {
        "lint": ["php", "-l"],
        "format": ["php-cs-fixer", "fix"],
    },
    "ruby": {
        "lint": ["rubocop"],
        "format": ["rubocop", "-A"],
    },
    "scala": {
        "lint": ["scalafmt", "--check"],
        "format": ["scalafmt"],
    },
}

# Beta 语言的辅助说明（写入失败提示，帮助用户安装缺失工具）
LANG_INSTALL_HINTS = {
    "go": "go vet 内置于 Go 工具链；更强的聚合 lint 可安装 golangci-lint",
    "csharp": "需要 .NET SDK 6+（dotnet format 内置）",
    "kotlin": "项目需配置 detekt / ktlint Gradle 插件",
    "swift": "brew install swiftlint",
    "php": "composer require --dev phpstan/phpstan friendsofphp/php-cs-fixer",
    "ruby": "gem install rubocop",
    "scala": "coursier install scalafmt",
}


def detect_language(file_path: str | Path) -> Optional[str]:
    """根据文件扩展名判断语言；非代码文件返回 None"""
    suffix = Path(file_path).suffix.lower()
    return EXT_LANG_MAP.get(suffix)


def find_project_root(start: str | Path) -> Optional[Path]:
    """从 start 路径向上找项目根（识别到 .git 或任一项目标记文件即停）"""
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


def detect_languages(project_root: str | Path) -> list[str]:
    """检测项目根中存在的语言：标记文件 + 常见源码目录浅扫描 + 根目录一层"""
    project_root = Path(project_root)
    langs: set[str] = set()
    # 1) 标记文件
    for marker, lang in PROJECT_MARKERS.items():
        if (project_root / marker).exists():
            langs.add(lang)
    # 2) 常见源码目录浅扫描
    src_dirs = ["src", "src/main", "lib", "pkg", "app", "tests", "test"]
    for d in src_dirs:
        base = project_root / d
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.is_file():
                lang = detect_language(f)
                if lang:
                    langs.add(lang)
    # 3) 根目录一层（小脚本项目）
    for f in project_root.iterdir():
        if f.is_file():
            lang = detect_language(f)
            if lang:
                langs.add(lang)
    return sorted(langs)


def load_user_config() -> dict:
    """从 ~/.zcode/settings.local.yaml 读插件配置（简化版：正则抠块，不依赖 yaml 库）"""
    cfg_path = Path.home() / ".zcode" / "settings.local.yaml"
    defaults = {
        "enabled_languages": [],
        "strict_mode": True,
        "auto_fix_on_save": True,
        "lint_timeout_seconds": 120,
    }
    if not cfg_path.exists():
        return defaults
    try:
        text = cfg_path.read_text()
    except OSError:
        return defaults
    cfg = dict(defaults)
    m = re.search(r"codeguard:\s*(\{.*?\n\})", text, re.DOTALL)
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
        items = [s.strip().strip("\"'") for s in mm.group(1).split(",") if s.strip()]
        cfg["enabled_languages"] = items
    return cfg


if __name__ == "__main__":
    import sys

    pr = find_project_root(sys.argv[1] if len(sys.argv) > 1 else ".")
    if pr:
        print(json.dumps(detect_languages(pr), ensure_ascii=False))
    else:
        print("[]")
