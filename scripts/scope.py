"""scripts/scope.py：linter 命令作用域物化 + git 改动集（delta 门禁共享层）。

从 `detect_lang.py` 独立出来有 spec 依据：`language-gate-commands` 要求
detect_lang 只暴露语言检测与命令表 API，不得混入配置/路径/其它职责。
本模块无反向依赖（不 import detect_lang），职责三件套：

- `ruff_config_args`：项目无自有 ruff 配置时注入 codeguard 默认配置
  （判定可复现性：规则集不能随机器上恰好装的 ruff 漂移；注入文件必须是
  ruff 原生格式，[tool.ruff] 包装的片段会被 TOML 解析拒绝）。
- `scope_cmd`：物化命令——{file} 替换、全仓扫描 token 收敛为文件列表、
  裸命令追加文件（`append_files=False` 的项目级命令如 mvn 不追加）、
  全量模式剔除依赖快照与构建产物目录（ruff 走 --exclude，
  `find -print0` 型 gate 注入 -not -path）。
- `changed_files`：git 仓的本次改动集；`lanes` 控制取哪几路
  （默认 staged+未暂存+未跟踪三路；硬门禁按命令链推断收窄到实际提交面），
  `extra` 并入显式 git add 路径；非 git 目录返回 None（调用方退回全量作用域）。

被 hooks/gate_lib、hooks/post_tool_lint、scripts/run_per_language、
scripts/fix 共用；detect_language 的按文件语言归属仍从 detect_lang 取。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from codeguard.path_policy import FULL_SCAN_EXCLUDES, is_build_artifact, is_dot_prefixed

__all__ = [
    "DEFAULT_LANES",
    "FULL_SCAN_EXCLUDES",
    "changed_files",
    "child_git_repo_names",
    "is_build_artifact",
    "is_dot_prefixed",
    "is_git_repo",
    "ruff_config_args",
    "scope_cmd",
]


def is_git_repo(root: str | Path) -> bool:
    """路径自身是否为 git 仓（.git 存在）。"""
    return (Path(root) / ".git").exists()


def child_git_repo_names(root: str | Path) -> list[str]:
    """扫描根**不是** git 仓（典型：会话工作区根）时，列出其下自带 .git
    的直接子目录名。

    这些子目录是独立仓库、由它们各自的提交门禁负责；非 git 根的全量扫描
    若把它们一并扫进去，就会出现"提交 A 仓却被 B 仓的存量问题拦截"的
    跨仓误伤（2026-09-23 opencli-java-sdk 会话实测：workspace 根的
    push-all-branches.sh 触发门禁时，根级脚本与子仓文件混在同一份报告里）。
    根级别的散文件（不属于任何子仓）仍保留在扫描面内——它们没有别的门禁。
    """
    out: list[str] = []
    try:
        for child in sorted(Path(root).iterdir()):
            if child.is_dir() and (child / ".git").exists():
                out.append(child.name)
    except OSError:
        pass
    return out


_RUFF_SNIPPET = Path(__file__).resolve().parents[1] / "linters" / "ruff" / "ruff.toml"


def _inject_find_excludes(expr: str, excludes: tuple[str, ...] | list[str] = FULL_SCAN_EXCLUDES) -> str:
    """给 `find …` 型 gate 表达式注入构建产物目录排除（-not -path）。

    覆盖三种实测形态——只认一种就有整族门禁漏网：
    - `find … -print0 | xargs -0 …`（shell/php/sql 等主流）→ 锚在 ` -print0` 前；
    - `find … -exec … {} +`（旧 html gate 形态，曾经因此漏掉 target HTML）→
      锚在 ` -exec` 前；
    - `find . -name … | xargs …`（c/objc/cuda 无 NUL 锚）→ 锚在
      `find <path>` 之后（要求 languages.json 中 -o 组已加括号——否则
      `-not -path … -name a -o -name b` 的 OR 优先级会让排除形同虚设）。
    幂等：已声明同类排除（'*/target/*' 或 '*/target'）的目录不重复注入。
    """
    if "find " not in expr:
        return expr
    # 点前缀默认忽略（scan-scope-policy）：`*/.*` 要求路径含 `/.` 段接点，
    # `./src/x.py` 不命中、`./.cursor/x.py` 与 `./x/.eslintrc.js` 命中
    additions = "" if "'*/.*'" in expr else " -not -path '*/.*'"
    additions += "".join(
        f" -not -path '*/{d}/*'"
        for d in excludes
        if f"'*/{d}/*'" not in expr and f"'*/{d}'" not in expr
    )
    if not additions:
        return expr
    import re as _re
    for anchor in (" -print0", " -exec"):
        if anchor in expr:
            return expr.replace(anchor, additions + anchor, 1)
    m = _re.search(r"find\s+\S+\s+", expr)
    if m:
        return expr[:m.end()] + additions[1:] + " " + expr[m.end():]
    return expr


def _project_python_target(root: Path) -> str | None:
    """读项目声明的 Python 版本，返回 ruff 目标代号（如 py38）；未声明返回 None。

    注入的默认配置硬编码 py310——老项目（3.8/3.9）会被 UP 规则按 3.10 语法
    目标刷屏（假违规）。按 requires-python / .python-version 自适应后，规则
    目标与项目声明一致，判定才可复现于项目自身契约。
    """
    import re as _re
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            m = _re.search(
                r"requires-python\s*=\s*[\"']\s*[~^>=<\s]*(\d+)\.(\d+)",
                pyproject.read_text(encoding="utf-8", errors="ignore"),
            )
            if m:
                return f"py{m.group(1)}{m.group(2)}"
        except OSError:
            pass
    version_file = root / ".python-version"
    if version_file.is_file():
        try:
            m = _re.search(r"(\d+)\.(\d+)", version_file.read_text(encoding="utf-8", errors="ignore"))
            if m:
                return f"py{m.group(1)}{m.group(2)}"
        except OSError:
            pass
    return None


def ruff_config_args(cmd: list, project_root: str | Path) -> list:
    """ruff 命令注入 codeguard 默认配置——仅当项目没有自己的 ruff 配置时。

    按 ruff 的配置发现顺序判定：ruff.toml / .ruff.toml / 含 [tool.ruff] 的
    pyproject.toml；存在自有配置则完全不动（项目规则优先）。注入的文件必须是
    ruff 原生格式——指向带 [tool.ruff] 包装的 pyproject 片段会 TOML 解析失败。
    没有这层注入，门禁规则集取决于机器上恰好装了哪个 ruff 及其默认值，
    判定不可复现（实测：无配置环境直接按 I001/EXE001 级规则报错）。
    项目声明了 Python 版本时追加 --target-version 覆盖注入配置里的 py310。
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
    args = ["--config", str(_RUFF_SNIPPET)]
    target = _project_python_target(root)
    if target:
        args += ["--target-version", target]
    return args


def scope_cmd(
    cmd: list,
    project_root: str | Path,
    *,
    files: list[str] | None = None,
    single_file: str | None = None,
    full_excludes: bool = False,
    append_files: bool = True,
) -> list:
    """物化一条 linter 命令：占位符替换 + 作用域收敛 + ruff 配置注入。

    - `{file}` 占位符 → single_file 路径（PostToolUse 文件型 linter）；
    - 全仓扫描 token（`.`、`**/*.md` 等；`#exclude` 辅助项一并处理）：
      给了 files/single_file 就替换成具体文件列表，没给则保留（全量模式）；
    - 既无占位符也无扫描 token 的裸命令：给了文件就**追加**（yamllint 这类
      不带路径时读 stdin 恒"通过"，追加才检查得到东西）；`append_files=False`
      的项目级命令（mvn/gradle——文件路径会被当 goal 报
      `Unknown lifecycle phase` 误拦）保持原命令，文件列表只决定跑不跑；
    - ruff 命令注入 ruff_config_args 的默认配置；full_excludes=True（全量
      模式）时剔除依赖快照与构建产物：ruff 追加 --exclude，`find -print0`
      型命令（bash -c find … | xargs 形态的 gate）注入 -not -path。
    """
    out = list(cmd)
    if not out:
        return out
    targets = [single_file] if single_file else list(files or [])
    root = Path(project_root)
    # 非 git 根（会话工作区）的全量扫描：排除子 git 仓——它们由各自的
    # 提交门禁负责，混进来就是跨仓误伤（见 child_git_repo_names）。
    scan_excludes = list(FULL_SCAN_EXCLUDES)
    if full_excludes and not is_git_repo(root):
        scan_excludes += child_git_repo_names(root)
    if "{file}" in " ".join(out):
        return [c.replace("{file}", single_file or "") for c in out]
    if out[0] == "ruff":
        args = ruff_config_args(out, project_root)
        out = [out[0]] + args + out[1:]
        if full_excludes:
            for d in scan_excludes:
                out += ["--exclude", d]
            # 点前缀默认忽略（scan-scope-policy）：两种 glob 兜住
            # 「basename 任意层匹配」与「全路径匹配」两种语义读法
            out += ["--exclude", ".*", "--exclude", "**/.*"]
    elif full_excludes and Path(out[0]).name in {"bash", "sh", "dash", "zsh", "ksh"}:
        # 只改 Shell 的命令体；普通 argv/Python -c 中的 "find " 是字面数据，不能注入语法。
        for index in range(1, len(out) - 1):
            flag = out[index]
            if flag.startswith("-") and flag[1:].isalpha() and "c" in flag[1:]:
                out[index + 1] = _inject_find_excludes(out[index + 1], scan_excludes)
                break
    scan_idx = [i for i, tok in enumerate(out[1:], 1) if tok == "." or "**" in tok]
    if targets and scan_idx:
        flags = [tok for i, tok in enumerate(out) if i not in scan_idx and not tok.startswith("#")]
        at = min(scan_idx)
        return flags[:at] + targets + flags[at:]
    if targets and not scan_idx and append_files:
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


_LANE_ARGS = {
    "staged": ("diff", "--cached", "--name-only"),
    "unstaged": ("diff", "--name-only"),
    "untracked": ("ls-files", "--others", "--exclude-standard"),
}
DEFAULT_LANES = ("staged", "unstaged", "untracked")


def changed_files(
    project_root: str | Path, *,
    mode: str = "commit",
    lanes: tuple[str, ...] | list[str] | None = None,
    extra: tuple[str, ...] | list[str] | None = None,
) -> list[str] | None:
    """本次改动涉及的文件；非 git 仓返回 None。

    mode="commit"（提交面）：按 `lanes` 取工作树各路，默认三路 =
    staged + 未暂存 + 未跟踪。**硬门禁按命令链把 lanes 收窄到实际会提交的面**
    （纯 `git commit` 只有暂存区入库；并行会话留在工作树的未暂存 WIP 不属于
    本次提交，曾因此被误拦——收窄逻辑见 pre_tool_git_guard.staging_intent）。
    `extra` = 命令链里 `git add <paths>` 的显式路径（PreToolUse 时 add 尚未
    执行、暂存区还是旧的，不并入会漏掉"即将暂存"的文件）。
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
    for lane in (lanes or DEFAULT_LANES):
        args = _LANE_ARGS.get(lane)
        if not args:
            continue
        out = _git_out(root, *args)
        if out:
            names.update(line for line in out.splitlines() if line.strip())
    for p in (extra or ()):
        if p and not Path(p).is_absolute():
            names.add(p)
    if mode == "push":
        names.update(_unpushed_files(root))
    # 构建产物不进任何面：force-add 进索引的 target 文件、未被 gitignore 的
    # 生成物，对 linter 只是"下次构建就重写"的假红（单一事实源谓词过滤）
    return sorted(n for n in names
                  if not is_build_artifact(n) and not is_dot_prefixed(n, root))
