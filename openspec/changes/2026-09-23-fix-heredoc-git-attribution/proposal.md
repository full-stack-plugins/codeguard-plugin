# 2026-09-23-fix-heredoc-git-attribution

## Why

fix-release-chain-and-gate-attribution 把非 Shell 脚本正文的 git 归因收紧为调用形态，但其 Non-Goal
留了一个敞口：**外层 Bash heredoc/命令文本数据段的 git 样例仍被切段误伤**。本轮实测该敞口高频咬人
（写作 OpenSpec/测试文档时 heredoc 里的 `git add && git commit && git push` 样例文本 5+ 次整调用被拦，
连写入操作都未执行）。根因：`split_shell_segments` 把 heredoc 正文当 shell 语法切段；且
`_flatten_substitutions` 先于切段抽取 `$(...)`，连引号定界（全字面量）的正文也拦不住。

## What Changes

- heredoc 正文按**归属语义**遮蔽（保留换行的空白）后再切段/展开：
  - 数据程序 + 引号定界符：正文全字面量 → 全遮蔽（杀误报）；
  - 数据程序 + 无引号：正文会做命令替换展开，`$(...)`/反引号跨度保留扫描（规格既有实测向量）；
  - bash/sh 等 Shell 解释器：正文是内层 shell 代码 → 不遮蔽、保留既有切段建模；
  - python/node：正文非 shell 语法 → 全遮蔽（杀误报）。
- 遮蔽前移至 `_flatten_substitutions` 入口，保证引号定界正文的 `$(...)` 不被提前抽取。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

无（heredoc 归属语义以 ADDED requirement 并入 hook-protocol，不重改同一条 requirement）。

## Impact

- `scripts/codeguard/git_syntax.py`（mask_heredoc_bodies + 两处入口接线）。
- 行为变更：heredoc 数据段的 git 字面量样例不再触发门禁；无引号数据正文的命令替换向量、
  Shell 解释器正文建模、直接命令判定全部不变（五态语义回归锚定）。
- 已声明边界：python/node **stdin heredoc** 内的 subprocess 调用形态不在归因范围
  （与动态拼接同类；脚本文件路径上的调用形态归因不受影响）。
