"""扫描排除与提交路径安全规则的单一来源，无宿主与进程依赖。"""
from __future__ import annotations

import fnmatch
from pathlib import Path

# 构建产物/依赖快照的**单一事实源**——"哪些目录不需要检测"由这里回答。
# 语义边界：gate_lib.GUARD_EXCLUDE_DIRS 管"能否入库"（= 本清单 + IDE 目录，
# 从本清单派生），本清单管"扫不扫"；两侧永不漂移（改这里即两侧同变）。
# 为什么必须完备（两类实测永久红）：target/ 下 maven-javadoc 生成的
# javadoc.sh 让 shell 门禁必红（java 与 shell 两个 gate 步骤互相矛盾）；
# target/site/jacoco 与 target/apidocs 的生成 HTML 让 html 门禁必红——生成物
# 不会被"修复"，下次构建就重写，扫描它们得到的永远是与仓库内容无关的红。
# vendor/upstream 是供应链依赖快照，内容不可编辑，同理只产"永久红"。
# 生效通道必须四条全覆盖（缺一条就漏一类门禁）：
#   1) ruff --exclude（全量）
#   2) find 型 gate 注入 -not -path（-print0/-exec/无 NUL 锚三形态）
#   3) PostToolUse 对产物路径静默跳过（写 target/ 的生成物不检查）
#   4) changed_files 过滤产物路径（force-add 的 target 文件不进 delta 面）
FULL_SCAN_EXCLUDES = (
    ".venv", "venv", "env", "node_modules", "vendor", "upstream",
    "build", "dist", "target", "out", ".next", ".nuxt", ".gradle",
    "coverage", ".terraform", ".tox", ".eggs", "htmlcov", ".turbo",
    ".parcel-cache", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache",
    # Agent/宿主工具工作目录：会话实测 .mimosa/（含源码快照）与 .worktrees/
    # （git 子工作树）曾被 git add -A 带进暂存区——既不该入库，也不该被全量
    # 扫描重复检查（子工作树是同一份源码，扫两遍 = 双份误报）。
    ".mimosa", ".worktrees", ".code-review-graph", ".kimi-code",
    ".zcode", ".codex-plugin", ".agents",
)

# === git 提交内容安全检查：绝不该进版本库的文件 ===

# 目录 = 构建产物/依赖快照**单一事实源**（path_policy.FULL_SCAN_EXCLUDES）+ IDE 目录。
# 从单一来源派生：清单只在本模块改一处，"入库面"与"扫描面"永不漂移
# （此前两份手抄清单已经漂移：扫描面缺 out/.next/coverage 等 14 个目录，
# 入库面缺 upstream）。路径任一段落匹配即违规；vendor 的仓根级特例在
# check_paths 里（嵌套 scripts/vendor 是第一方源码树）。
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


def is_build_artifact(path: str | Path) -> bool:
    """路径是否落在构建产物/依赖快照目录下（任一段命中即算）。

    单一事实源的谓词形态，供 PostToolUse（生成物不检查）与 changed_files
    （产物不进 delta 面）复用同一份认知，避免两处各写一遍目录名。
    注意不能用 lstrip("./")——会把 `.tox` 的点一起剥掉（实测踩点）。
    """
    parts = [seg for seg in str(path).replace("\\", "/").split("/")
             if seg not in ("", ".")]
    return any(seg in FULL_SCAN_EXCLUDES for seg in parts)


def is_dot_prefixed(path: str | Path, root: str | Path | None = None) -> bool:
    """路径相对 root 的任一段以 `.` 开头（`.`/`..` 段除外）→ 点前缀，默认忽略。

    检查面的单一谓词（scan-scope-policy spec）：PostToolUse 保存面、delta 门禁面、
    全量扫描与语言发现都用它跳过点前缀目录与文件（.cursor/、.claude/、
    .eslintrc.js 等——枚举追不上新宿主目录，谓词才是硬约束）。
    例外面由调用方保证：入库安全检查（check_paths）与配置发现不走本谓词。

    root 语义：path 相对 root 判段——项目根本身位于点前缀父目录（~/.config/proj/）
    不算命中（实测陷阱）；root 缺省或 path 不在 root 下时退化为全路径判段。
    不能用 lstrip("./")（会把 `.tox` 的点剥掉，同 is_build_artifact 的踩点）。
    """
    p = Path(path)
    if root is not None:
        try:
            p = p.resolve().relative_to(Path(root).resolve())
        except (ValueError, OSError):
            pass  # root 外或无法解析：全路径判段，宁可多忽略也不错扫宿主目录
    parts = [seg for seg in str(p).replace("\\", "/").split("/")
             if seg not in ("", ".", "..")]
    return any(seg.startswith(".") for seg in parts)


def check_paths(paths: list[str]) -> list[tuple[str, str, str]]:
    """纯路径策略：只判断给定拟入库路径，不发现文件、不读 Git、不执行修复。"""
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
            # 点前缀目录默认忽略（2026-09-23）：.agents/.codex-plugin/.zcode/
            # .github/.claude/ 等是宿主插件清单与第一方配置，必须可入库——
            # 裸段匹配曾把插件仓的 marketplace.json/plugin.json 判成"不应入库"
            # （实测阻断发版）。扫描面本就不扫这些目录（FULL_SCAN_EXCLUDES），
            # 这里只放开"入库面"的目录拦截；密钥类**文件**模式不受影响
            # （.env、*.pem 等仍按 GUARD_EXCLUDE_FILES 拦截）。
            if seg.startswith("."):
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
