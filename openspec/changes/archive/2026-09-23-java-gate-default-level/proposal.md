# 2026-09-23-java-gate-default-level

## Why

java 门禁当前默认执行完整 `mvn verify`（含测试执行）。实测：easy4j 线上仓
reactor + 全量测试普遍超 300s（lint_timeout_seconds 默认），超时按 timeout
路由归 UNVERIFIED——门禁跑满超时预算也给不出真结论，而 Java 冷缓存
`install -DskipTests` 就普遍超 2 分钟（user_config.py 注释实录）。门禁的
职责是提交面的编译/打包/静态正确性；测试执行是 CI 的职责边界（P2-6 收口）。

P2-7 残余：codeguard 在项目无自有 ruff 配置时注入默认配置，其规则集以特定
ruff 版本为基准，README 未记录基线，机器间判定可能漂移。

## What Changes

- `scripts/java_project.py`：Maven 默认 argv 追加 `-DskipTests`（测试代码仍
  编译，仅跳过执行）；Gradle 默认 argv 追加 `-x test`（check 任务图剔除
  test 任务）。
- `scripts/languages.json`：java.lint 同步为 `mvn -B -DskipTests verify`
  （注册表与实际命令一致，docs/LANGUAGES.md 可复现）。
- README：①Java 章节记录默认等级语义与 `codeguard.json java.commands`
  升级到含测试完整 verify 的路径；②记录 ruff 版本基线（CI 钉扎
  `ruff==0.16.8`，项目无自有 ruff 配置时注入的默认配置以该版本为基准）。

## Impact

- Affected specs: `language-gate-commands`
- 受益场景：多模块/大测试面的 Maven/Gradle 仓（easy4j 全系三分支）——
  门禁从「超时 UNVERIFIED」变为真实结论，每提交不再重复执行全量测试。
- 行为变更：默认检查等级不含测试执行；需要测试执行的项目用
  `codeguard.json` `java.commands` 显式声明（既有权威覆盖机制）。
- 不改：`java.commands` 权威覆盖语义、模块影响分析（-pl/-am 反向闭包）、
  UNVERIFIED 判定契约、wrapper 探测（./mvnw 优先）、静态检查生命周期
  绑定的 gaps 说明。
