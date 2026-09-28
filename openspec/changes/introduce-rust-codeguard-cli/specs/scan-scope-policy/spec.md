## ADDED Requirements

### Requirement: Managed remediation artifacts SHALL have a bounded self-scan policy

`.codeguard/` 按既有点前缀策略不进入普通源码发现；其中被初始化清单拥有的运行产物与问题/任务文件 MUST 接受工作区 schema、路径及脱敏校验。不得因目录名 `codeguard` 忽略同名非点目录；其中的用户源码与未声明文件 MUST 继续普通检查。点目录排除不得赋予 `.codeguard/` 质量策略批准或入库安全豁免；拟提交记录仍须接受安全检查。既有点前缀的配置例外保持不变。

#### Scenario: Managed files coexist with user code
- **WHEN** `.codeguard/tasks` 有生成任务且 `codeguard/src` 有用户源码
- **THEN** 生成任务走工作区校验，用户源码照常检测，不出现递归扫描运行副本

#### Scenario: A managed record contains a secret
- **WHEN** 拟提交的持久记录意外包含密钥
- **THEN** 入库安全仍检查并阻断，受管产物不能豁免敏感内容

#### Scenario: Agent expands the ownership manifest
- **WHEN** agent 将普通源码路径添加进受管排除清单
- **THEN** 生成器所有权校验不接受扩张，不能据可写 manifest 关闭扫描
