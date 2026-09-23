# 2026-09-23-save-scope-lock-and-doc-parity

## Why

用户指令（2026-09-23）：按建议优化发现的问题。收敛为三件：

1. **save 面 auto-fix 范围零测试锁定**：P0「PostToolUse 全仓 format 静默重写无关文件」的机制面
   已由并行批次修复（`scoped_plan` scope=save 收束单文件 + `touched_others` 显式告警），但**没有任何
   测试锁住该行为**——回退即复发，且这类回归正是「改一个文件冒出无关 diff」的源头。
2. **`CODEGUARD_SKIP_GATE` 真值缺陷**：`bool(os.environ.get(...))` 只判断存在性——`=0`/`=false`
   也会**静默关闭门禁**（实测），而 `git config codeguard.skipGate` 路径是严格词表解析，
   两条豁免路径值语义不一致；`gate_directive` 文案称环境变量「只对手动直调 run_check 有效
   （无法传入宿主钩子进程）」，但 `pre_tool_git_guard`/`user_prompt_validator` 都真实读取它——
   又一例文档与行为矛盾。
3. **文档断言无机制约束**：「文档与行为矛盾」家族本会话累计 7 例（--ecosystem java 静默失效、
   trivy 兜底未接线、LANGUAGES 双向漂移、markdown 缺 glob、绕过机制文案、…）。需要把
   **可执行的文档断言钉在行为测试上**，让矛盾在 CI 现形而不是靠会话考古。

## What Changes

- `env_skip_gate()` 单一解析器：环境变量豁免只认 `1/true/yes`（与 git config 同词表），
  两个钩子调用点统一接入；`gate_directive` 文案改为与行为一致的准确表述。
- save 面 auto-fix 范围行为以回归测试锁定三态：scan token 收束单文件、`{file}` 替换、
  裸命令文件追加；越界触碰（format 改到别的文件）必须显式告警。
- 新增 `tests/test_doc_behavior_parity.py`：文档中的可执行断言（绕过值词表、生态别名、
  点前缀语义、markdown probe 形态、CVE 退出码）与真实行为逐条互证，矛盾即红。

## Capabilities

### New Capabilities

- `doc-behavior-parity`：文档可执行断言必须被测试钉在行为上，矛盾可被 CI 检出。

### Modified Capabilities

无（save 范围与豁免值语义以 ADDED requirement 并入 hook-protocol）。

## Impact

- `scripts/codeguard/repository_policy.py`（env_skip_gate）、`hooks/pre_tool_git_guard.py`、
  `hooks/user_prompt_validator.py`（调用点）、`scripts/codeguard/reporting.py`（文案）。
- 新测试两个模块。行为变更：`CODEGUARD_SKIP_GATE=0`/`false` 不再豁免（此前静默关闭门禁）。
- 发版 v0.15.4。
