## ADDED Requirements

### Requirement: Claude Code marketplace manifest SHALL exist and track the release version

`.claude-plugin/marketplace.json` MUST 存在且为合法 JSON，形态为市场清单（顶层仓库标识与 owner，`plugins[]` 含 `name`/`description`/`version`/`source`）。`plugins[0].version` MUST 与各宿主 manifest 的版本一致，且发版工具 MUST 将该文件纳入版本链更新（版本漂移按契约失败）。

#### Scenario: Claude host installs the plugin

- **WHEN** 检查发布仓的 `.claude-plugin/marketplace.json`
- **THEN** 文件存在、可解析、`plugins[0]` 的 name 为插件 id、`source` 为 `"./"`，且 version 与 `kimi.plugin.json` 等 manifest 一致

#### Scenario: A release bumps the version

- **WHEN** 发版工具执行版本升级
- **THEN** `.claude-plugin/marketplace.json` 的版本随其余 manifest 同步更新，读回校验覆盖该文件
