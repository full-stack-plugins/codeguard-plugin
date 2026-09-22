## Context

审计以实弹方式进行（image-factory 仓几十次真实提交尝试），每条缺陷都有复现记录。核心张力：门禁是"硬"的，但它的输出直接塑造 AI 的下一步行为——一句缺失或误导的反馈（不声明整调用被拒）会引发整类错误操作。另一张力：作用域太宽（全仓）让存量问题绑架新提交，作用域太窄（无）则失去保护；git 本身提供了天然的分界线——本次改动。

## Goals / Non-Goals

**Goals:**

- 让拦截反馈与宿主真实语义一致（整调用未执行）。
- 让"改没改、查哪些"完全由 git 状态决定（delta），并可用 `gate_scope` 退回全仓。
- 让判定可复现（规则集不随机器漂移）、诚实（工具崩溃=未验证，非失败）。
- 让一切绕过可见、可回收（记账 + Stop 提醒 + 双门一致）。

**Non-Goals:**

- 不改退出码与 JSON schema（§1 表原样）。
- 不做更深层（subprocess 拼接）的间接执行分析——静态一层是能力边界，文档不夸大。
- 不引入第三方依赖；不改 `languages.json` 之外的注册表语义。
- 不处理 2 个与本变更无关的既有 yaml 环境性测试失败（基线同名保留）。

## Decisions

1. **delta 为 git 仓缺省、`codeguard.json gate_scope:"repo"` 可退回**——提交门禁的正确语义是"新提交不引入新问题"，仓健康属 `check` CLI（保持全量）。
2. **作用域物化放独立 `scripts/scope.py`**——`language-gate-commands` 明文限定 detect_lang 只暴露检测面白名单，塞进去违反既有 spec；新模块无反向依赖。
3. **exit 2 归未验证而非失败**——与该 spec 既有的"用法错误不是 lint 结论"要求同向；zig 等真问题工具实测用 exit 1，无冲突。
4. **ruff 默认配置用原生格式文件**——`--config` 指向 `[tool.ruff]` 包装的 pyproject 片段直接解析失败（实测），故新增 `linters/ruff/ruff.toml` 与 snippet 并存（文档用 snippet、注入用原生）。
5. **整调用声明进 `gate_directive` 末段而非首行**——首行综述是 tests 守护的契约，末段追加不破坏它。
6. **状态目录迁 `~/.codeguard` + 条目归一化**——`_notify` 曾写出缺 `total` 的残缺条目，`entry["total"]` KeyError 被 fail-open 吞掉导致输出全空（实测复现）；归一化从根上封死。
7. **shell severity 政策对齐进 lint**——gate 带 `--severity=warning` 而单文件 lint 不带，delta 与 PostToolUse 都走 lint，政策分叉会造成门禁间互相矛盾。

## Risks / Trade-offs

- [delta 让存量坏文件不再拦新提交] → 这是设计意图（提交门禁查增量），仓健康由 `check`/CI 全量承担；`gate_scope:"repo"` 可逐仓回退。
- [静态一层间接可被更深构造绕过] → 文档明确能力边界，不夸大"硬保证"；触发面（直接命令+一层脚本）已覆盖实测全部漏网案例。
- [exit 2 归未验证对用 exit 2 报 findings 的假想工具变宽] → 主流工具（ruff/eslint/shellcheck/yamllint/zig fmt）findings 均为 exit 1，注册表内无反例（测试锁定）。
- [双副本仍在宿主同时启用] → 插件只能告警+事件去重，卸载动作在用户；去重键依赖宿主事件 id，缺失时保持旧行为（宁可重复不误吞）。

## Migration Plan

1. 本变更规格先行（已完成），三份 delta 挂既有能力。
2. 实现按 B1-B8 批次落地（已完成），`tests/run_all.py` 的 delta 前提 3 处与 `shell.lint` 政策同步修正。
3. `__protocol__.md` 同 commit 更新符号定位与新语义（本变更）。
4. 版本 0.7.1 → 0.8.0（行为新增，minor），走 AGENTS.md 发版流程推两仓。
5. 既有 2 个 yaml 环境性失败留在基线（与本变更无关、同名复现）。
