# 本次设计交付验证

日期：2026-09-24。性质：架构与规格文档验证，**不是 Rust 实现、真实扫描器或发布验收**。

## 交付范围

- [设计文档入口](../../../docs/rust-cli/README.md)：架构、技术方案、57 项语言迁移与验收、项目内持久修复工作流。
- 本 change 的 proposal、design、10 个 capability delta 和可执行 tasks。
- 持久工作区使用 `./codeguard/`，含自有 .gitignore；以问题、阻塞、任务和复检事件指导修复，规则和最终门禁不由任务文件决定。

## 实际检查

`openspec validate introduce-rust-codeguard-cli --strict --json --no-interactive` 已通过，无 issue。最初的校验发现 MODIFIED scenario 标题未保留，已恢复原 scenario 名称并显式限定旧协议范围，再次校验通过；未删除旧场景来绕过验证。

本次使用只读脚本核对 Markdown 本地链接、代码围栏、JSON 示例、语言 ID/状态、重复任务编号、proposal/spec 目录和规范任务追踪，最终退出 0、issues=[]。范围为 19 份 Markdown、40 个本地链接、57 个语言条目、10 个 capability、43 条 requirement、89 个 scenario、228 项未勾选实现任务。Mermaid 有 9 个代码块，已检查围栏与人工语法，未执行渲染器视觉验收。

`git diff --check` 与 `git diff --cached --check` 在本次文档路径范围均通过。任务初次语言 ID 机器核对发现三项仅写了大小写不同的展示名，已补充 canonical ID 并复核 57 项全部可追踪。

OpenSpec 的 planning artifacts 为 complete 只说明 proposal/design/specs/tasks 已齐备，不意味着实施完成。实现任务全部未勾选；不得据 status 的 isComplete 字段声称二进制可用。

## 独立读者检查

两轮只读审查识别并修订以下六项：

1. 例外同时绑定范围、内容身份和到期时间，不允许无期限例外。
2. 离线执行必须具备可验证的网络隔离条件，不能只转发参数。
3. 可信 CI 验证端与被测脚本执行区隔离，防止项目脚本篡改策略或签发结果。
4. work sync 幂等消费全部匹配未导入报告，不只取最后一次检查。
5. 已启用插件工作流必须经过 scan→sync→RepairBrief；存储失败可见。
6. attempt 开始/结束记录复检前失败和无修改尝试，避免预算失效。

语言任务已细分到具体 language ID；每种语言均有适用性、lint/comments、CVE/security/build 与真实工具验收要求，不用大组汇总掩盖缺项。

## 当前证据边界

源码观察基线为 `03ebb24`，读到的注册表为 54 stable/3 planned。工作过程中存在其他任务切换分支、暂存 release/manifest 文件；本次不创建或切换分支、不修改这些发布文件、不代替其他任务提交。文档最终实现基线须在实施开始时再次核对。

没有建立 Rust 源码仓、编译或执行新 CLI，没有安装工具、测量实际误报率、发布制品、同步市场或验收宿主；没有运行 openspec apply/sync/archive。既有代码全量测试不用于证明本次文档设计已运行。后续实现与发布证据按 tasks 逐项记录。
