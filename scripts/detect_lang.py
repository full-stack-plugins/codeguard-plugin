"""detect_lang.py：项目语言检测 + 用户配置加载 + linter 命令表。

实现逻辑（借鉴 codegraph 的统一注册表管线）：
1. **单一事实源** `scripts/languages.json`：每语言一条注册（id/name/extensions/
   markers/lint/format/status/install_hint/since），识别与命令表全部由它构建；
2. **扩展名自动识别，零配置**：内置映射表覆盖全部注册语言；
3. **项目级自定义映射**：项目根 `codeguard.json` 的 `extensions` 可合并/覆盖内置
   默认（如 `{ "extensions": { ".dota_lua": "lua" } }`），`exclude` 数组排除文件模式；
4. **安全降级**：注册表中 lint/format 为 null 的语言（Planned 状态）安全跳过。

被 hooks/、commands/、skills/ 共享。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "languages.json"


def ensure_user_path(from_login_shell: bool = False) -> None:
    """补齐 hook 进程的 PATH。

    ZCode 等桌面宿主以 GUI 方式启动，hook 子进程继承的 PATH 往往缺少
    用户级工具目录（pip --user → ~/.local/bin、cargo → ~/.cargo/bin、
    nvm/fnm 的 node、homebrew），导致已安装的 linter 被误报「未安装」。

    始终补充常见静态目录；from_login_shell=True 时额外从用户登录 shell
    继承完整 PATH（覆盖 nvm 等动态目录，约 100-300ms，只适合低频钩子）。
    """
    static_dirs = [
        "/opt/homebrew/bin", "/usr/local/bin",
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / ".cargo" / "bin"),
        str(Path.home() / "go" / "bin"),
        str(Path.home() / ".local" / "pipx" / "bin"),
    ]
    cur = os.environ.get("PATH", "")
    parts = cur.split(":")
    for d in reversed(static_dirs):
        if Path(d).exists() and d not in parts:
            parts.insert(0, d)
    os.environ["PATH"] = ":".join(parts)

    # node/npx 不可用且静态目录未覆盖时，自动降级登录 shell 继承一次
    # （覆盖 nvm/fnm/Kimi runtime 等非标准 node 安装；约 100-300ms）
    def _node_available() -> bool:
        for d in os.environ.get("PATH", "").split(":"):
            if d and (Path(d) / "node").exists():
                return True
        return False

    if not from_login_shell and not _node_available():
        ensure_user_path(from_login_shell=True)
        return

    if not from_login_shell:
        return
    # 登录 shell 继承结果缓存（跨进程文件，10 分钟 TTL）——
    # 每条含触发词的消息/每次门禁都要补 PATH，不缓存则每次 spawn zsh（100-300ms）
    import time as _time
    cache_file = Path(tempfile.gettempdir()) / f"codeguard-path-cache-{os.getuid()}"
    now = _time.time()
    if cache_file.exists():
        try:
            age = now - cache_file.stat().st_mtime
            cached = cache_file.read_text().strip()
            if age < 600 and ":" in cached:
                os.environ["PATH"] = cached
                return
        except OSError:
            pass
    try:
        shell = os.environ.get("SHELL") or "/bin/zsh"
        proc = subprocess.run(
            [shell, "-lc", "printf '%s' \"$PATH\""],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0:
            inherited = proc.stdout.strip().splitlines()
            if inherited and inherited[-1].count(":") > cur.count(":"):
                os.environ["PATH"] = inherited[-1]
                try:
                    cache_file.write_text(inherited[-1])
                except OSError:
                    pass
    except (OSError, subprocess.SubprocessError):
        pass


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
    import shutil
    import subprocess

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
    import subprocess
    try:
        proc = subprocess.run(probe, capture_output=True, text=True, timeout=timeout)
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
    import subprocess
    if shutil.which(b) is None:
        return False, f"{b} 不在 PATH"
    try:
        proc = subprocess.run([b, "--version"], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"{b} --version 超时"
    except OSError as exc:
        return False, f"{b} 无法执行: {exc}"
    if proc.returncode != 0:
        first = next((ln for ln in (proc.stderr or proc.stdout).splitlines() if ln.strip()), "")
        return False, f"{b} --version 退出 {proc.returncode}: {first[:100]}"
    return True, ""


# === 项目根 codeguard.json 自定义扩展映射（借鉴 codegraph.json 设计） ===
_OVERRIDES_CACHE: dict[str, dict] = {}


def load_project_overrides(project_root: str | Path) -> dict:
    """读取项目根 codeguard.json 的 extensions/exclude 自定义映射"""
    cfg = Path(project_root) / "codeguard.json"
    if not cfg.exists():
        return {}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        "extensions": {k.lower(): v for k, v in (data.get("extensions") or {}).items()},
        "exclude": list(data.get("exclude") or []),
    }


def get_overrides(project_root: str | Path) -> dict:
    key = str(Path(project_root).resolve())
    if key not in _OVERRIDES_CACHE:
        _OVERRIDES_CACHE[key] = load_project_overrides(project_root)
    return _OVERRIDES_CACHE[key]


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
    ext_map = {**EXT_LANG_MAP, **overrides.get("extensions", {})}

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
