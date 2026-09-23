## ADDED Requirements

### Requirement: Managed remediation artifacts SHALL have a bounded self-scan policy

初始化清单验证通过的 Codeguard 自有运行产物及生成问题/任务文件 MUST 从普通被测源码发现中排除，并接受工作区 schema、路径及脱敏校验。排除 MUST 精确到生成器拥有的路径集合，不得仅因目录名 codeguard 忽略整棵树；用户源码、未声明文件及入库安全检查 MUST 保留。此要求 MUST 不改变既有点前缀策略及两项例外。

#### Scenario: Managed files coexist with user code
- **WHEN** `codeguard/tasks` 有生成任务且 `codeguard/src` 有用户源码
- **THEN** 生成任务走工作区校验，用户源码照常检测，不出现递归扫描运行副本

#### Scenario: A managed record contains a secret
- **WHEN** 拟提交的持久记录意外包含密钥
- **THEN** 入库安全仍检查并阻断，受管产物不能豁免敏感内容

#### Scenario: Agent expands the ownership manifest
- **WHEN** agent 将普通源码路径添加进受管排除清单
- **THEN** 生成器所有权校验不接受扩张，不能据可写 manifest 关闭扫描
