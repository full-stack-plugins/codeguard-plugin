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
