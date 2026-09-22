## Why

delta 作用域落地后出现了一个由它自己引入的空洞：**推送面失守**。坏改动一旦被提交（绕过门禁的提交、装插件之前的提交、用户手动提交），工作树即干净——`git push` 前的门禁按"本次改动"得到空集，全语言"未涉及"跳过，推送畅通无阻（实测：坏提交入史后 commit 面返回 `[]`）。提交门禁防的是"这次要提交什么"，推送门禁必须防"这次要送出什么"——两者不是同一组文件。同批还修两处一致性：`requiresConfig`（未接入）判定排在探活之前（纯文件系统判定更快且更根本，本机无 yamllint 时既有 yaml 测试因顺序报错消息不对而失败）；CLI 对 exit 127（命令不存在）按失败上报，与钩子路径的 skipped 口径分叉。

## What Changes

- `changed_files` 增加 `mode`：`commit` 面 = staged + 未暂存 + 未跟踪；`push` 面 = 提交面 ∪ 未推送提交（`up...HEAD` 三点差，无 upstream 时按 `origin/<branch>`→`origin/main`→`origin/master` 逐个尝试，均不可解析则保持空、不崩）。
- 硬门禁新增 `_guarded_mode`：直接命令与一层解释器间接共用同一套扫描，命中即返回生效面（commit/push 并存时 push 优先——推送面是提交面的超集）；`is_guarded` 即其存在性判断，命中与选面不分叉。`run_gate`/缓存键携带 mode（同 HEAD 下两面文件集不同，不带 mode 会互相污染缓存）。
- `UserPromptSubmit` 按提示词 `push/推送` 选同一套面，透传给 `run_gate` 与提交内容安全检查——软硬两门永远看同一组文件。
- `run_per_language`：exit 127 与 exit 2 同归 unverified（此前 CLI 报失败、钩子报 skipped，口径分叉）。
- 顺带完成双副本去重的补齐：SessionStart/Stop 也按 `session_id` 去重（四钩子同一规则），`__protocol__.md` 同步。
- README 双语如实化：`strict_mode` 标注为保留未接线（实测零消费；其声称的"PostToolUse exit 2 阻塞"与协议 §1 恒 exit 0 矛盾），并新增门禁作用域/绕过审计/未验证判定说明。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `language-gate-commands`: "Gates in git repositories SHALL default to changed-file scope" 增加 mode 拆分与推送面场景（原 requirement 全文随 MODIFIED 更新）。

## Impact

`scripts/scope.py`、`hooks/gate_lib.py`、`hooks/pre_tool_git_guard.py`、`hooks/user_prompt_validator.py`、`scripts/run_per_language.py`、`hooks/{env_check,stop_summary}.py`、`hooks/__protocol__.md`、README 双语、新增回归测试。退出码与 JSON schema 不变。行为变化：推送前会检查未推送提交里的问题；CLI 的 127 改报 unverified。
