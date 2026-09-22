## MODIFIED Requirements

### Requirement: The commit face SHALL match the actual staging surface

PreToolUse MUST 按可识别命令预测提交内容：纯 commit 使用 index，git add -A 使用工作树覆盖，git add -u / commit -a 不得纳入未跟踪文件，带路径 add 不得扩张到全仓。精确快照不得复用软门禁缓存。无独立基线时，项目命令在未修改文件上的失败 MUST 保留，不得按路径猜测历史债。无法完整建模的命令必须声明能力边界，不能作为全面验收证据。

#### Scenario: Plain commit with unrelated unstaged WIP in the worktree
- **WHEN** index 可提交且工作树存在无关 WIP
- **THEN** 在 index 快照检查，不检查 WIP 内容

#### Scenario: Chained add widens the face before commit runs
- **WHEN** git add 后接 commit
- **THEN** 按 add 的范围叠加工作树文件并保留删除影响

#### Scenario: Project-level linter fails only on files outside the changeset
- **WHEN** 项目级检查在未修改文件发现违规且没有独立基线证据
- **THEN** 保留失败，不归类为已知存量

## ADDED Requirements

### Requirement: Fail-open uncertainty SHALL be visible

PreToolUse 放行工具故障或无法物化快照时 MUST 使用 JSON additionalContext 说明未验证；UserPromptSubmit MUST NOT 对含未验证项的检查输出全部通过。PostToolUse 只提供反馈，strict_mode 不得被文档描述为已生效的阻断开关。

#### Scenario: A tool cannot run at the Git gate
- **WHEN** 工具缺失或配置导致无法获得检查结论
- **THEN** 保留 exit 0 的兼容放行，并明确未验证而不是 PASS
