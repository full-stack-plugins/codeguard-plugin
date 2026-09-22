"""hooks/gate_lib.py：提交门禁的共享检查逻辑。

被两个钩子复用：
- user_prompt_validator.py（UserPromptSubmit）：失败 → exit 0 + additionalContext 修复指令
- pre_tool_git_guard.py（PreToolUse Bash）：git commit/push 前硬拦截 → exit 2 + stderr 指令

统一行为：通过/跳过 = 静默；失败 = 「问题节选 + 怎么修」结构化输出。
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]   # hooks/ 的上级 = 插件根
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

# maven 依赖解析失败的特征（javadoc:jar 独立 goal 在 reactor 上跑时的典型崩法）
_DEP_RESOLUTION_RE = re.compile(
    r"Could not resolve dependencies|Could not find artifact|DependencyResolutionException"
)

from detect_lang import (
    LANG_COMMANDS,
    detect_language,
    detect_languages,
    get_overrides,
    probe_toolchain,
    project_uses_linter,
)
from scope import changed_files, scope_cmd

# === git 提交内容安全检查：绝不该进版本库的文件 ===
# 目录（路径任一段落匹配即违规）：依赖/虚拟环境/构建产物/IDE/缓存
GUARD_EXCLUDE_DIRS = {
    ".venv", "venv", "env", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "target", "dist", "build", "out", ".next",
    ".nuxt", ".gradle", "vendor", ".idea", ".vscode", "coverage", ".terraform",
    ".tox", ".eggs", "htmlcov", ".turbo", ".parcel-cache",
}
# 文件名模式（fnmatch，任意层级）：密钥/凭据/本地环境/系统垃圾
GUARD_EXCLUDE_FILES = [
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "*.keystore", "id_rsa", "id_ed25519", "id_ecdsa", "*.pem.orig",
    "credentials*.json", "serviceAccount*.json", "*service-account*.json",
    ".DS_Store", "Thumbs.db", "*.pyc",
]
# 仅**仓根级**命中的模式：数据库/日志常作第一方 fixture 合法入库
# （tests/fixtures/sample.db、docs 里的归档 log），只拦散落在根目录的
# 数据转储与调试日志——此前与密钥同池任意层级匹配，误伤合法入库（实测）。
GUARD_ROOT_ONLY_FILES = ["*.sqlite", "*.sqlite3", "*.db", "*.log"]


def _git(project_root: Path, *args: str) -> str | None:
    """跑只读 git 命令；失败（非 git 仓/无 upstream 等）返回 None，由调用方降级"""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=project_root, capture_output=True, check=False, text=True, timeout=15
        )
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def check_commit_safety(project_root: Path, mode: str) -> list[tuple[str, str, str]]:
    """检查即将进入版本库的文件（commit=暂存区；push=未推送提交的 diff）。

    返回违规列表 [(路径, 命中规则, 建议操作)]；无法判定（非 git 仓/无对比基线）
    返回空列表并由调用方按 skipped 处理——安全检查不做静默失败。
    """
    if mode == "commit":
        out = _git(project_root, "diff", "--cached", "--name-only", "-z")
    else:  # push：检查所有未推送提交触及的文件
        out = _git(project_root, "diff", "--name-only", "-z", "@{upstream}..HEAD")
        if out is None:
            out = _git(project_root, "diff", "--name-only", "-z", "origin/main..HEAD")
    if not out:
        return []

    import fnmatch
    violations: list[tuple[str, str, str]] = []
    for raw in out.split("\0"):
        f = raw.strip()
        if not f:
            continue
        parts = f.split("/")
        hit_dir = None
        for idx, seg in enumerate(parts[:-1]):
            if seg not in GUARD_EXCLUDE_DIRS:
                continue
            # vendor 仅**仓根级**=依赖快照；嵌套（scripts/vendor、tools/vendor）
            # 是第一方源码树——裸段匹配曾把 skill_vendor.py 判成"移出版本库"
            # （实测误伤，且打断依赖它的 skills-check CI）。
            if seg == "vendor" and idx != 0:
                continue
            hit_dir = seg
            break
        if hit_dir:
            violations.append((
                f, f"目录 ./{hit_dir}/ 属于依赖/产物/本地环境，不应入库",
                f"git rm -r --cached '{f}' 并在 .gitignore 加 '{hit_dir}/'",
            ))
            continue
        name = parts[-1]
        rule = next((pat for pat in GUARD_EXCLUDE_FILES if fnmatch.fnmatch(name, pat)), None)
        if rule is None and len(parts) == 1:
            # 仓根级 db/log/sqlite 单独一池（见 GUARD_ROOT_ONLY_FILES 注释）
            rule = next(
                (pat for pat in GUARD_ROOT_ONLY_FILES if fnmatch.fnmatch(name, pat)), None
            )
        if rule:
            violations.append((
                f, f"文件命中敏感模式 {rule}（密钥/凭据/本地配置类）",
                f"git rm --cached '{f}' 并在 .gitignore 加 '{rule}'；确认是否已泄露需要轮换密钥",
            ))
    return violations


def format_safety_report(violations: list[tuple[str, str, str]]) -> str:
    lines = [f"codeguard 🛑 提交内容安全检查：{len(violations)} 个文件不应入库", "─" * 60]
    for f, reason, fix in violations:
        lines.append(f"  {f}")
        lines.append(f"     原因: {reason}")
        lines.append(f"     怎么修: {fix}")
        lines.append("-" * 60)
    lines.append("修复后重新暂存再提交（git add 时排除上述文件）")
    return "\n".join(lines)


def _gate_cache_path(project_root: Path) -> Path:
    import hashlib
    import tempfile
    key = hashlib.sha1(str(project_root.resolve()).encode()).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / f"codeguard-gate-{os.getuid()}-{key}.json"


def _worktree_fingerprint(project_root: Path) -> str:
    """工作区指纹：staged + 未暂存 + 未跟踪三路 diff 的内容哈希。

    只用 index mtime 会漏掉"文件已修但未 git add"——键不变 → 60 秒内继续
    报修复前的旧失败（retry-timing 陷阱，实测踩过）。内容哈希一改即失效。
    """
    import hashlib

    h = hashlib.sha1()
    # 注意：("diff") 是字符串不是元组——*unpacking 会拆成字符。单元素必须带逗号。
    for args in (("diff", "--cached"), ("diff",)):
        out = _git(project_root, *args) or ""
        h.update(out.encode("utf-8", "replace"))
    # 未跟踪文件：ls-files 只给文件名——内容改动名字不变，必须叠加 stat 指纹
    others = (_git(project_root, "ls-files", "--others") or "").splitlines()
    for name in sorted(others)[:500]:
        if not name.strip():
            continue
        try:
            st = (project_root / name).stat()
            h.update(f"{name}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8", "replace"))
        except OSError:
            h.update(name.encode("utf-8", "replace"))
    return h.hexdigest()[:16]


def _gate_cache_key(project_root: Path, languages: list, *, mode: str = "commit") -> str | None:
    """缓存键：HEAD + 暂存区指纹 + 工作区内容指纹 + 门禁面（mode）。

    同一 HEAD/工作树下 commit 面与 push 面看到的文件集不同（push 面含未推送
    提交），不带 mode 会互相污染缓存。"""
    head = _git(project_root, "rev-parse", "HEAD")
    if head is None:
        return None
    idx = project_root / ".git" / "index"
    try:
        idx_sig = f"{idx.stat().st_mtime_ns}:{idx.stat().st_size}" if idx.exists() else "no-index"
    except OSError:
        return None
    return (
        f"{head.strip()}|{idx_sig}|{_worktree_fingerprint(project_root)}"
        f"|{mode}|{','.join(sorted(languages))}"
    )


GATE_CACHE_TTL = 60  # 秒：UPS 软门禁与紧随的 PreToolUse 硬门禁之间复用


def run_gate(
    project_root: Path,
    cfg: dict,
    languages: list | None = None,
    *,
    mode: str = "commit",
) -> tuple[list, list]:
    """运行 linter 门禁（跨进程结果缓存 + 并行执行）。

    `languages` 可选：调用方（UserPromptSubmit）可传入用户消息里提到的
    语言子集，门禁只跑该子集；不传则按 `detect_languages()` 全量探测。

    软门禁（UserPromptSubmit）与硬门禁（PreToolUse）在正常提交路径上
    会对同一状态连跑两次全量 lint——缓存键含 HEAD 与暂存区指纹，
    文件未变则 60s 内直接复用；AI 修复并重新暂存后键变化自动失效。

    返回 (failures, skipped)：
    - failures: [(lang, 问题节选, 修复命令, install_hint)]
    - skipped:  [str] 无法验证的说明（工具未装/超时），不阻塞
    """
    import time as _time
    if languages is None:
        languages = detect_languages(project_root)
    if not languages:
        return [], []
    # 作用域：项目可用 codeguard.json gate_scope 覆盖；缺省 = git 仓 delta、
    # 非 git 目录全量。delta 只检查本次改动涉及的文件——存量问题不拦新提交。
    changed = changed_files(project_root, mode=mode)
    scope = (get_overrides(project_root) or {}).get("gate_scope") or (
        "delta" if changed is not None else "repo"
    )
    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    ck = _gate_cache_key(project_root, languages, mode=mode)
    cache_file = _gate_cache_path(project_root)
    if ck:
        try:
            blob = json.loads(cache_file.read_text())
            if blob.get("key") == ck and _time.time() - blob.get("ts", 0) < GATE_CACHE_TTL:
                return blob["failures"], blob["skipped"]
        except (OSError, ValueError, KeyError):
            pass

    failures, skipped = _run_gate_uncached(
        project_root, cfg, languages,
        scope=scope, changed=changed if scope == "delta" else None,
    )

    if ck:
        with contextlib.suppress(OSError):
            cache_file.write_text(json.dumps(
                {"key": ck, "ts": _time.time(), "failures": failures, "skipped": skipped},
                ensure_ascii=False))
    return failures, skipped


def _log_path(project_root: Path, lang: str) -> Path:
    import hashlib
    import tempfile
    key = hashlib.sha1(str(project_root.resolve()).encode()).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / f"codeguard-gate-{key}-{lang}.log"


def _truncate_detail(full: str, project_root: Path, lang: str) -> str:
    """节选 + 总量 + 完整日志路径：截断只留头 600 字符会让 AI 一次修 3 个、
    重试再看 3 个（whack-a-mole）；必须给出"共几行、完整在哪"。"""
    lines = [ln for ln in full.splitlines() if ln.strip()]
    detail = full[:600]
    if len(lines) > 8 or len(full) > 600:
        try:
            path = _log_path(project_root, lang)
            path.write_text(full, encoding="utf-8")
            detail += f"\n…（截断，共 {len(lines)} 行；完整输出: {path}）"
        except OSError:
            detail += f"\n…（截断，共 {len(lines)} 行）"
    return detail


def _run_gate_uncached(
    project_root: Path,
    cfg: dict,
    languages: list,
    *,
    scope: str = "repo",
    changed: list[str] | None = None,
) -> tuple[list, list]:
    """单次门禁（多语言并行，结果顺序保持语言表顺序）。

    scope="delta" 时只检查 changed 里属于该语言的文件（存量问题不拦新提交；
    lint 为 {file} 单文件模式则逐文件循环，上限 50 个，超出回退全量命令）。
    scope="repo" 时按项目级 gate/lint 全量扫（ruff 注入默认配置并剔除依赖
    快照目录——vendor 是供应链不可变内容，扫它只会得到不可修的永久红）。
    """
    from concurrent.futures import ThreadPoolExecutor

    def check(lang: str):
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            return None
        lang_files: list[str] = []
        if scope == "delta":
            lang_files = [
                f for f in (changed or [])
                if detect_language(f, project_root) == lang
            ]
            if not lang_files:
                return (lang, None, f"{lang} 本次改动未涉及，跳过")
        uses_delta_files = bool(lang_files) and len(lang_files) <= 50
        base_cmd = (cmd_def.get("gate") or cmd_def.get("lint")) if (
            scope != "delta" or not uses_delta_files
        ) else cmd_def.get("lint")
        base_cmd = base_cmd or cmd_def.get("gate") or cmd_def.get("lint")
        if not base_cmd:
            return None
        if scope != "delta" and "{file}" in " ".join(base_cmd):
            # {file} 占位符只在文件模式下被替换；门禁拿字面量当文件名跑必然
            # 报"文件不存在"→ 误判成 lint 失败。归跳过。
            return (lang, None, f"{lang} 未配置项目级 gate 命令（lint 为单文件模式），本次未验证")
        timeout = cfg.get("lint_timeout_seconds", 120)
        hint = cmd_def.get("install_hint") or "见 docs/LANGUAGES.md"
        # 「未接入」先于「工具不可用」：requiresConfig 是纯文件系统判定（快、
        # 不起进程），且是更根本的原因——项目没接这个 linter 时，装没装工具
        # 都不该影响结论；反过来会把"未接入"报成"工具不可用"（本机无 yamllint
        # 时既有 yaml 测试即因此失败）。
        if not project_uses_linter(cmd_def, project_root):
            return (lang, None, f"{lang} 项目未接入（缺 linter 配置文件），本次未验证")
        ok, reason = probe_toolchain(cmd_def)
        if not ok:
            return (lang, None, f"{lang} 工具链不可用未验证：{reason}（安装: {hint}）")

        outputs: list[tuple[int, str, str]] = []
        if scope == "delta" and uses_delta_files and "{file}" in " ".join(base_cmd or []):
            for f in lang_files:
                cmd = scope_cmd(base_cmd, project_root, single_file=f)
                outputs.append(_run_one(cmd, timeout, lang, hint))
                if outputs[-1][0] not in (0,):
                    break
        else:
            if scope == "delta":
                # files=None（delta 超 50 文件回退全量命令）时同样要剔除构建产物——
                # 否则回退路径反而比常规全量门禁更容易扫到 target/ 生成物。
                cmd = scope_cmd(
                    base_cmd, project_root,
                    files=lang_files if uses_delta_files else None,
                    full_excludes=not uses_delta_files,
                )
            else:
                cmd = scope_cmd(base_cmd, project_root, full_excludes=True)
            outputs.append(_run_one(cmd, timeout, lang, hint))

        rc, out, err = outputs[0]
        if rc == 124:
            return (lang, None, f"{lang} 检查超时（>{timeout}s），本次未验证")
        if rc == 0:
            return None
        if lang == "markdown":
            return (lang, None, "markdown 风格告警（不阻塞提交）")
        if rc == 127:
            return (lang, None, f"{lang} 工具链异常未验证：命令不存在（exit 127）")
        if rc == 2:
            # exit 2 = 工具用法/依赖/配置崩溃，与仓库内容无关（与 markdownlint
            # 用法错误同族）。按"无法验证≠验证失败"归 skipped，绝不拦提交。
            head = next((ln.strip() for ln in f"{out}\n{err}".splitlines() if ln.strip()), "")
            return (lang, None, f"{lang} 工具链异常未验证：exit 2（非 lint 结论）{('｜' + head[:80]) if head else ''}")
        full = "\n".join(seg for seg in ((out or "").rstrip(), (err or "").rstrip()) if seg)
        detail = _truncate_detail(full or "（linter 无输出）", project_root, lang)
        dep_hint = _dependency_resolution_hint(lang, full)
        if dep_hint:
            detail += f"\n{dep_hint}"
        fix = f"自动修复: {' '.join(cmd_def['format'])}" if cmd_def.get("format") else "按上述问题逐项修复"
        return (lang, (lang, detail, fix, hint), None)

    def _run_one(cmd: list[str], timeout: int, lang: str, hint: str) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                cmd, cwd=project_root, capture_output=True, check=False,
                text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 124, "", f"timeout after {timeout}s"
        except FileNotFoundError:
            return 127, "", f"{lang} linter 未安装（安装: {hint}）"
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    results = []
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(languages)))) as pool:
        results = list(pool.map(check, languages))

    failures, skipped = [], []
    for r in results:              # pool.map 保序，输出与语言表顺序一致
        if r is None:
            continue
        _, failure, skip = r
        if failure:
            failures.append(failure)
        if skip:
            skipped.append(skip)
    return failures, skipped

def skip_gate_via_git_config(project_root: Path) -> bool:
    """仓库级豁免：git config codeguard.skipGate true。

    CODEGUARD_SKIP_GATE 环境变量设在用户 shell，传不进宿主起的 hook 子进程
    （宿主环境独立）；git config 由钩子进程在项目根读取，任何调用形态可用。
    """
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "codeguard.skipGate"],
            cwd=project_root, capture_output=True, check=False, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0 and proc.stdout.strip().lower() in ("true", "1", "yes")


def codeguard_home() -> Path:
    """钩子共享状态目录（可用 CODEGUARD_HOME 覆盖，测试隔离用）。"""
    import os as _os
    return Path(_os.environ.get("CODEGUARD_HOME") or (Path.home() / ".codeguard"))


def session_state_path() -> Path:
    """会话 lint 状态（原先存插件安装目录——升级即清零、双副本各存一半）。"""
    return codeguard_home() / "session_state.json"


def _dependency_resolution_hint(lang: str, full: str) -> str | None:
    """Java 门禁报依赖解析失败时给行动指引，而不是只留 maven 堆栈尾部。

    javadoc:jar 以独立 goal 跑在 reactor 上，sample 类模块常设
    maven.install.skip=true，它们的构件不在本地仓——下游模块必然
    Could not resolve。没有这行提示，用户看到的是与"该改什么"无关的堆栈。
    """
    if lang != "java":
        return None
    if not _DEP_RESOLUTION_RE.search(full):
        return None
    return (
        "提示：依赖构件不可解析（如 samples 模块 maven.install.skip=true 未入本地仓）。"
        "先在仓根执行 mvn install -DskipTests（必要时加 -Dmaven.install.skip=false）再重试门禁。"
    )


def record_skip_event(kind: str, project_root: Path | None = None) -> None:
    """记录一次绕过（skipGate/逃生门）到会话状态，Stop 汇总时可见。

    除计数外保留最近 20 条明细（时间 + 仓库 + 类型）——豁免必须可回溯：
    只有总数时无法回答"哪个仓、什么时候被跳过的"。
    """
    state = {}
    path = session_state_path()
    try:
        if path.exists():
            state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    meta = state.setdefault("_skip", {"count": 0, "kinds": {}})
    meta["count"] = int(meta.get("count", 0)) + 1
    kinds = meta.setdefault("kinds", {})
    kinds[kind] = int(kinds.get(kind, 0)) + 1
    events = meta.setdefault("events", [])
    events.append({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "kind": kind,
        "repo": project_root.name if project_root else None,
    })
    del events[:-20]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def should_suppress_event(key: str, window: float = 2.0) -> bool:
    """事件级双副本去重：同一 key 在窗口内重复触发只执行一次。

    双副本（partme-ai + full-stack-plugins）同时启用时每个钩子事件会跑两遍
    （PostToolUse 有文件级去重，这里给 PreToolUse/UserPromptSubmit 用）。key
    由调用方带 hook 事件 id（tool_use_id/session_id）构造；测试 payload 通常
    不带这些字段——此时调用方不调用本函数，保持旧行为。
    """
    import hashlib
    import time as _time
    path = codeguard_home() / "hook_dedup.json"
    now = _time.monotonic()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        dedup = {}
        if path.exists():
            dedup = json.loads(path.read_text(encoding="utf-8"))
        h = hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()[:24]
        last = dedup.get(h) or {}
        stale = [k for k, v in dedup.items() if now - v.get("ts", 0) > 60]
        for k in stale:
            dedup.pop(k, None)
        if now - last.get("ts", 0) < window:
            dedup[h] = last
            path.write_text(json.dumps(dedup), encoding="utf-8")
            return True
        dedup[h] = {"ts": now}
        path.write_text(json.dumps(dedup), encoding="utf-8")
    except (OSError, ValueError):
        return False
    return False


def summarize_failures(failures: list) -> str:
    """问题综述（一行，用作标题/通知标题）：哪几个生态、什么性质的问题"""
    langs = "、".join(f[0] for f in failures)
    return f"codeguard ❌ 提交门禁未通过：{langs} 共 {len(failures)} 个语言生态有 lint 问题"


def format_failure_report(failures: list) -> str:
    """渲染「综述 + 细节」两段式报告。

    第一行 = 问题综述（宿主 UI 通常取首行作标题）；随后是细节，
    不再重复综述内容——修复"标题和详情一样"的问题。
    """
    lines = [
        summarize_failures(failures),
        "─" * 60,
    ]
    for lang, detail, fix, hint in failures:
        lines.append(f"【{lang}】具体问题：")
        lines.append(detail if detail else "  lint 退出码非零，无文本输出")
        lines.append(f"  ▶ 怎么修: {fix}")
        lines.append(f"  ▶ 未安装工具时先安装: {hint}")
        lines.append("─" * 60)
    lines.append(f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py")
    return "\n".join(lines)


def gate_directive(failures: list) -> str:
    """给 AI 的行动指令：收到后应立即修复并重新提交，而不是询问用户"""
    return (
        format_failure_report(failures)
        + "\n\n"
        + "**给 AI 的强制指令**：提交门禁未通过，禁止执行 git commit / git push。\n"
        + "请立即处理：1) 按上面「怎么修」逐项修复（能自动修复的先跑自动修复命令）；"
        + "2) 纯 lint 类修复可直接继续、不必逐项追问；但凡涉及付费、发布、删除、"
        + "密钥、或跨出本仓的操作，必须先征得用户同意再执行；"
        + "3) 修复完成后重新执行用户要做的提交操作。\n"
        + "确需绕过（仅用户明确要求时）：在该仓库执行 git config codeguard.skipGate true，"
        + "完成后 git config --unset codeguard.skipGate 恢复。环境变量 CODEGUARD_SKIP_GATE "
        + "只对手动直调 run_check 有效（无法传入宿主钩子进程）。\n\n"
        + "**⚠️ 整个工具调用没有执行**：被拦截的是一次包含 git commit/push 的完整 Bash "
        + "调用——其中非 git 的前序步骤（写文件、跑脚本）也全部未运行。请把「修复」与"
        + "「提交」拆成两次独立的工具调用，修完再单独执行提交。"
    )
