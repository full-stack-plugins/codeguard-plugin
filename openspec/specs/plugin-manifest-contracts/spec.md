# plugin-manifest-contracts Specification

## Purpose
定义插件清单族的一致性契约：四端 manifest 与市场清单的版本链一致、发布物中的 skills bundle 必须等于 skills.lock 与 plugin-local 声明的并集，安装面不出现缺技能或多技能。
## Requirements
### Requirement: Released manifest skills bundle SHALL equal the lock+local union

For each released manifest, the test contract SHALL assert that `len(glob("skills/*/SKILL.md")) == |union(skills.lock.json sources[*].skills) ∪ plugin-local-skills.json skills|`. The expectation SHALL NOT be a hardcoded number.

#### Scenario: A new vendored skill lands in the upstream snapshot

- **WHEN** the upstream `codeguard-skills` snapshot is bumped and adds one new skill
- **THEN** the test passes once the plugin repo runs `python3 scripts/vendor/skill_vendor.py update` and the new directory appears under `skills/`

#### Scenario: A plugin-local skill is declared without a directory

- **WHEN** `plugin-local-skills.json` lists a name that has no matching `skills/<name>/SKILL.md`
- **THEN** the test fails with the symmetric-set difference, pointing at the missing directory

#### Scenario: An undeclared directory appears under skills/

- **WHEN** a directory `skills/<x>/SKILL.md` exists but `<x>` is neither in any lock source nor in `plugin-local-skills.json`
- **THEN** the test fails with the same symmetric-set difference, pointing at the orphan directory

### Requirement: Claude Code marketplace manifest SHALL exist and track the release version

`.claude-plugin/marketplace.json` MUST 存在且为合法 JSON，形态为市场清单（顶层仓库标识与 owner，`plugins[]` 含 `name`/`description`/`version`/`source`）。`plugins[0].version` MUST 与各宿主 manifest 的版本一致，且发版工具 MUST 将该文件纳入版本链更新（版本漂移按契约失败）。

#### Scenario: Claude host installs the plugin

- **WHEN** 检查发布仓的 `.claude-plugin/marketplace.json`
- **THEN** 文件存在、可解析、`plugins[0]` 的 name 为插件 id、`source` 为 `"./"`，且 version 与 `kimi.plugin.json` 等 manifest 一致

#### Scenario: A release bumps the version

- **WHEN** 发版工具执行版本升级
- **THEN** `.claude-plugin/marketplace.json` 的版本随其余 manifest 同步更新，读回校验覆盖该文件

