# language-gate-commands（增量）：zsh 不进 shellcheck 目标面

## ADDED Requirements

### Requirement: Unsupportable script dialects SHALL stay out of the linter target face

ShellCheck 不支持 zsh；shell 生态的 `.zsh` 文件 MUST 被识别为 shell 语言，
但 MUST NOT 进入 shellcheck 的目标面（全量 gate 与 delta 面均需剔除）。剔除
MUST 明示「N 个 zsh 文件未验证（ShellCheck 不支持 zsh）」，MUST NOT 静默丢弃。

#### Scenario: Only zsh files changed
- **WHEN** 本次改动仅涉及 `.zsh` 文件
- **THEN** shell 门禁放行，并明示 zsh 文件未验证

#### Scenario: Mixed sh and zsh changes
- **WHEN** 本次改动同时涉及 `lib.sh` 与 `run.zsh`
- **THEN** 仅 `lib.sh` 进入 shellcheck，`run.zsh` 计入未验证说明

#### Scenario: Full-scan gate never hands zsh to shellcheck
- **WHEN** 全量 shell gate 执行 find 型命令
- **THEN** find 目标模式 MUST NOT 包含 `*.zsh`
