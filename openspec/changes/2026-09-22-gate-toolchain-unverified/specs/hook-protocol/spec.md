# hook-protocol（增量）：缓存键作用域 + 单次内联豁免 + 豁免读取审计

## ADDED Requirements

### Requirement: Gate cache keys SHALL distinguish scope

门禁结果缓存键 MUST 含作用域维度（delta / repo）。UPS 软门禁（可能 repo 全量）
与 PreToolUse 硬门禁（delta）在缓存 TTL 内 MUST NOT 复用彼此结果——否则本次
改动无关的存量问题会误拦新提交。

#### Scenario: Full-scan failure must not leak into a delta commit
- **WHEN** UPS 按 repo 全量扫出存量失败并写缓存，随后硬门禁按 delta 检查本次改动
- **THEN** 硬门禁不复用该缓存，独立按 delta 得出结论

### Requirement: Escape hatches SHALL be explicit and audited

逃生门 MUST 显式、可审计：

- `git -c codeguard.skipGate=true|1|yes …` MUST 被识别为**单次内联豁免意图**
  （不落配置、无残留），放行并记 `inline-skipGate` 审计事件；识别 MUST 只认
  **子命令之前**的 `-c` 全局参数位赋值（git 语法本义），MUST NOT 凭子串匹配
  命令文本或子命令之后的参数（`commit -m` 消息里出现豁免短语 MUST NOT 构成
  豁免——危险方向误判会静默关掉门禁）。
- 命令链里含 `git config codeguard.skipGate <true|1|yes>` **设置**段 MUST 被
  识别为**显式豁免意图**（文档推荐的 set→提交→unset 自清理写法），放行并记
  `chain-skipGate` 审计事件；`--get`/`--unset`/`--list` 查询形态 MUST NOT 算
  豁免。
- `git config codeguard.skipGate` 读取失败（超时/OSError）MUST 记
  `skipGate-read-error` 审计事件并附异常摘要，MUST NOT 静默返回未豁免。
- 所有豁免形态 MUST 进入会话审计明细（时间 + 类型 + 仓库），Stop 汇总可见。

#### Scenario: Inline single-shot escape
- **WHEN** 命令为 `git -c codeguard.skipGate=true commit -m x`
- **THEN** 门禁放行并记 `inline-skipGate` 事件；`git -c core.editor=vim commit` 不算豁免

#### Scenario: Chain self-cleaning escape
- **WHEN** 命令为 `git config codeguard.skipGate true && git commit -m x && git config --unset codeguard.skipGate`
- **THEN** 门禁放行并记 `chain-skipGate` 事件；`git config --get codeguard.skipGate && git push` 不算豁免

#### Scenario: Message text never disables the gate
- **WHEN** 命令为 `git commit -m "config codeguard.skipGate true"` 或 `git commit -m "use -c codeguard.skipGate=true"`
- **THEN** 不构成豁免，门禁照常执行

#### Scenario: Unreliable config read leaves a trace
- **WHEN** `git config --get` 读取超时
- **THEN** 返回未豁免（宁可误拦不误放行），并记 `skipGate-read-error` 事件与异常摘要

## MODIFIED Requirements

### Requirement: Agent/host tooling work directories SHALL be excluded from scan and intake

`FULL_SCAN_EXCLUDES`（扫描面与入库面单一事实源）除构建产物/依赖快照外 MUST
排除 Agent 与宿主工具工作目录（`.mimosa`、`.worktrees`、`.code-review-graph`、
`.kimi-code`、`.zcode`、`.codex-plugin`、`.agents`）——这些目录可能含源码快照
或 git 子工作树，入库会污染历史、全量扫描会重复报同一批问题。

#### Scenario: A hook-state directory is staged by git add -A
- **WHEN** 仓根存在 `.mimosa/` 且执行 `git add -A && git commit`
- **THEN** 提交内容安全检查 MUST 报「目录 ./.mimosa/ 不应入库」，全量扫描 MUST 跳过该目录
