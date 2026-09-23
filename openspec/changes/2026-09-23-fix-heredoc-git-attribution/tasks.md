# Tasks: 2026-09-23-fix-heredoc-git-attribution

## 1. 实现

- [x] 1.1 `mask_heredoc_bodies`：按归属语义遮蔽（引号数据全遮蔽/无引号保留替换跨度/Shell 解释器不遮蔽/非 Shell 全遮蔽）
- [x] 1.2 `split_shell_segments` 与 `_flatten_substitutions` 两处入口接线（遮蔽先于展开）

## 2. 回归测试（五态语义）

- [x] 2.1 python heredoc 三引号样例文本不触发
- [x] 2.2 无引号数据 heredoc 的 `$(git …)` 仍触发（既有向量）
- [x] 2.3 引号数据 heredoc 的字面 `$(git …)` 不触发（flatten 前遮蔽回归）
- [x] 2.4 bash heredoc 真实命令仍触发且建模不变
- [x] 2.5 直接命令判定不变
- [x] 2.6 全量回归 + ruff 干净

## 3. 发版

- [ ] 3.1 dogfood 直跑 bump 发 v0.15.3
- [ ] 3.2 市场仓同步 + PR/CI/合并 + 两仓推送
