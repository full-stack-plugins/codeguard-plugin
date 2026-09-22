"""scripts/scope.py：linter 命令作用域物化 + git 改动集（delta 门禁共享层）。

从 `detect_lang.py` 独立出来有 spec 依据：`language-gate-commands` 要求
detect_lang 只暴露语言检测与命令表 API，不得混入配置/路径/其它职责。
本模块无反向依赖（不 import detect_lang），职责三件套：

- `ruff_config_args`：项目无自有 ruff 配置时注入 codeguard 默认配置
  （判定可复现性：规则集不能随机器上恰好装的 ruff 漂移；注入文件必须是
  ruff 原生格式，[tool.ruff] 包装的片段会被 TOML 解析拒绝）。
- `scope_cmd`：物化命令——{file} 替换、全仓扫描 token 收敛为文件列表、
  裸命令追加文件、全量模式剔除依赖快照目录。
- `changed_files`：git 仓的本次改动集（staged + 未暂存 + 未跟踪）；
  非 git 目录返回 None（调用方据此退回全量作用域）。

被 hooks/gate_lib、hooks/post_tool_lint、scripts/run_per_language、
scripts/fix 共用；detect_language 的按文件语言归属仍从 detect_lang 取。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# 门禁/CI 全量模式下 ruff 默认剔除的目录（不可编辑的依赖快照与构建产物）。
# 与 hooks/gate_lib.GUARD_EXCLUDE_DIRS 语义重叠但职责不同：那边管"能否入库"，
# 这边管"扫不扫"。vendor 快照是供应链不可变内容，扫它只会得到"永久红"。
_RUFF_FULL_EXCLUDES = (
    ".venv", "venv", "node_modules", "vendor", "upstream", "build", "dist",
    "target", ".tox", "__pycache__",
)
_RUFF_SNIPPET = Path(__file__).resolve().parents[1] / "linters" / "ruff" / "ruff.toml"


def ruff_config_args(cmd: list, project_root: str | Path) -> list:
    """ruff 命令注入 codeguard 默认配置——仅当项目没有自己的 ruff 配置时。

    按 ruff 的配置发现顺序判定：ruff.toml / .ruff.toml / 含 [tool.ruff] 的
    pyproject.toml；存在自有配置则完全不动（项目规则优先）。注入的文件必须是
    ruff 原生格式——指向带 [tool.ruff] 包装的 pyproject 片段会 TOML 解析失败。
    没有这层注入，门禁规则集取决于机器上恰好装了哪个 ruff 及其默认值，
    判定不可复现（实测：无配置环境直接按 I001/EXE001 级规则报错）。
    """
    if not cmd or cmd[0] != "ruff" or not _RUFF_SNIPPET.is_file():
        return []
    root = Path(project_root)
    if (root / "ruff.toml").exists() or (root / ".ruff.toml").exists():
        return []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            if "[tool.ruff]" in pyproject.read_text(encoding="utf-8", errors="ignore"):
                return []
        except OSError:
            pass
    return ["--config", str(_RUFF_SNIPPET)]


def scope_cmd(
    cmd: list,
    project_root: str | Path,
    *,
    files: list[str] | None = None,
    single_file: str | None = None,
    full_excludes: bool = False,
) -> list:
    """物化一条 linter 命令：占位符替换 + 作用域收敛 + ruff 配置注入。

    - `{file}` 占位符 → single_file 路径（PostToolUse 文件型 linter）；
    - 全仓扫描 token（`.`、`**/*.md` 等；`#exclude` 辅助项一并处理）：
      给了 files/single_file 就替换成具体文件列表，没给则保留（全量模式）；
    - 既无占位符也无扫描 token 的裸命令：给了文件就**追加**（yamllint 这类
      不带路径时读 stdin 恒"通过"，追加才检查得到东西）；
    - ruff 命令注入 ruff_config_args 的默认配置；full_excludes=True（全量
      模式）再追加 --exclude，剔除依赖快照与构建产物。
    """
    out = list(cmd)
    if not out:
        return out
    targets = [single_file] if single_file else list(files or [])
    if "{file}" in " ".join(out):
        return [c.replace("{file}", single_file or "") for c in out]
    if out[0] == "ruff":
        args = ruff_config_args(out, project_root)
        out = [out[0]] + args + out[1:]
        if full_excludes:
            for d in _RUFF_FULL_EXCLUDES:
                out += ["--exclude", d]
    scan_idx = [i for i, tok in enumerate(out[1:], 1) if tok == "." or "**" in tok]
    if targets and scan_idx:
        flags = [tok for i, tok in enumerate(out) if i not in scan_idx and not tok.startswith("#")]
        at = min(scan_idx)
        return flags[:at] + targets + flags[at:]
    if targets and not scan_idx:
        return out + targets
    return out


def _git_out(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root, capture_output=True, check=False, text=True, timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _unpushed_files(root: Path) -> list[str]:
    """push 面：相对上游「我这侧」的合并分歧文件（up...HEAD 三点差）。

    无 upstream 时按 origin/<当前分支> → origin/main → origin/master 逐个尝试；
    全部不可解析（如首次推送前的裸仓）返回空——不猜测、不崩（既有
    「push 无 upstream 不崩」行为保持）。
    """
    ranges: list[str] = []
    upstream = _git_out(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream:
        ranges.append(f"{upstream.strip()}...HEAD")
    else:
        branch = _git_out(root, "rev-parse", "--abbrev-ref", "HEAD")
        if branch and branch.strip() not in ("HEAD",):
            ranges.append(f"origin/{branch.strip()}...HEAD")
        ranges += ["origin/main...HEAD", "origin/master...HEAD"]
    for rng in ranges:
        out = _git_out(root, "diff", "--name-only", rng)
        if out is not None:
            return [line for line in out.splitlines() if line.strip()]
    return []


def changed_files(
    project_root: str | Path, *, mode: str = "commit",
) -> list[str] | None:
    """本次改动涉及的文件；非 git 仓返回 None。

    mode="commit"（提交面）：staged + 未暂存 + 未跟踪——"这次要提交什么"。
    mode="push"（推送面）：在提交面基础上**并集未推送提交的文件**
    （up...HEAD）——工作树干净但本地领先时，坏改动已入库、提交面为空，
    推送面必须接管，否则 push 门禁形同虚设（实测：坏提交入史后
    changed_files 返回 []）。排序去重，路径相对仓根。
    """
    root = Path(project_root)
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=root, capture_output=True, check=False, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    names: set[str] = set()
    for args in (
        ("diff", "--cached", "--name-only"),
        ("diff", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        out = _git_out(root, *args)
        if out:
            names.update(line for line in out.splitlines() if line.strip())
    if mode == "push":
        names.update(_unpushed_files(root))
    return sorted(names)
