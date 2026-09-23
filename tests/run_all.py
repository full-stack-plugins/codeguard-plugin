#!/usr/bin/env python3
"""codeguard 测试集：语言规则结构审计 + 对话级钩子触发模拟 + 报告结构断言。

可按子集单独跑（缺省全跑）：
  python3 tests/run_all.py          # 全量
  python3 tests/run_all.py langs    # 语言注册表结构审计（纯结构，不依赖工具安装）
  python3 tests/run_all.py hooks    # 钩子级模拟（构造临时 git 仓，按宿主协议 stdin JSON 触发）
  python3 tests/run_all.py unit     # 纯函数单测（glob/requiresConfig、{file} 兜底、多 cd 边界、综述≠细节）
  python3 tests/run_all.py cve      # CVE 生态标识、别名归一化与参数校验退出码

钩子模拟的原理 = 完全复刻宿主行为：把 ZCode/Claude 会发给钩子的 JSON payload
通过 stdin 喂给真实钩子脚本，断言退出码与输出协议（exit 0 JSON / exit 2 stderr）。

宿主契约的**单源事实**在 `hooks/__protocol__.md`（exit 码 / JSON 形态 / fail-open /
三端兼容矩阵 / 新增 hook checklist）。任何与本测试断言不一致的脚本改动必须**同
commit**同步更新该文档与 `openspec/specs/hook-protocol/spec.md`。
runtime 用例按工具可用性自动 SKIP（shellcheck 已装则真跑，未装则结构通过）。
"""
from __future__ import annotations

import sys

from _harness import FAIL, PASS, PLUGIN, SKIP
from _subsets import (
    test_cve,
    test_doc_sync,
    test_edges,
    test_field_regressions,
    test_hooks,
    test_languages,
    test_perf,
    test_unit,
)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"codeguard 测试集  plugin={PLUGIN.name}")
    if which in ("all", "langs"):
        test_languages()
    if which in ("all", "hooks"):
        test_hooks()
    if which in ("all", "unit"):
        test_unit()
    if which in ("all", "edges"):
        test_edges()
    if which in ("all", "perf"):
        test_perf()
    if which in ("all", "field"):
        test_field_regressions()
    if which in ("all", "cve"):
        test_cve()
    if which in ("all", "doc"):
        test_doc_sync()
    print(f"\n═══ 结果: {len(PASS)} 通过 / {len(FAIL)} 失败 / {len(SKIP)} 跳过 ═══")
    if FAIL:
        print("失败项:", *FAIL, sep="\n  - ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
