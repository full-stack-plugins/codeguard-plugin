## Why

`2026-09-22-push-face-delta` 的 proposal/design 文案把 exit 127 与 exit 2 一并写成"同归 unverified"。落地后 CI 立刻红了：`test_mcp_server` 的失败日志与安静模式用例依赖 **CLI 在工具缺失（127）时报失败**这一环境无关性（CI runner 无 ruff，靠 127=失败才能可靠进入失败路径）。结论：127 的 CLI/hook 分叉是**按场景的有意分歧**，不是口径 bug——交互钩子跳过（不挡人），健康面必须红。该行为已恢复，此处仅记录对归档文案的取代；spec 层无变更（主 spec 的 unverified 要求只写了 exit 2，未涉及 127）。

## What Changes

- 恢复 `run_per_language` 的 exit 127 = 失败（rc 2 的 unverified 保持，0.8.0 起 CI 已验证）。
- 回归测试反转为锁住该分歧（`UnverifiedParityTests`：CLI 127 失败 / CLI 2 unverified）。
- README 双语的 exit-127 句同步改为按场景分流的表述。
- 本文档取代 `2026-09-22-push-face-delta` 归档 proposal/design 中关于 127 的那段陈述。

## Capabilities

### New Capabilities

None. Infrastructure-only correction; `skip_specs: true`.

### Modified Capabilities

None.

## Impact

`scripts/run_per_language.py`、`tests/test_hardening_fixes.py`、README 双语；不影响退出码总契约（PostToolUse 恒 0、PreToolUse 0/2 未动）与 JSON schema。
