"""fix.py：自动修复所有 linter 问题。

CLI：
    python3 fix.py              # 自动检测并修复所有语言
    python3 fix.py --lang java  # 只修 java
    python3 fix.py --dry-run    # 只看，不真改

按语言执行细节委托给 `scripts/run_per_language.py`；本文件仅负责
argparse、目标语言过滤、报告输出。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeguard import language_check as run_per_language
from codeguard.config import ConfigurationError
from detect_lang import (
    detect_languages,
    find_project_root,
)
from scope import changed_files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="只修复指定语言")
    parser.add_argument("--dry-run", action="store_true", help="只看，不真改")
    parser.add_argument("--all", action="store_true",
                        help="全仓修复（缺省只修本次改动涉及的文件——一键修复不该重写整个仓库）")
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()

    project_root = find_project_root(args.path) or Path(args.path).resolve()
    try:
        languages = detect_languages(project_root)
    except ConfigurationError as exc:
        print(f"[codeguard] UNVERIFIED: {exc}", file=sys.stderr)
        return 1
    if args.lang:
        languages = [lang for lang in languages if lang == args.lang]

    if not languages:
        print("[codeguard] 未识别到语言")
        return 1

    print(f"[codeguard] project: {project_root}")
    print(f"[codeguard] languages: {languages}  dry-run={args.dry_run}")
    print()

    target_files = None
    if not args.all:
        target_files = changed_files(project_root)
        if target_files is not None:
            if not target_files:
                print("[codeguard] 本次无改动文件，无需修复（--all 可全仓修复）")
                return 0
            print(f"[codeguard] scope: 仅本次改动的 {len(target_files)} 个文件（--all 全仓）")
        # target_files None = 非 git 目录 → 退回全量（无改动概念可依）
    results = run_per_language.run_fix(
        languages, project_root, dry_run=args.dry_run, files=target_files,
    )
    failed: list[str] = []
    for r in results:
        lang = r["language"]
        if r.get("skipped"):
            print(f"  {lang:12s} ⏭️  {r.get('note')}")
            continue
        if r.get("dry_run"):
            print(f"  {lang:12s} would run: {' '.join(r.get('command') or [])}")
            continue
        if r.get("fixed"):
            # 兼容字段 fixed 表示 formatter 以 0 退出，不能证明文件确实改变。
            print(f"  {lang:12s} \u2705 formatter 执行成功（文件变化未验证）")
        else:
            print(f"  {lang:12s} \u274c failed: exit={r.get('exit_code')}")
            if r.get("stderr_tail"):
                last = r["stderr_tail"].strip().splitlines()
                tail = last[-1] if last else ""
                print(f"     \u2514\u2500 {tail[:120]}")
            failed.append(lang)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
