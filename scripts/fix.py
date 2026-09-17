"""fix.py：自动修复所有 linter 问题。

CLI：
    python3 fix.py              # 自动检测并修复所有语言
    python3 fix.py --lang java  # 只修 java
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detect_lang import (  # noqa: E402
    LANG_COMMANDS,
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

    failed = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            continue
        if args.dry_run:
            print(f"  {lang:12s} would run: {' '.join(cmd_def['format'])}")
            continue
        try:
            proc = subprocess.run(
                cmd_def["format"], cwd=project_root, capture_output=True, text=True, timeout=180
            )
        except FileNotFoundError as e:
            print(f"  {lang:12s} \u274c command not found: {e}")
            failed.append(lang)
            continue
        if proc.returncode == 0:
            print(f"  {lang:12s} \u2705 fixed")
        else:
            print(f"  {lang:12s} \u274c failed: exit={proc.returncode}")
            if proc.stderr:
                print(f"     \u2514\u2500 {proc.stderr.strip().splitlines()[-1][:120]}")
            failed.append(lang)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
