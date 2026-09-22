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
import run_per_language
from detect_lang import (
    detect_languages,
    find_project_root,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="只修复指定语言")
    parser.add_argument("--dry-run", action="store_true", help="只看，不真改")
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()

    project_root = find_project_root(args.path) or Path(args.path).resolve()
    languages = detect_languages(project_root)
    if args.lang:
        languages = [lang for lang in languages if lang == args.lang]

    if not languages:
        print("[codeguard] 未识别到语言")
        return 1

    print(f"[codeguard] project: {project_root}")
    print(f"[codeguard] languages: {languages}  dry-run={args.dry_run}")
    print()

    results = run_per_language.run_fix(
        languages, project_root, dry_run=args.dry_run,
    )
    failed: list[str] = []
    for r, lang in zip(results, languages):
        if r.get("dry_run"):
            print(f"  {lang:12s} would run: {' '.join(r.get('command') or [])}")
            continue
        if r.get("fixed"):
            print(f"  {lang:12s} \u2705 fixed")
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