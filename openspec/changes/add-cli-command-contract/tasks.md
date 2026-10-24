# CodeGuard CLI 命令契约任务

状态：规划完成，按实现证据勾选。

## 1. P0 生命周期

- [ ] 1.1 实现 install/uninstall，区分宿主接入与项目文件；支持 --dry-run。规格：CLI-001。
- [ ] 1.2 实现 version/doctor/status，输出 JSON；doctor 不执行代码检查。规格：CLI-004。
- [ ] 1.3 实现 discover，只读识别项目、语言、构建系统和可用工具。规格：CLI-002。

## 2. P0 项目事实

- [ ] 2.1 实现/补齐 init，幂等，不覆盖已有配置，支持 --dry-run。规格：CLI-003。
- [ ] 2.2 实现/补齐 check，只读门禁，输出统一 decision。规格：CLI-005。
- [ ] 2.3 实现 report，读取已有证据，不重新执行。规格：CLI-006。

## 3. P1 专业能力

- [ ] 3.1 按命令表补齐领域命令：install,uninstall,upgrade,version,doctor,status,discover,init,check,fix,cve,dockerfile,impact,explain,report,hooks install,hooks status,engine,completion。规格：CLI-007。
- [ ] 3.2 未实现能力必须输出 DESIGN_ONLY/UNVERIFIED；不得伪造 PASS。规格：CLI-008。

## 4. P1 Hook

- [ ] 4.1 实现 hooks install/status，只写当前仓库 Hook。规格：CLI-009。
- [ ] 4.2 确认 Hook 事件所有权，不与其他 Guard 抢占同一事件。规格：CLI-010。

## 5. P2 兼容

- [ ] 5.1 保留旧命令别名并输出弃用提示。规格：CLI-011。
- [ ] 5.2 增加 golden JSON 与退出码矩阵测试。规格：CLI-012。
