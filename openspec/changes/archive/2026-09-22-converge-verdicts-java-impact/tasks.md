# Tasks

## 1. 判定可信度

- [x] 1.1 为多文件漏检、UNVERIFIED 序列化、命令作用域和 CVE 错误建立失败测试，再修复并验证 test_verdict_integrity。
- [x] 1.2 为 index/HEAD 与工作树错配、预测暂存安全范围、删除文件建立真实临时 Git 测试；实现隔离快照并确认原工作树/index 不变。
- [x] 1.3 统一 CLI/MCP/hooks 状态，取消无证据历史归因，工具故障不自动修复；通过相关回归。

## 2. Java 项目感知

- [x] 2.1 先建立 Maven/Gradle、wrapper、多模块反向依赖及保守回退测试，再实现只读 java-plan。
- [x] 2.2 接入 Java gate/check 与 CLI/MCP，测试真实子进程参数、范围及未验证输出，不执行真实联网构建。

## 3. 收敛与交付

- [x] 3.1 同步协议、双语 README、架构/技术路线和 OpenSpec；验证 docs parity、OpenSpec validate。
- [x] 3.2 执行全量 unittest、run_all、ruff、vendor 离线/在线检查、注册表校验并记录结果。
- [x] 3.3 检查市场仓状态，按仓库脚本准备 minor 升版，验证元数据一致；远端发布未经确认不执行。
- [x] 3.4 对照规格完成完整性/正确性/一致性审查，保存验证报告和未验证边界。
