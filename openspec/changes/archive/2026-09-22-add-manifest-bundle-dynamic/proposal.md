## Why

`tests/test_plugin_manifests.py::test_each_released_manifest_points_to_the_68_skill_bundle` 写死 `assertEqual(68, expected)`。当上游技能 snapshot bump（如 `c1468d0` 升至 `codeguard-skills@v0.1.2`）引入或移除技能时，这条断言会让 CI 在「不相关」位置失败，错误信号弱——测试位于 manifest 校验区，但失败源是 lockfile/技能数漂移。需要把硬编码常量改成「从锁+本地插件推导」的动态期望。

## What Changes

- `tests/test_plugin_manifests.py::test_each_released_manifest_points_to_the_68_skill_bundle` 重命名为 `test_each_released_manifest_points_to_the_lock_union_plus_local_skills`，断言改为：期望 = `skills.lock.json` 各 source 的 `skills` 并集 + `plugin-local-skills.json` 的 `skills` 集合 + 仓根 `skills/` 下含 `SKILL.md` 的目录数三者一致。
- 期望值不再硬编码；测试名去掉魔法数字。

## Capabilities

### New Capabilities

- `plugin-manifest-contracts`: Defines the contract that released manifests' skills field resolves to the union of vendored and plugin-local skills.

### Modified Capabilities

None.

## Impact

仅修改 1 个测试用例（~5 行）。不改变 manifest 内容、不改 lock、不改 plugin-local 登记。