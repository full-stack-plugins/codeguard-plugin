## Why

一次 14 项实弹审计（两个仓、几十次真实提交尝试）暴露了门禁层的成组缺陷：整调用拦截不声明"前序步骤也没执行"（AI 误判编辑被吞 ×3）、脚本间接完全绕过硬门禁（/tmp runner 连推 4 次漏网）、缓存键漏工作区改动（修完仍报旧失败的 retry-timing 陷阱）、非 git 目录回退扫描 cwd（工作区根被上百无关仓的存量 lint 变成永久红）、exit 2 工具崩溃被当成 lint 失败、全仓 format 静默重写无关文件（单文件保存炸出 30+ 漂移）、skipGate 只拦硬门不拦软门（放行与"禁止提交"自相矛盾）、双副本重复执行、绕过无记账、状态存安装目录升级即失。这些都可离线复现，且大多与既有 spec 的"无法验证≠验证失败"原则同向。

## What Changes

- 硬拦截反馈新增**整调用声明**：被拒的是一次完整 Bash 调用（含非 git 前序步骤），指令要求把修复与提交拆成独立调用。
- `is_guarded` 覆盖**一层解释器间接**（脚本文件与 `-c` 内联的静态扫描），封堵 `bash runner.sh` 式绕过。
- 门禁缓存键纳入**工作区内容指纹**（staged + 未暂存 + 未跟踪 stat），修完未暂存即失效。
- git 仓门禁缺省 **delta 作用域**（只查 staged/未暂存/未跟踪中属于该语言的文件；存量问题不拦新提交；`codeguard.json gate_scope` 可退回全量），全量模式剔除 vendor 等不可编辑目录。
- **exit 2 一律归未验证**（hook 路径 skipped、CLI/MCP `unverified` 标记），按既定"无法验证≠验证失败"。
- ruff 命令在项目无自有配置时注入 `linters/ruff/ruff.toml`（原生格式）默认规则集，判定不再随机器 ruff 漂移；新增 `scripts/scope.py` 承载作用域物化（detect_lang 保持 spec 规定的纯检测面）。
- PostToolUse 的 lint/format 物化到**单文件作用域**，自动修复后把被波及文件清单注入上下文；节选告警附总量与完整日志路径。
- `UserPromptSubmit` 非 git 目录显式跳过（一行说明），并与硬门禁**共用 skipGate**；软硬两门的绕过都记账，Stop 汇总显示绕过次数与 skipGate 遗留告警。
- 会话状态迁至 `~/.codeguard/session_state.json`（`CODEGUARD_HOME` 可覆盖），状态条目归一化防 KeyError-fail-open；双副本启用时 SessionStart 告警；PreToolUse/UPS 按宿主事件 id 去重。
- 仓库级 `format`（如 shellcheck severity 政策）与单文件 lint 对齐：`shell.lint` 增 `--severity=warning`，消除"保存时绿、提交时红"的政策分叉。
- `__protocol__.md` 指针从行号改为**符号级**定位并同步全部新语义。

## Capabilities

### New Capabilities

无。三项均落在既有能力上。

### Modified Capabilities

- `hook-protocol`: 硬拦截出口新增整调用声明要求；`is_guarded` 拦截条件扩展为直接+一层间接；新增软硬门禁共享 skipGate、非 git 目录不回退扫描的语义边界。
- `gate-trigger-policy`: 新增否定语境（未提交/别提交）不触发的回归要求。
- `language-gate-commands`: 新增 git 仓缺省 delta 作用域、exit 2 归未验证、单文件钩子命令不得全仓展开三条要求。

## Impact

改动面：`hooks/{gate_lib,pre_tool_git_guard,user_prompt_validator,post_tool_lint,stop_summary,env_check}.py`、`hooks/__protocol__.md`、新增 `scripts/scope.py` 与 `linters/ruff/ruff.toml`、`scripts/{paths,user_config,run_per_language,run_check,fix}.py`、`scripts/languages.json` + 重生成 `docs/LANGUAGES.md`、`tests/run_all.py`（delta 前提 3 处）+ 新增 `tests/test_hardening_fixes.py`（29 例）。退出码与 JSON schema 均未变——§1 协议总表字段原样，首行综述契约保持。CLI 行为变化：`check` 对 exit 2 显示 unverified（不计失败）、`fix` 缺省只修本次改动（`--all` 全仓）。
