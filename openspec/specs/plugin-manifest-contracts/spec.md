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

