"""项目发现：显式项目根、只读配置与语言索引，不负责工具探活。"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .config import get_overrides
from .path_policy import is_dot_prefixed
from .registry import EXT_LANG_MAP, FILE_LANG_MAP, PROJECT_MARKERS


def project_uses_linter(cmd_def: dict, project_root: str | Path) -> bool:
    """项目是否接入了该语言的 linter（requiresConfig 声明的配置文件任一存在）。

    生态型 linter（如 ESLint 9+）在没有配置文件的项目里必然报错退出——
    那是「未接入」，不是「代码违规」；未接入的语言归 skipped 不拦提交。
    requiresConfig 缺省的语言（自包含工具如 shellcheck/clippy）视为已接入。
    """
    required = cmd_def.get("requiresConfig") if isinstance(cmd_def, dict) else None
    if not required:
        return True
    root = Path(project_root)
    for name in required:
        if any(w in name for w in "*?["):
            if any(fnmatch.fnmatch(p.name, name) for p in root.iterdir()):
                return True
        elif (root / name).exists():
            return True
    return False


def detect_language(file_path: str | Path, project_root: Path | None = None) -> str | None:
    """按扩展名/文件名判断语言；支持 codeguard.json 自定义映射；非代码文件返回 None"""
    p = Path(file_path)
    # 项目根缺省从文件路径推导——钩子调用都不显式传 root，
    # 不推导则 codeguard.json 的自定义扩展映射永远不会生效
    if project_root is None:
        project_root = find_project_root(p)
    overrides = get_overrides(project_root) if project_root else {}
    ext_map = {**EXT_LANG_MAP, **overrides.get("extensions", {})}
    lang = ext_map.get(p.suffix.lower())
    if lang:
        return lang
    # 文件名级识别（Dockerfile 等）
    return FILE_LANG_MAP.get(p.name)


def find_project_root(start: str | Path) -> Path | None:
    """从 start 路径向上找项目根（识别到 .git 或任一项目标记文件即停）"""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    while True:
        if (p / ".git").exists():
            return p
        for marker in PROJECT_MARKERS:
            if (p / marker).exists():
                return p
        if p.parent == p:
            return None
        p = p.parent


def _excluded(f: Path, exclude_patterns: list[str]) -> bool:
    return any(re.search(pat, str(f)) for pat in exclude_patterns)


def detect_languages(project_root: str | Path) -> list[str]:
    """检测项目根中存在的语言：标记文件 + 常见源码目录递归扫描 + 根目录一层；
    支持 codeguard.json 的 exclude 排除"""
    project_root = Path(project_root)
    overrides = get_overrides(project_root)
    exclude = overrides.get("exclude", [])
    ext_map = {**EXT_LANG_MAP, **overrides.get("extensions", {})}

    def include(file: Path) -> None:
        if is_dot_prefixed(file, project_root):
            return  # 点前缀默认忽略（scan-scope-policy）：.eslintrc.js 不计入语言
        if file.is_file() and not _excluded(file, exclude):
            language = ext_map.get(file.suffix.lower()) or FILE_LANG_MAP.get(file.name)
            if language:
                langs.add(language)

    langs: set[str] = set()
    # 1) 标记文件
    for marker, lang in PROJECT_MARKERS.items():
        if (project_root / marker).exists():
            langs.add(lang)
    # 2) 保留递归覆盖，但不重复遍历 src/main，不逐文件重新读取配置或推断根。
    src_dirs = ["src", "lib", "pkg", "app", "tests", "test",
                "scripts", "bin", "hooks", "cmd", "internal"]
    for d in src_dirs:
        base = project_root / d
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            include(f)
    # 3) 根目录一层（小脚本项目）
    for f in project_root.iterdir():
        include(f)
    return sorted(langs)
