## Why

`README.md`（310 行，英文）与 `README.zh-CN.md`（293 行，简体中文）是双语镜像，但没有任何门禁守护一致性——MEDIUM #4 评审指出任一版本修改都需手工同步另一版本，实际已发生漂移：英文版有 `## Governance skills (Git & Security) → ### External skill source` 的两层嵌套，中文版是平铺的 `## 外部技能来源`；两份文件的 `Current version` 行都停在 `0.5.4`（实际 0.6.6+）；vendor 快照串都写 `v0.1.0`（`skills.lock.json` 实为 `v0.1.2`）。

## What Changes

- 新增 `tests/test_readme_parity.py`：三条一致性断言（围栏外标题层级序列相等、本地链接目标集合相等、`x.y.z` 版本串集合相等），任一 README 单边修改即 CI 失败。
- `README.zh-CN.md`：插入 `## 治理技能（Git 与安全）` 并把 `外部技能来源` 降级为 `###`，恢复与英文版一致的标题层级序列。
- 双语同步修正（两份文件同 commit）：`Current version` 行 `0.5.4 → 0.6.7`；vendor 快照串 `v0.1.0 → v0.1.2`（与 lock 一致）；在 `### CLI` 段落补一句 `bin/codeguard` 分发器的说明（bash 子命令 → `scripts/*.py` 映射，回应评审 LOW #13）。
- 两份 README 顶部各加一行 parity 说明（指向门禁测试）。
- 文档改名（回应评审 LOW #14）：`docs/5、partme-codeguard-plugin-技术方案与路线.md` → `docs/technical-roadmap.zh_CN.md`（与既有 `...Architecture.zh_CN.md` 命名对齐，消除全角逗号文件名的跨平台转义风险）；同步更新两份 README 的 3 处链接（导航、表格引用、仓库树目录）与文档自身 H1。
- `✅ V0.5.4 verified` 兼容性行**保持不动**——它们记录的是「在 v0.5.4 验证过」的历史事实，未在 0.6.7 重测就不改写。

## Capabilities

### New Capabilities

- `bilingual-docs-consistency`: Defines the parity contract between README.md and README.zh-CN.md and the single-commit mirror-edit rule.

### Modified Capabilities

None.

## Impact

新增 1 个测试（~60 行）；修改两份 README（结构修正 + 4 处同步串 + 2 行说明）；`git mv` 1 个 docs 文件 + 7 处链接更新。无运行时行为变化。