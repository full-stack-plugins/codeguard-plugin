# 2026-09-22-gate-toolchain-unverified

## Why

会话实测（hermes-java-sdk feature/1.0.x/3.0.x、easydoc feature/3.0.x）连续四类
误拦：门禁把**工具链自身不兼容**判成**代码违规**，且逃生门不可靠，只能靠
匹配层漏洞绕过——违背 verdict-integrity 的「无法验证 ≠ 验证失败」原则。

实测复现（4/4 判 FAIL，应为 UNVERIFIED）：

1. 系统 Maven 3 读不了 POM 4.1.0：
   `[FATAL] 'modelVersion' of '4.1.0' is newer than the versions supported …`
2. 宿主 JDK 26 不支持 `--release 8`：
   `error: release version 1.8 not supported`
3. javac target 与当前 JDK 不匹配：`error: invalid target release: 21`
4. 字节码高于当前 JVM：`UnsupportedClassVersionError … class file version 65.0`

第五类永久红：ShellCheck 不支持 zsh（SC1071 是 error 级固有限制），`.zsh`
文件进 shellcheck 目标面必红——实测中「只改 .py」的提交被两个从未触碰的
`.zsh` 拦下。

逃生门缺陷：`git config codeguard.skipGate true` 实测时灵时不灵（git config
读取 timeout=10s 时**静默**返回 False，无任何痕迹）；`git -c codeguard.skipGate=true`
内联形态因 `-c` 被归一化剥掉而**漏拦**（守卫绕过口），用户想单次豁免却没有
正门。另：门禁缓存键缺 scope 维度，UPS 软门禁（repo 全量）与硬门禁（delta）
在 60s TTL 内互串，本次改动无关的旧文件误拦新提交。

## What Changes

- `scripts/verdict.py`：`_ENV_ERROR` 追加 Maven POM 版本不匹配 / release version
  不支持 / invalid target release / UnsupportedClassVersionError 特征，归
  UNVERIFIED；新增 SC1071 归 UNVERIFIED（ShellCheck 方言能力边界）。
- `scripts/languages.json`：shell 全量 gate 的 find 目标剔除 `*.zsh`（识别仍属
  shell 生态，只是不送 shellcheck）。
- `hooks/gate_lib.py`：①delta 面对 shell 过滤 `.zsh` 并明示「N 个 zsh 文件
  未验证」，不静默丢弃；②`_gate_cache_key` 增加 `scope` 维度，切断 UPS/硬
  门禁跨作用域缓存污染；③`skip_gate_via_git_config` 读取失败（timeout/OSError）
  记 `skipGate-read-error` 审计事件 + detail，不再静默 False；④逃生门文档
  增补单次内联豁免与链内 set→提交→unset 自清理写法。
- `hooks/pre_tool_git_guard.py`：新增 `inline_skip_gate()`——识别
  `git -c codeguard.skipGate=true|1|yes …` 为**显式单次豁免意图**（不落配置、
  无残留），放行并记 `inline-skipGate` 审计事件；新增 `chain_skip_gate()`——
  链内 `git config codeguard.skipGate <真值>` **设置**段同为显式豁免意图，
  记 `chain-skipGate` 审计（文档推荐的 set→提交→unset 同链写法此前整链被拦、
  首用必败）；新增 `_git_seg_parts()` 按 git 全局参数语法识别子命令边界，
  `commit -m` 消息文本里的豁免短语不再被误判为豁免（堵"文本短语静默关掉
  门禁"的危险方向误判）。
- `scripts/scope.py`：`FULL_SCAN_EXCLUDES` 增加 Agent/宿主工具工作目录
  （`.mimosa`/`.worktrees`/`.code-review-graph`/`.kimi-code`/`.zcode`/
  `.codex-plugin`/`.agents`）——实测 `.mimosa/`（含源码快照）与 `.worktrees/`
  （git 子工作树）曾被 `git add -A` 带进暂存区，且子工作树重复扫描出双份误报。

## Impact

- Affected specs: `verdict-integrity`、`language-gate-commands`、`hook-protocol`
- 受益场景：任意 JDK/Maven 版本矩阵下的 Java 仓（easy4j 全系三分支）、含
  `.zsh` 的仓、需要单次豁免的发布流程、UPS 与硬门禁连跑的正常提交路径。
- 行为变更：`.zsh` 不再被 shellcheck 检查（改由 SC1071 兜底明示未验证）；
  `git -c codeguard.skipGate=true` 从「漏拦绕过口」变为「有审计的正门」；
  链内 set→commit→unset 同链写法从「整链被拦」变为「有审计的正门」，
  消息文本豁免短语从「静默关掉门禁」变为「不构成豁免」。
- 不改：真违规判定（rc==1 非环境特征仍 FAIL）、敏感文件安全检查、
  fail-open 内部错误策略。
