"""scripts/validate_languages_json.py：languages.json 的 11 条 schema 与一致性校验。

CLI：
    python3 scripts/validate_languages_json.py                 # 默认路径 scripts/languages.json
    python3 scripts/validate_languages_json.py --path /tmp/foo.json
    python3 scripts/validate_languages_json.py --help

退出码：
    0 = 全部规则通过
    1 = 一条或多条规则失败（输出 N errors 汇总）
    2 = 参数错误（--path 指向不存在的文件 / --help 文本 / argparse 错误）

实现要点：
- 纯函数 check(registry: dict) -> list[str] 返回错误列表；CLI 仅做 IO + 退出码
- 11 条规则按设计稿固定顺序执行；每条失败累加错误；全部规则结束后再统一输出
- 跨语言冲突（extensions / markers）只对 stable/beta 检查，planned 留给路线图
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codeguard.registry_schema import check


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", default="scripts/languages.json",
                        help="path to languages.json (default: scripts/languages.json)")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: --path '{path}' does not exist", file=sys.stderr)
        return 2
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to read/parse {path}: {exc}", file=sys.stderr)
        return 2

    errs = check(reg)
    if errs:
        for err in errs:
            print(f"ERROR: {err}")
        print(f"SUMMARY: {len(errs)} errors", file=sys.stderr)
        return 1
    langs = reg["languages"]
    counts: dict[str, int] = {}
    for lang in langs:
        if isinstance(lang, dict):
            counts[lang.get("status", "unknown")] = counts.get(lang.get("status", "unknown"), 0) + 1
    print(f"INFO: languages.json contains {len(langs)} entries "
          f"({counts.get('stable', 0)} stable, {counts.get('beta', 0)} beta, {counts.get('planned', 0)} planned)")

    print("INFO: 11 schema rules passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
