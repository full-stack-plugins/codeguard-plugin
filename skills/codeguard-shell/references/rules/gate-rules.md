# Shell 门禁规则与失败语义

## 状态机

```text
DETECTED -> READY -> CHECKING -> PASS
                  |            -> FAIL -> FIXING -> RECHECK
                  -> UNVERIFIED
DETECTED -> PLANNED
```

- `PASS`：权威检查命令在明确范围内退出 0。
- `FAIL`：工具成功运行并发现违规。
- `UNVERIFIED`：工具、配置、权限、版本或环境不足。
- `PLANNED`：仅有识别能力，尚无可执行门禁。

## 修复优先级

1. 配置加载错误：先恢复工具可运行性。
2. 自动可逆格式问题：运行 formatter 并审查 diff。
3. 确定性静态规则：做最小代码修复。
4. 可能改变行为的问题：停止自动修复，解释取舍。
5. 规则争议：保留失败，等待用户决定，不静默豁免。

## 完成门禁

- [ ] 记录工具版本、命令、工作目录与扫描范围。
- [ ] 原失败命令复跑退出 0。
- [ ] 自动修复 diff 已审查。
- [ ] 项目已有测试/构建已运行或明确标为未运行。
- [ ] 没有新增 suppression、ignore 或规则降级。
- [ ] 报告区分 PASS、FAIL、UNVERIFIED、PLANNED。
