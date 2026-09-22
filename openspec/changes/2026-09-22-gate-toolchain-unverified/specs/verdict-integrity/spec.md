# verdict-integrity（增量）：工具链不兼容归 UNVERIFIED

## ADDED Requirements

### Requirement: Toolchain incompatibility SHALL be UNVERIFIED, never FAIL

工具链自身不兼容（版本矩阵不匹配、工具能力边界）MUST NOT 被判为代码违规。
命中下列输出特征时结论 MUST 为 UNVERIFIED 并附原因，MUST NOT 阻塞 Git 操作：

- Maven POM 模型版本高于当前 Maven（`'modelVersion' of '…' is newer than the versions supported`、`requires a newer version of Maven`）
- javac/javadoc 的 `--release` / `target` 高于或低于当前 JDK（`release version … not supported`、`invalid target release`）
- 字节码版本高于当前 JVM（`UnsupportedClassVersionError`、`class file version`、`has been compiled by a more recent version`）

真违规（非上述特征的 rc==1）MUST 仍为 FAIL。

#### Scenario: Maven 3 reads a POM 4.1.0 project
- **WHEN** java 门禁以系统 Maven 3 在 modelVersion 4.1.0 的工程上执行且 rc=1
- **THEN** 结论为 UNVERIFIED（原因：工具链执行异常），提交放行且明示未验证

#### Scenario: JDK 26 javadoc rejects release 8
- **WHEN** javadoc 输出 `error: release version 1.8 not supported`
- **THEN** 结论为 UNVERIFIED，MUST NOT 阻塞提交

#### Scenario: A genuine violation still fails
- **WHEN** 输出不含任何环境特征且 rc=1
- **THEN** 结论为 FAIL 并阻塞提交

### Requirement: ShellCheck dialect limits SHALL be UNVERIFIED

ShellCheck 不支持的脚本方言（SC1071）是工具能力边界而非代码违规，命中时
结论 MUST 为 UNVERIFIED 并说明原因。

#### Scenario: A zsh script reaches ShellCheck
- **WHEN** ShellCheck 对 `.zsh` 文件报 SC1071 (error)
- **THEN** 结论为 UNVERIFIED（原因：ShellCheck 不支持该脚本方言），MUST NOT 阻塞提交

#### Scenario: SC1071 must not mask a real finding in the same batch
- **WHEN** 同一 shellcheck 输出同时包含 `.zsh` 的 SC1071 块与 `.sh` 的真实违规
- **THEN** 剥离 SC1071 诊断块后按剩余内容判定，真实违规 MUST 仍为 FAIL

### Requirement: Stale findings MAY be excused only with same-tool baseline evidence

存量问题豁免（不拦新提交）MUST 有基线证据：用同一条 linter 命令、同一工具
版本对**改动前版本**跑出相同发现签名（finding_signatures），且本次发现 ⊆
基线发现。基线引用 MUST 取"改动前"：commit 面取 `HEAD`，push 面取
`@{upstream}`（坏提交已进 HEAD，拿 HEAD 当基线会把新引入坏内容误判成存量）。
基线内容不存在（如新文件）或签名提不出或基线跑不起来时 MUST NOT 豁免。

#### Scenario: A pre-existing finding is excused with baseline
- **WHEN** HEAD 版本同一文件经同命令同工具跑出相同发现签名
- **THEN** 该项归存量豁免并明示「存量问题（基线同命令同工具已存在）」

#### Scenario: A push of a bad commit is not excused
- **WHEN** 坏内容已提交进 HEAD 但未推送，push 面检查发现违规
- **THEN** 基线取 `@{upstream}`（无此内容）→ 不豁免，MUST 阻塞推送

#### Scenario: No baseline refuses excusal
- **WHEN** 文件从未入库（无改动前版本）
- **THEN** MUST NOT 豁免，按 FAIL 处理

### Requirement: Gate decisions SHALL be logged for audit

每次语言级门禁判定（语言、命令、退出码、结论、原因）MUST 落盘
`gate-decisions.jsonl`（滚动保留最近 500 条），写失败 MUST NOT 影响门禁主流程。

#### Scenario: A gate run leaves an audit trail
- **WHEN** shell 语言检查因违规判 FAIL
- **THEN** 决策日志含 lang=shell、命令 argv、rc、status=FAIL 与时间戳
