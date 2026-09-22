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
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:  # Windows 无 fcntl——锁降级为可选，原子替换仍生效
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

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
from scope import FULL_SCAN_EXCLUDES, changed_files, scope_cmd

# === git 提交内容安全检查：绝不该进版本库的文件 ===
CODEGUARD_VERSION = "0.12.0"

# 目录 = 构建产物/依赖快照**单一事实源**（scope.FULL_SCAN_EXCLUDES）+ IDE 目录。
# 从单一来源派生：清单只在 scope.py 改一处，"入库面"与"扫描面"永不漂移
# （此前两份手抄清单已经漂移：扫描面缺 out/.next/coverage 等 14 个目录，
# 入库面缺 upstream）。路径任一段落匹配即违规；vendor 的仓根级特例在
# check_commit_safety 里（嵌套 scripts/vendor 是第一方源码树）。
GUARD_EXCLUDE_DIRS = set(FULL_SCAN_EXCLUDES) | {".idea", ".vscode"}
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


def check_commit_safety(project_root: Path, mode: str, *, lanes=None, extra=None,
                        pending_commit=False) -> list[tuple[str, str, str]]:
    """检查即将进入版本库的文件（commit=暂存区；push=未推送提交的 diff）。

    返回违规列表 [(路径, 命中规则, 建议操作)]；无法判定（非 git 仓/无对比基线）
    返回空列表并由调用方按 skipped 处理——安全检查不做静默失败。
    """
    from git_snapshot import proposed_paths
    paths = proposed_paths(project_root, mode, lanes=lanes, extra=extra,
                           pending_commit=pending_commit)

    import fnmatch
    violations: list[tuple[str, str, str]] = []
    for raw in paths:
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


def _worktree_fingerprint(project_root: Path, *, max_files: int = 500) -> str:
    """工作区指纹：三路改动的**名字 + stat** 指纹（不再哈希全文内容）。

    只用 index mtime 会漏掉"文件已修但未 git add"——键不变 → 60 秒内继续
    报修复前的旧失败（retry-timing 陷阱，实测踩过），所以工作树改动必须进键。
    此前对 staged+未暂存跑两个**全仓全文 diff** 再 sha1——多工作树大仓上这是
    每次 commit/push 前的固定 MB 级开销。改为：改动文件名单 + 每文件
    size/mtime_ns（staged 部分由 _gate_cache_key 的 index mtime+size 兜底，
    暂存内容变化必动 index）；内容改动不改名不改 size 也会动 mtime_ns
    （纳秒级），既有 CacheKeyTests 语义保持。
    """
    import hashlib

    h = hashlib.sha1()
    for args in (("diff", "--cached", "--name-only"), ("diff", "--name-only")):
        out = _git(project_root, *args) or ""
        names = sorted(line for line in out.splitlines() if line.strip())
        h.update(("\n".join(names)).encode("utf-8", "replace"))
        if args[:2] == ("diff", "--name-only"):
            # 未暂存已跟踪文件：内容改动名字不变，必须叠加 stat 指纹
            # （staged 路不需要——暂存内容变化必动 index，由键内 idx_sig 兜底）。
            # 名字集合不截断：截断会让第 N+1 个文件的修复在缓存窗口内被旧
            # 指纹掩盖（retry-timing 陷阱对大改动面复活）。stat 本身足够便宜。
            for name in names:
                try:
                    st = (project_root / name).stat()
                    h.update(f"{name}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8", "replace"))
                except OSError:
                    h.update(name.encode("utf-8", "replace"))
    # 未跟踪文件：ls-files 只给文件名——内容改动名字不变，必须叠加 stat 指纹
    others = (_git(project_root, "ls-files", "--others") or "").splitlines()
    for name in sorted(n for n in others if n.strip()):
        try:
            st = (project_root / name).stat()
            h.update(f"{name}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8", "replace"))
        except OSError:
            h.update(name.encode("utf-8", "replace"))
        try:
            st = (project_root / name).stat()
            h.update(f"{name}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8", "replace"))
        except OSError:
            h.update(name.encode("utf-8", "replace"))
    return h.hexdigest()[:16]


def _gate_cache_key(
    project_root: Path, languages: list, *,
    mode: str = "commit",
    lanes: tuple[str, ...] | list[str] | None = None,
    extra: tuple[str, ...] | list[str] | None = None,
    scope: str = "delta",
) -> str | None:
    """缓存键：HEAD + 暂存区指纹 + 工作区内容指纹 + 门禁面（mode）+ 文件面（lanes/extra）+ 作用域（scope）。

    同一 HEAD/工作树下 commit 面与 push 面看到的文件集不同（push 面含未推送
    提交），不带 mode 会互相污染缓存。**lanes/extra 必须进键**：纯 `git commit`
    （仅 staged）与 `git add -A && git commit`（三路）在同一工作树状态下看到
    不同文件集——只按工作树指纹，先跑的窄面结果会把宽面查询喂给同一缓存条目
    （staged 干净 + 未暂存有病 → 窄面 pass 被宽面复用 = 绕过）。
    **scope 必须进键**：UPS 软门禁可能按 repo 全量扫（gate_scope 覆盖或非 git
    目录），硬门禁按 delta——同一文件面同一 HEAD 下，repo 全量的存量失败会被
    delta 查询复用，本次改动无关的旧文件就误拦提交（会话实测：UPS 全量扫出的
    .zsh SC1071 被 60s 内的 delta 提交面复用，尽管本次提交没碰任何 .zsh）。
    """
    head = _git(project_root, "rev-parse", "HEAD")
    if head is None:
        return None
    idx = project_root / ".git" / "index"
    try:
        idx_sig = f"{idx.stat().st_mtime_ns}:{idx.stat().st_size}" if idx.exists() else "no-index"
    except OSError:
        return None
    face = ",".join(lanes or ()) + "|" + ",".join(sorted(extra or ()))
    return (
        f"{head.strip()}|{idx_sig}|{_worktree_fingerprint(project_root)}"
        f"|{mode}|{','.join(sorted(languages))}|{face}|{scope}"
    )


GATE_CACHE_TTL = 60  # 秒：UPS 软门禁与紧随的 PreToolUse 硬门禁之间复用


def run_gate(
    project_root: Path,
    cfg: dict,
    languages: list | None = None,
    *,
    mode: str = "commit",
    lanes: tuple[str, ...] | list[str] | None = None,
    extra: tuple[str, ...] | list[str] | None = None,
    exact: bool = False,
    pending_commit: bool = False,
) -> tuple[list, list]:
    """运行 linter 门禁（跨进程结果缓存 + 并行执行）。

    `languages` 可选：调用方（UserPromptSubmit）可传入用户消息里提到的
    语言子集，门禁只跑该子集；不传则按 `detect_languages()` 全量探测。
    `lanes`/`extra`：本次要检查的文件面（见 scope.changed_files）——硬门禁
    （PreToolUse）按命令链传入预测面；不传 = 三路宽口径（软门禁 UPS 无命令
    上下文，按"工作树有待提交改动就提醒"的宽口径注入，不硬拦）。

    软门禁（UserPromptSubmit）与硬门禁（PreToolUse）在正常提交路径上
    会对同一状态连跑两次全量 lint——缓存键含 HEAD 与暂存区指纹，
    文件未变则 60s 内直接复用；AI 修复并重新暂存后键变化自动失效。

    返回 (failures, skipped)：
    - failures: [(lang, 问题节选, 修复命令, install_hint)]
    - skipped:  [str] 无法验证的说明（工具未装/超时），不阻塞
    """
    import time as _time
    if exact:
        from git_snapshot import SnapshotError, validation_tree
        from scope import is_build_artifact
        try:
            with validation_tree(project_root, mode, lanes=lanes, extra=extra,
                                 pending_commit=pending_commit) as (snapshot, paths):
                selected = languages if languages is not None else detect_languages(snapshot)
                enabled = cfg.get("enabled_languages", [])
                if enabled and enabled != ["auto"]:
                    selected = [lang for lang in selected if lang in enabled]
                requested_scope = (get_overrides(snapshot) or {}).get("gate_scope") or "delta"
                return _run_gate_uncached(snapshot, cfg, selected, scope=requested_scope,
                                          changed=[p for p in paths if not is_build_artifact(p)])
        except (SnapshotError, OSError, ValueError) as exc:
            return [], [f"git UNVERIFIED：无法验证准确内容快照：{exc}"]
    if languages is None:
        languages = detect_languages(project_root)
    if not languages:
        return [], []
    # 作用域：项目可用 codeguard.json gate_scope 覆盖；缺省 = git 仓 delta、
    # 非 git 目录全量。delta 只检查本次改动涉及的文件——存量问题不拦新提交。
    changed = changed_files(project_root, mode=mode, lanes=lanes, extra=extra)
    scope = (get_overrides(project_root) or {}).get("gate_scope") or (
        "delta" if changed is not None else "repo"
    )
    enabled = cfg.get("enabled_languages", [])
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]

    ck = _gate_cache_key(project_root, languages, mode=mode, lanes=lanes, extra=extra,
                         scope=scope)
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
        baseline_ref="@{upstream}" if mode == "push" else "HEAD",
    )

    if ck:
        with contextlib.suppress(OSError):
            # 原子替换：UPS 与 PreToolUse 并发写同一 cache 文件时，
            # 裸 write_text 可能让对方读到半截 JSON（ValueError → 缓存失效重扫）。
            tmp = cache_file.with_name(f"{cache_file.name}.{os.getpid()}.tmp")
            tmp.write_text(json.dumps(
                {"key": ck, "ts": _time.time(), "failures": failures, "skipped": skipped},
                ensure_ascii=False))
            os.replace(tmp, cache_file)
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


def _mentioned_files(full: str, project_root: Path) -> set[str]:
    """从 linter 输出提取"提到的、且在仓内真实存在的"文件（仓根相对路径）。

    两类通行格式：`path/file.ext:12:`（javadoc/ruff/pylint/mvn——绝对路径先剥
    仓根前缀）与 `In path/file.ext line 12`（shellcheck）。只收 root 下真实
    存在的路径——裸 token（`version:1`）被存在性过滤挡掉。
    """
    import re
    root = Path(project_root)
    found: set[str] = set()
    pats = (
        # path/file.ext:12:（javadoc 绝对路径 / ruff / mvn）——目录前缀可选：
        # ruff 在仓根输出裸文件名 `old.py:1:1:`，强制含 / 会漏归因（实测）。
        # 无点的裸 token（SC2086:1 / version:1）不会命中；命中的再过存在性。
        re.compile(r"((?:[A-Za-z]:)?(?:/?(?:[\w.\-]+/)*)[\w.\-]+\.[A-Za-z0-9]+):\d+"),
        re.compile(r"\bIn ((?:[\w.\-]+/)+[\w.\-]+\.[A-Za-z0-9]+) line \d+"),
    )
    for pat in pats:
        for m in pat.findall(full):
            p = m
            root_s = str(root)
            if p.startswith(root_s + "/"):
                p = p[len(root_s) + 1:]
            p = p.lstrip("./")
            if p.startswith("/"):
                continue  # 仓外绝对路径不归因
            if (root / p).exists():
                found.add(p)
    return found


def _stale_attribution(full: str, project_root: Path, lang: str, lang_files: list[str]) -> str | None:
    """[已弃用·保留接口] delta 失败路径下的"历史债"弱归因。

    verdict-integrity 原则：**真正的豁免必须有基线复跑证据**（双跑
    baseline_stale_finding）——本函数对此**永远不豁免**，遵循"宁可误拦
    不误放行"：只靠失败文件是否在改动集推断存量债是危险的（同名文件被
    替换时也会"不在改动集"，但其实是新债），必须有 baseline_ref 上同
    命令同工具的实际复跑才能豁免。

    历史与契约：
    - 入口仍保留以兼容 tests/test_verdict_integrity.py 与 test_session_fixes
      中的调用；这些测试断言本函数返回 None（不豁免），本实现亦满足。
    - 真正的豁免路径在 baseline_stale_finding（hook_lib.py 行 ~430+），
      由 _run_gate_uncached 在 delta 逐文件失败循环里调用。
    - 如未来加入"按文件位置启发式豁免"，本函数将是扩展点：补基线 fallback
      或与 baseline_stale_finding 双签名比对。

    本函数当前实现永远返回 None。
    """
    return None


def _run_gate_uncached(
    project_root: Path,
    cfg: dict,
    languages: list,
    *,
    scope: str = "repo",
    changed: list[str] | None = None,
    baseline_ref: str = "HEAD",
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
            return (lang, None, f"{lang} PLANNED：没有可执行检查命令")
        if lang == "java":
            from run_per_language import run_check
            outcome = run_check([lang], project_root, timeout=cfg.get("lint_timeout_seconds", 120),
                                files=changed if scope == "delta" else None,
                                log_dir=_log_path(project_root, lang).with_suffix(""))[0]
            if outcome["status"] == "PASS":
                return None
            if outcome["status"] != "FAIL":
                return (lang, None, f"java {outcome['status']}: {outcome['reason']}")
            detail = _truncate_detail(outcome.get("stdout_tail", "") + outcome.get("stderr_tail", ""), project_root, lang)
            if outcome.get("log_path"):
                detail += f"\n完整输出: {outcome['log_path']}"
            return (lang, (lang, detail, "按 Java 影响计划修复并复跑 verify/check",
                           "无需安装工具；用项目自带 mvnw/gradlew 与匹配 JDK 复跑"), None)
        lang_files: list[str] = []
        if scope == "delta":
            lang_files = [
                f for f in (changed or [])
                if detect_language(f, project_root) == lang and (project_root / f).is_file()
            ]
            # ShellCheck 不支持 zsh（SC1071 是 error 级固有限制）——.zsh 送检
            # 必红且不是代码违规。从目标面剔除并明示"未验证"，不静默丢弃。
            if lang == "shell":
                zsh_files = [f for f in lang_files if f.endswith(".zsh")]
                if zsh_files:
                    lang_files = [f for f in lang_files if not f.endswith(".zsh")]
                    if not lang_files:
                        return (lang, None,
                                f"shell {len(zsh_files)} 个 zsh 文件未验证（ShellCheck 不支持 zsh）")
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

        # Java 门禁接入 java_project 分析：mvnw 感知 + 工具链失配归跳过。
        if lang == "java":
            try:
                from java_project import analyze as _jp_analyze
                _jp = _jp_analyze(str(project_root))
                if _jp.get("status") == "UNVERIFIED":
                    return (lang, None,
                            (f"{lang} 项目分析 UNVERIFIED（{_jp.get('build_system', '?')}），"
                             f"原因: {'; '.join(_jp.get('reasons', []))}，本次未验证"))
                exe = _jp.get("executable")
                if exe and base_cmd and base_cmd[0] in ("mvn", "gradle"):
                    base_cmd = [exe] + base_cmd[1:]
            except Exception as exc:  # noqa: BLE001 — 分析失败不阻塞门禁，走原路径
                print(f"[codeguard] java_project 分析失败（走原路径）: {exc!r}",
                      file=sys.stderr)
                record_gate_decision(project_root, lang, base_cmd, -1,
                                     "UNVERIFIED", f"java_project 分析失败: {exc!r}")

        outputs: list[tuple[int, str, str]] = []
        stale_notes: list[str] = []
        # 项目级命令（mvn/gradle 等，无 {file} 占位符）不追加文件路径——
        # 文件被当 goal 会报 `Unknown lifecycle phase` 造成假失败；文件列表
        # 只用来决定跑不跑（delta 上面已按语言过滤）。
        append = cmd_def.get("append_files", True)
        if scope == "delta" and uses_delta_files and "{file}" in " ".join(base_cmd or []):
            for f in lang_files:
                cmd = scope_cmd(base_cmd, project_root, single_file=f)
                rc_f, out_f, err_f = _run_one(cmd, timeout, lang, hint)
                if rc_f == 0:
                    outputs.append((rc_f, out_f, err_f))
                    continue
                # 失败先做双跑基线：HEAD 版本同命令同工具已有相同发现 → 存量
                # 豁免（本次未引入新问题）；否则按新增违规拦截。exact 快照目录
                # 非 git 仓，git show 失败 → 不豁免（宁可误拦不误放行）。
                stale = baseline_stale_finding(
                    project_root, f, base_cmd, (out_f or "") + (err_f or ""), timeout,
                    baseline_ref=baseline_ref)
                if stale is not None:
                    stale_notes.append(f"{f}: {stale}")
                    continue
                outputs.append((rc_f, out_f, err_f))
                break
        else:
            if scope == "delta":
                # files=None（delta 超 50 文件回退全量命令）时同样要剔除构建产物——
                # 否则回退路径反而比常规全量门禁更容易扫到 target/ 生成物。
                cmd = scope_cmd(
                    base_cmd, project_root,
                    files=lang_files if uses_delta_files else None,
                    full_excludes=not uses_delta_files,
                    append_files=append,
                )
            else:
                cmd = scope_cmd(base_cmd, project_root, full_excludes=True)
            outputs.append(_run_one(cmd, timeout, lang, hint))

        # 任一后续文件失败都不能被首个文件的成功覆盖。
        if not outputs:
            # 所有失败项都比对为存量 → 放行，但必须明示豁免内容
            record_gate_decision(project_root, lang, base_cmd, 0, "PASS", "存量问题豁免（基线比对）")
            return (lang, None, f"{lang} 存量问题已豁免（基线同命令同工具比对）："
                                + "；".join(stale_notes[:3]))
        rc, out, err = next((entry for entry in outputs if entry[0] != 0), outputs[0])
        if rc == 0:
            record_gate_decision(project_root, lang, base_cmd, 0, "PASS", "检查执行成功")
            if stale_notes:
                return (lang, None, f"{lang} 存量问题已豁免（基线比对）："
                                    + "；".join(stale_notes[:3]))
            return None
        from verdict import UNVERIFIED, lint_verdict
        status, reason = lint_verdict(rc, base_cmd, out + err)
        if status == UNVERIFIED:
            record_gate_decision(project_root, lang, base_cmd, rc, "UNVERIFIED", reason)
            return (lang, None, f"{lang} 工具链异常未验证：{reason} (exit {rc})")
        if lang == "markdown":
            record_gate_decision(project_root, lang, base_cmd, rc, "SKIPPED", "markdown 风格告警")
            return (lang, None, "markdown 风格告警（不阻塞提交）")
        full = "\n".join(seg for seg in ((out or "").rstrip(), (err or "").rstrip()) if seg)
        if scope == "delta" and lang_files:
            # 无基线时不做“历史债”推断；保留接口供未来双跑基线扩展。
            stale = _stale_attribution(full, project_root, lang, lang_files)
            if stale is not None:
                return (lang, None, stale)
        detail = _truncate_detail(full or "（linter 无输出）", project_root, lang)
        dep_hint = _dependency_resolution_hint(lang, full)
        if dep_hint:
            detail += f"\n{dep_hint}"
        fix = f"自动修复: {' '.join(cmd_def['format'])}" if cmd_def.get("format") else "按上述问题逐项修复"
        record_gate_decision(project_root, lang, base_cmd, rc, "FAIL", "检查发现违规")
        return (lang, (lang, detail, fix, hint), None)

    def _run_one(cmd: list[str], timeout: int, lang: str, hint: str) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                cmd, cwd=project_root, capture_output=True, check=False,
                text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            # 超时 = 不可证伪，路由到 skipped 而非 failures。上游 run_gate 把
            # timeout 当失败会把 Maven install -DskipTests 冷缓存（普遍 >2 分钟）
            # 误报为阻断；报告 skip + 指引加长 timeout，不阻塞硬门禁。
            return 124, "", f"timeout after {timeout}s"
        except FileNotFoundError:
            return 127, "", f"{lang} linter 未安装（安装: {hint}）"
        # exit 124 = subprocess 自身用 124 报 timeout（与上面的 TimeoutExpired
        # 区分：后者是 _run_one 自身超时，subprocess.run 不抛），同样不可证伪。
        if proc.returncode == 124:
            return 124, proc.stdout or "", f"subprocess timeout after {timeout}s"
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
    # OpenSpec validate：项目使用 OpenSpec 管理 change proposal 时，跨语言 lint
    # 通过后再核验 openspec/changes/* 是否仍合法（DRAFT/REVIEW_REQUIRED 提案
    # 实施时此步提醒 agent 评审未通过）。OpenSpec 未安装或项目无 config 时跳过。
    try:
        openspec_check = _openspec_validate(
            project_root, timeout_seconds=cfg.get("lint_timeout_seconds", 300))
        failures.extend(openspec_check["failures"])
        if openspec_check["skipped"]:
            skipped.append(openspec_check["skipped"])
    except Exception as exc:  # noqa: BLE001 — 调用面异常同样归"未验证"，不静默吞
        skipped.append(f"openspec UNVERIFIED：{exc!r}")
    return failures, skipped


def _openspec_validate(project_root: Path, timeout_seconds: int = 300) -> dict:
    """若仓根有 openspec/config.yaml 且 openspec CLI 可用，跑 strict validate。

    报告：failures=[("openspec", detail, 修复命令, install_hint), ...]
          skipped="…" 或 None（无 openspec 项目或 CLI 缺失时）。
    """
    cfg_path = project_root / "openspec" / "config.yaml"
    if not cfg_path.is_file():
        return {"failures": [], "skipped": None}
    cli = shutil.which("openspec")
    if cli is None:
        return {"failures": [], "skipped": "openspec CLI 未安装，跳过验证"}
    try:
        proc = subprocess.run(
            [cli, "validate", "--all", "--strict", "--no-interactive", "--json"],
            cwd=project_root, capture_output=True, text=True,
            check=False, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"failures": [], "skipped": "openspec validate 超时（lint_timeout_seconds）"}
    except Exception as exc:  # noqa: BLE001 — validate 自身异常归"未验证"，绝不逃逸成 fail-open 静默吞
        return {"failures": [], "skipped": f"openspec validate 异常未验证: {exc!r}"}
    if proc.returncode == 0:
        return {"failures": [], "skipped": None}
    detail = _truncate_detail((proc.stdout or "") + (proc.stderr or ""), project_root, "openspec")
    fix = f"{cli} validate --all --strict --no-interactive"
    hint = "见 https://openspec.dev 或 `npm i -g @fission-ai/openspec`"
    return {"failures": [("openspec", detail, fix, hint)], "skipped": None}

def skip_gate_via_git_config(project_root: Path) -> bool:
    """仓库级豁免：git config codeguard.skipGate true。

    CODEGUARD_SKIP_GATE 环境变量设在用户 shell，传不进宿主起的 hook 子进程
    （宿主环境独立）；git config 由钩子进程在项目根读取，任何调用形态可用。

    读取失败（超时/OSError）**不静默**：低超时（3s）重试一次后仍失败才按
    "未豁免"处理，并记 skipGate-read-error 审计事件——门禁误拦 vs 误放行之间
    宁可误拦，但必须留痕可排障（此前 timeout=10s 静默 False，门禁满负载时
    高概率误判"没豁免"且无痕迹）。
    """
    last_exc: Exception | None = None
    for _attempt in (1, 2):
        try:
            proc = subprocess.run(
                ["git", "config", "--get", "codeguard.skipGate"],
                cwd=project_root, capture_output=True, check=False, text=True, timeout=3,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            last_exc = exc
            continue
        return proc.returncode == 0 and proc.stdout.strip().lower() in ("true", "1", "yes")
    record_skip_event("skipGate-read-error", project_root)
    with contextlib.suppress(OSError, ValueError):
        path = session_state_path()
        state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        events = state.get("_skip", {}).get("events", [])
        if events:
            events[-1]["detail"] = f"git config 读取失败(重试2次): {last_exc!r}"
            path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return False


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


def baseline_stale_finding(
    project_root: Path, rel_path: str, base_cmd: list[str], output: str, timeout: int = 60,
    *,
    baseline_ref: str = "HEAD",
) -> str | None:
    """同命令同工具跑**改动前版本**：基线已存在相同发现 → 存量豁免说明；否则 None。

    verdict-integrity 既有原则：**无基线证据绝不豁免**（`_stale_attribution` 因
    此恒返回 None）。本函数首次落地"双跑基线"：把 baseline_ref:<path> 的内容
    写到临时文件、用同一条 linter 命令跑一遍，两次输出各取 finding_signatures；
    新发现 ⊆ 基线发现 → 全是存量（本次改动未引入新问题）；基线为空/提不出
    签名/基线跑不起来 → 一律不豁免，宁可误拦不误放行。

    baseline_ref 必须是"改动前"：commit 面（工作树/暂存改动）用 HEAD；push 面
    （检查未推送提交）必须用 @{upstream}——坏提交已经进了 HEAD，拿 HEAD 当基线
    会把本次新引入的坏内容误判成存量（实测踩过：push 面坏提交被豁免放行）。
    """
    from verdict import finding_signatures
    pre = _git(project_root, "show", f"{baseline_ref}:{rel_path}")
    if pre is None:
        return None
    new_sigs = finding_signatures(output)
    if not new_sigs:
        return None
    import tempfile as _tf
    with _tf.TemporaryDirectory(prefix="cg-baseline-") as td:
        tmp = Path(td) / ("baseline" + (Path(rel_path).suffix or ".txt"))
        try:
            tmp.write_text(pre, encoding="utf-8", errors="replace")
        except OSError:
            return None
        joined = " ".join(base_cmd)
        cmd = ([c.replace("{file}", str(tmp)) for c in base_cmd] if "{file}" in joined
               else list(base_cmd) + [str(tmp)])
        try:
            proc = subprocess.run(
                cmd, cwd=project_root, capture_output=True, check=False,
                text=True, timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            return None
        base_sigs = finding_signatures((proc.stdout or "") + (proc.stderr or ""))
    if not base_sigs:
        return None
    return "存量问题（基线同命令同工具已存在）" if new_sigs <= base_sigs else None


def record_gate_decision(project_root: Path, lang: str, cmd: list[str], rc: int,
                         status: str, reason: str, limit: int = 500) -> None:
    """门禁决策落盘（gate-decisions.jsonl）：哪个语言、跑了什么命令、rc、结论。

    只有 skip 事件有明细时，事后无法回答"这个仓这次提交门禁为什么放行/拦截"
    ——决策日志是排障与回归对比的证据链。写失败不影响门禁主流程。
    """
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo": project_root.name,
        "lang": lang,
        "cmd": list(cmd),
        "rc": rc,
        "status": status,
        "reason": reason,
    }
    with contextlib.suppress(OSError):
        path = codeguard_home() / "gate-decisions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
        lines.append(json.dumps(entry, ensure_ascii=False))
        path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")


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
    now = _time.time()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # 并发安全：UPS 与 PreToolUse 两条钩子在数秒窗口内先后读写本文件，
        # 裸 read-modify-write 会互相覆盖（丢抑制事件 → 双份报告）或读到半截
        # JSON（ValueError → 去重静默失效）。进程锁 + tmp+replace 原子替换。
        # 时间戳用墙钟：monotonic 跨重启回绕，持久化文件不能存。
        lock_path = path.with_name(path.name + ".lock")
        with open(lock_path, "w") as lock:
            if fcntl:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            dedup = {}
            if path.exists():
                dedup = json.loads(path.read_text(encoding="utf-8"))
            h = hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()[:24]
            last = dedup.get(h) or {}
            stale = [k for k, v in dedup.items() if now - v.get("ts", 0) > 60]
            for k in stale:
                dedup.pop(k, None)
            suppress = now - last.get("ts", 0) < window
            dedup[h] = {"ts": last.get("ts", now)} if suppress else {"ts": now}
            tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
            tmp.write_text(json.dumps(dedup), encoding="utf-8")
            os.replace(tmp, path)
        return suppress
    except (OSError, ValueError):
        return False


def summarize_failures(failures: list) -> str:
    """问题综述（一行，用作标题/通知标题）：哪几个生态、什么性质的问题"""
    langs = "、".join(f[0] for f in failures)
    return f"codeguard ❌ 提交门禁未通过：{langs} 共 {len(failures)} 个语言生态有 lint 问题"


REPORT_MAX_CHARS = 3000  # gate_directive 总长硬上限：宿主会把超长 stderr 从尾部
                         # 截断，指令段曾因此整体丢失（实测报告只见到首段报错）


def _squeeze(text: str, budget: int) -> str:
    """保头保尾截断：尾部含「完整输出: /tmp/…」日志路径，砍中段也不能丢。"""
    if len(text) <= budget:
        return text
    keep_tail = min(150, budget // 3)
    keep_head = max(0, budget - keep_tail - 10)
    return text[:keep_head] + "\n……（中略）……" + text[-keep_tail:]


def _failure_detail_blocks(failures: list, *, fix_first: bool = False) -> list[str]:
    """每个语言的细节块。fix_first=True 把「怎么修/安装」排在长 detail 之前——
    报告被宿主截断时，行动指引必须比 linter 原始输出先存活下来。"""
    blocks: list[str] = []
    for lang, detail, fix, hint in failures:
        block = [f"【{lang}】具体问题："]
        tail = [
            f"  ▶ 怎么修: {fix}",
            f"  ▶ 未安装工具时先安装: {hint}",
        ]
        body = detail if detail else "  lint 退出码非零，无文本输出"
        if fix_first:
            block += tail + [body]
        else:
            block += [body] + tail
        block.append("─" * 60)
        blocks.append("\n".join(block))
    return blocks


def format_failure_report(failures: list) -> str:
    """渲染「综述 + 细节」两段式报告（CLI/调试面）。

    第一行 = 问题综述（宿主 UI 通常取首行作标题）；随后是细节，
    不再重复综述内容——修复"标题和详情一样"的问题。
    """
    lines = [
        summarize_failures(failures),
        "─" * 60,
    ]
    lines.extend(_failure_detail_blocks(failures))
    lines.append(f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py")
    return "\n".join(lines)


def gate_directive(failures: list) -> str:
    """给 AI 的行动指令：收到后应立即修复并重新提交，而不是询问用户。

    结构 = 综述（首行契约）→ 强制指令（前置！）→ 每语言细节（fix 先于
    detail）→ 修复入口；整体压到 REPORT_MAX_CHARS 内。指令必须前置：宿主把
    超长 stderr 从尾部截断，此前指令在报告末段，长报告下 AI 只看到首段 linter
    报错、「拆两次调用」与 skipGate 逃生门全部丢失（实测）。首行仍为综述、
    综述不重复、含「具体问题」——run_all/硬门禁契约保持。
    """
    header = [
        summarize_failures(failures),
        f"codeguard v{CODEGUARD_VERSION}",
        "─" * 60,
        "**给 AI 的强制指令**：提交门禁未通过，禁止执行 git commit / git push。\n"
        + "**⚠️ 整个工具调用没有执行**：被拦截的是一次包含 git commit/push 的完整 Bash "
        "调用——其中非 git 的前序步骤（写文件、跑脚本）也全部未运行。请把「修复」与"
        "「提交」拆成两次独立的工具调用，修完再单独执行提交。\n"
        + "**⚠️ 如果报错涉及 target/、dist/、build/ 下的构建产物**：请先单独"
        "运行清理命令（如 `rm -rf target/reports`，不含 git commit/push），"
        "清理完成后再重试提交——本门禁在命令执行前拦截，此前命令链中的清理"
        "步骤不会被执行。\n"
        + "请立即处理：1) 按下面「怎么修」逐项修复（能自动修复的先跑自动修复命令）；"
        "2) 纯 lint 类修复可直接继续、不必逐项追问；但凡涉及付费、发布、删除、"
        "密钥、或跨出本仓的操作，必须先征得用户同意再执行；"
        "3) 修复完成后重新执行用户要做的提交操作。\n"
        + "确需绕过（仅用户明确要求时）：**单次豁免**用 `git -c codeguard.skipGate=true commit …`"
        "（不落配置、无残留，推荐）；**仓库级豁免**在该仓库执行 git config codeguard.skipGate true，"
        "完成后 git config --unset codeguard.skipGate 恢复。环境变量 CODEGUARD_SKIP_GATE "
        "只对手动直调 run_check 有效（无法传入宿主钩子进程）。两种豁免都会记入会话审计明细。",
        "─" * 60,
    ]
    footer = f"一键尝试自动修复: python3 {PLUGIN_ROOT}/scripts/fix.py"
    head = "\n".join(header)
    budget = max(400, REPORT_MAX_CHARS - len(head) - len(footer) - 64)
    blocks = _failure_detail_blocks(failures, fix_first=True)
    used, kept = 0, []
    for block in blocks:
        remain = budget - used
        if remain <= 0:
            kept.append("…（其余语言的问题明细已省略，按上方怎么修逐语言处理）")
            break
        if len(block) > remain:
            block = _squeeze(block, remain)
        kept.append(block)
        used += len(block) + 1
    return "\n".join([head, *kept, footer])
