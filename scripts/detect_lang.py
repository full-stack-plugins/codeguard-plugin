"""detect_lang.py：项目语言检测 + linter 命令表（事实源 `scripts/languages.json`）。

实现逻辑（借鉴 codegraph 的统一注册表管线）：
1. **单一事实源** `scripts/languages.json`：每语言一条注册（id/name/extensions/
   markers/lint/format/status/install_hint/since），识别与命令表全部由它构建；
2. **扩展名自动识别，零配置**：内置映射表覆盖全部注册语言；
3. **项目级自定义映射**：项目根 `codeguard.json` 的 `extensions` 可合并/覆盖内置
   默认（如 `{ "extensions": { ".dota_lua": "lua" } }`），`exclude` 数组排除文件模式；
4. **安全降级**：注册表中 lint/format 为 null 的语言（Planned 状态）安全跳过。

职责边界（见 openspec/changes/add-detect-lang-splits）：
- PATH 补齐：`scripts/paths.py::ensure_user_path`
- 用户/项目配置：`scripts/user_config.py::load_user_config / load_project_overrides / get_overrides`
- 本文件 re-export 上述符号以保持外部 API 不变。

被 hooks/、commands/、skills/ 共享。
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

# === 跨职责 re-export（保持外部 API 不变） ===
from paths import ensure_user_path
from user_config import (
    get_overrides,
    load_project_overrides,
    load_user_config,
)

__all__ = [
    "EXT_LANG_MAP",
    "FILE_LANG_MAP",
    "LANG_COMMANDS",
    "LANG_INSTALL_HINTS",
    "LANG_STATUS",
    "PROJECT_MARKERS",
    "REGISTRY",
    "detect_language",
    "detect_languages",
    "ensure_user_path",
    "extract_tool_binaries",
    "find_project_root",
    "get_overrides",
    "load_project_overrides",
    "load_user_config",
    "probe_toolchain",
    "project_uses_linter",
]


REGISTRY_PATH = Path(__file__).resolve().parent / "languages.json"


def _load_registry() -> dict[str, dict[str, Any]]:
    """加载语言注册表：id -> language 定义"""
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {lang["id"]: lang for lang in data["languages"]}


REGISTRY = _load_registry()


# === 派生表（由注册表构建，保持与旧 API 兼容） ===
EXT_LANG_MAP: dict[str, str] = {}
FILE_LANG_MAP: dict[str, str] = {}
PROJECT_MARKERS: dict[str, str] = {}
LANG_COMMANDS: dict[str, dict[str, list[str]]] = {}
LANG_INSTALL_HINTS: dict[str, str] = {}
LANG_STATUS: dict[str, str] = {}

for _id, _lang in REGISTRY.items():
    for _ext in _lang.get("extensions", []):
        EXT_LANG_MAP[_ext.lower()] = _id
    for _fname in _lang.get("file_names", []):
        FILE_LANG_MAP[_fname] = _id
    for _marker in _lang.get("markers", []):
        PROJECT_MARKERS[_marker] = _id
    LANG_STATUS[_id] = _lang.get("status", "planned")
    # 门禁命令表只收 Stable/Beta；Planned 语言安全跳过（命令留作路线图参考）
    if _lang.get("status") in ("stable", "beta"):
        _lint, _fmt = _lang.get("lint"), _lang.get("format")
        if _lint or _fmt:
            LANG_COMMANDS[_id] = {
                "lint": _lint,
                "format": _fmt,
                "gate": _lang.get("gate"),       # 项目级门禁命令（文件型 linter 必须传文件清单）
                "probe": _lang.get("probe"),     # 显式探活命令（npx 系必配，覆盖包未装场景）
                "requiresConfig": _lang.get("requiresConfig"),  # 未接入配置的项目归 skipped
                "install_hint": _lang.get("install_hint"),
                "append_files": _lang.get("append_files", True),
            }
    if _lang.get("install_hint"):
        LANG_INSTALL_HINTS[_id] = _lang["install_hint"]


_TOOL_CACHE: dict[tuple, tuple] = {}

# 运行时依赖：wrapper 命令存在不代表能用（npx 自身是 #!/usr/bin/env node 脚本）
BINARY_DEPENDENCIES = {
    "npx": ["node"],
}

# 管道胶水命令不算 linter 本体（gate 命令形如 find ... | xargs -0 shellcheck）
_PIPE_GLUE = {"find", "xargs", "grep", "sort", "sh", "bash", "echo"}


def extract_tool_binaries(cmd_def: dict) -> list[str]:
    """提取 lint/gate 命令真正依赖的可执行名（展开运行时依赖，去胶水命令）。

    供门禁 pre-flight 探活与 SessionStart 盘点共用。
    """
    bins: set[str] = set()
    for key in ("lint", "gate"):
        cmd = cmd_def.get(key)
        if not cmd:
            continue
        if cmd[0] in ("bash", "sh") and len(cmd) >= 3 and cmd[1] == "-c":
            for segment in cmd[2].split("|"):
                token = segment.strip().split()
                if token and token[0] not in _PIPE_GLUE:
                    bins.add(token[0])
        else:
            bins.add(cmd[0])
    expanded: set[str] = set()
    for b in bins:
        expanded.add(b)
        expanded.update(BINARY_DEPENDENCIES.get(b, []))
    return sorted(b for b in expanded if b)


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
    import fnmatch
    for name in required:
        if any(w in name for w in "*?["):
            if any(fnmatch.fnmatch(p.name, name) for p in root.iterdir()):
                return True
        elif (root / name).exists():
            return True
    return False


def probe_toolchain(cmd_def: dict, timeout: int = 10) -> tuple[bool, str]:
    """pre-flight 探活：验证工具链真的能启动。

    语言可用 `probe` 字段显式指定探活命令（npx 系必配——包未装时
    `--no-install ... --version` 会明确失败，而不是 lint 时才 npm error）；
    缺省对每个必需二进制跑 `--version`。

    进程内缓存（_TOOL_CACHE）：eslint 等被 typescript/vue/svelte/astro 多个
    语言共享，同一进程只真探一次；hooks 进程短生命周期，无需落盘。

    返回 (ok, 失败原因)。失败即工具链问题（运行时缺失/包未装/命令损坏），
    该语言本轮无法检查——归 skipped，绝不能算 lint 失败拦提交。
    """

    def _cached(key: tuple, fn):
        if key not in _TOOL_CACHE:
            _TOOL_CACHE[key] = fn()
        return _TOOL_CACHE[key]

    probe = cmd_def.get("probe")
    if probe:
        return _cached(("probe", tuple(probe)), lambda: _run_probe_cmd(probe, timeout))

    for b in extract_tool_binaries(cmd_def):
        ok, reason = _cached(("bin", b), lambda b=b: _probe_binary(b, timeout))
        if not ok:
            return False, reason
    return True, ""


def _run_probe_cmd(probe: list, timeout: int) -> tuple[bool, str]:
    try:
        # stdin=DEVNULL：探活命令绝不消费宿主 stdin；--format 类探活靠 EOF 立即返回
        proc = subprocess.run(probe, capture_output=True, check=False, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, f"探活超时: {' '.join(probe)}"
    except OSError as exc:
        return False, f"探活无法执行: {exc}"
    if proc.returncode != 0:
        first = next((ln for ln in (proc.stderr or proc.stdout).splitlines() if ln.strip()), "")
        return False, f"探活退出 {proc.returncode}: {first[:100]}"
    return True, ""


def _probe_binary(b: str, timeout: int) -> tuple[bool, str]:
    import shutil
    if shutil.which(b) is None:
        return False, f"{b} 不在 PATH"
    try:
        proc = subprocess.run([b, "--version"], capture_output=True, check=False, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"{b} --version 超时"
    except OSError as exc:
        return False, f"{b} 无法执行: {exc}"
    if proc.returncode != 0:
        first = next((ln for ln in (proc.stderr or proc.stdout).splitlines() if ln.strip()), "")
        return False, f"{b} --version 退出 {proc.returncode}: {first[:100]}"
    return True, ""


# === 项目根 codeguard.json 自定义扩展映射（借鉴 codegraph.json 设计） ===
# 实现已迁至 scripts/user_config.py；re-export 见顶部 import 段。


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


def _excluded(f: Path, exclude_patterns: list[str]) -> bool:
    return any(re.search(pat, str(f)) for pat in exclude_patterns)


def detect_languages(project_root: str | Path) -> list[str]:
    """检测项目根中存在的语言：标记文件 + 常见源码目录浅扫描 + 根目录一层；
    支持 codeguard.json 的 exclude 排除"""
    project_root = Path(project_root)
    overrides = get_overrides(project_root)
    exclude = overrides.get("exclude", [])

    langs: set[str] = set()
    # 1) 标记文件
    for marker, lang in PROJECT_MARKERS.items():
        if (project_root / marker).exists():
            langs.add(lang)
    # 2) 常见源码目录浅扫描（含脚本/二进制/钩子目录：shell 等胶水语言常在这些位置）
    src_dirs = ["src", "src/main", "lib", "pkg", "app", "tests", "test",
                "scripts", "bin", "hooks", "cmd", "internal"]
    for d in src_dirs:
        base = project_root / d
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.is_file() and not _excluded(f, exclude):
                lang = detect_language(f)
                if lang:
                    langs.add(lang)
    # 3) 根目录一层（小脚本项目）
    for f in project_root.iterdir():
        if f.is_file() and not _excluded(f, exclude):
            lang = detect_language(f)
            if lang:
                langs.add(lang)
    return sorted(langs)


if __name__ == "__main__":
    import sys

    pr = find_project_root(sys.argv[1] if len(sys.argv) > 1 else ".")
    if pr:
        print(json.dumps(detect_languages(pr), ensure_ascii=False))
    else:
        print("[]")
