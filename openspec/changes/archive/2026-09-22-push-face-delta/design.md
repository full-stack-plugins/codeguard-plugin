## Context

delta 默认是 0.8.0 引入的（存量不拦新提交），其"改动集"当时只定义了提交面。push 场景下工作树恒净、改动已入历史——同一函数返回空集，门禁形同虚设。这是自引入的正确性缺口，必须在下一补丁版本闭合，否则"修存量不拦新提交"会顺带变成"什么都拦不住"。

## Goals / Non-Goals

**Goals:**

- 推送面前移到"尚未送出的提交"，堵住绕过提交后的出门路径。
- 面判定单源：命中与选面共用一次扫描（`_guarded_mode`），软硬两门共用语义（UPS 以提示词意图选面）。
- 缓存按面隔离；不可解析 upstream 时优雅回退（既有"push 无 upstream 不崩"保持）。

**Non-Goals:**

- 不做跨仓脚本的 cd 追踪（脚本内部换仓仍是能力边界，协议已声明）。
- 不实现 `strict_mode`（会违反协议 §1 PostToolUse 恒 exit 0 的设计；仅文档如实化）。
- 不改退出码与 JSON schema。

## Decisions

1. **push 面用三点差 `up...HEAD`（我这侧的分歧）而非两点差**——两点差会把上游侧的文件也卷进来，那些不是"我们要送出的改动"。
2. **push 优先的面选择**——`git commit && git push` 链同时命中两面时取更宽的 push 面，宁多勿漏。
3. **mode 进缓存键**——同 HEAD/工作树下两面文件集不同，共键会互相污染（commit 面的空结果把 push 面的失败缓存掉）。
4. **面判定复用命中判定**——`is_guarded` 由 `_guarded_mode` 派生，杜绝"命中了却选错面"的两条代码路径。
5. **`requiresConfig` 先于 probe**——纯文件系统判定不起步进程、更快，且是更根本的原因（没接这个 linter 时工具装没装不影响结论）；同时修复既有 yaml 测试在无 yamllint 机器上的失败。

## Risks / Trade-offs

- [push 面在大型仓多算一次 `up...HEAD` diff] → 只取文件名列表，量级与提交面三路 git 调用相同；不可解析时零成本返回空。
- [无 upstream 的首次推送拿不到提交面] → 与既有"不崩"行为一致；首次 push 由 GitHub 端 CI 兜底，且下一次起 upstream 即存在。
- [UPS 的 push 意图靠词面（push/推送）] → 与硬门禁的命令面判定是两套输入（自然语言 vs 命令），词面是可得的最优信号；误选 commit 面时仍查提交面，不失去拦截、只可能少查未推送提交（随后硬门禁 push 面补上）。

## Migration Plan

1. 本变更规格先行（MODIFIED requirement 全文更新 + 新场景）。
2. 实现（mode 化 + 顺序 + rc127 + 四钩子去重 + 文档）与回归测试同批落地。
3. run_all/unittest/openpec/lint 全绿后 bump 0.8.1（修复类，patch），走仓内 PR 流程发版。
