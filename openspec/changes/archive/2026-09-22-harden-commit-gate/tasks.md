## 1. Specification

- [x] 1.1 三份 delta spec（hook-protocol / gate-trigger-policy / language-gate-commands）
- [x] 1.2 `openspec validate --strict` 通过

## 2. Hard-gate semantics

- [x] 2.1 gate_directive 追加整调用声明（首行综述契约保持）
- [x] 2.2 is_guarded 直接 + 一层间接（脚本文件与 -c 内联）；边界在 docstring 声明
- [x] 2.3 skipGate 命中记账（env/两门双通路）；resolve_project_roots cd 语义注释

## 3. Scope and reproducibility

- [x] 3.1 缓存键加工作区内容指纹（staged/未暂存/未跟踪）
- [x] 3.2 git 仓缺省 delta 作用域 + `gate_scope` 项目级覆盖 + 全量剔除 vendor
- [x] 3.3 `scripts/scope.py` 承载物化（detect_lang 回到 spec 白名单面）
- [x] 3.4 ruff 原生默认配置注入（项目自有配置时不注入）
- [x] 3.5 `shell.lint` 对齐 severity 政策 + 重生成 LANGUAGES.md

## 4. Verdict honesty and feedback quality

- [x] 4.1 exit 2 → hook skipped / CLI-MCP unverified 标记
- [x] 4.2 节选附总量 + 完整日志路径（gate 与 post 两处）
- [x] 4.3 PostToolUse lint/format 单文件物化 + 波及文件清单注入
- [x] 4.4 fix.py 缺省 delta、`--all` 全仓

## 5. Governance

- [x] 5.1 UPS 非 git 目录显式跳过（不回退扫描 cwd）
- [x] 5.2 UPS 与硬门禁共享 skipGate；否定语境回归测试
- [x] 5.3 状态迁 `~/.codeguard/session_state.json` + 条目归一化 + Stop 绕过/skipGate 提醒
- [x] 5.4 双副本 SessionStart 告警 + PreToolUse/UPS 事件去重
- [x] 5.5 run_all delta 前提 3 处修正；新增 `tests/test_hardening_fixes.py`（29 例）
- [x] 5.6 `__protocol__.md` 符号定位与新语义同 commit 同步
