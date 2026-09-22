## ADDED Requirements

### Requirement: Negated statements SHALL NOT trigger the gate

当触发词出现在否定语境（如 `未提交`、`还没提交`、`别提交`）中且不存在行动意图短语时，UserPromptSubmit MUST 不触发门禁。该规则 MUST 同时适用于中文子串触发词与英文词边界触发词。

#### Scenario: User reports something is not committed

- **WHEN** 用户消息为 `未提交任何东西` 或 `别提交这些文件`
- **THEN** 钩子 exit 0 且 stdout 为空，不运行 linter

#### Scenario: Negation removed, imperative remains

- **WHEN** 用户消息为 `提交代码`
- **THEN** 钩子进入门禁路径（既有祈使规则保持）
