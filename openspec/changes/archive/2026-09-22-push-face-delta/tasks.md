## 1. Specification

- [x] 1.1 MODIFIED delta（mode 拆分全文 + 5 个场景）
- [x] 1.2 `openspec validate --strict` 通过

## 2. Push face

- [x] 2.1 `scope.changed_files(mode=...)`：commit 三路 + push `up...HEAD` 三点差与回退链
- [x] 2.2 guard `_guarded_mode` 单源判定（直接+间接，push 优先）；`is_guarded` 由其派生
- [x] 2.3 `run_gate(mode=...)` + 缓存键带 mode；UPS 按 push/推送 词面选面并透传安全检查

## 3. Consistency

- [x] 3.1 `requiresConfig` 判定先于 probe（修无 yamllint 机器上的 yaml 测试失败）
- [x] 3.2 CLI exit 127 与 exit 2 同归 unverified（与钩子 skipped 口径对齐）
- [x] 3.3 SessionStart/Stop 按 session_id 双副本去重；`__protocol__.md` 四钩子规则与面语义同步
- [x] 3.4 README 双语：strict_mode 如实标注未接线 + 门禁作用域/绕过审计/未验证判定说明（parity 通过）

## 4. Verification

- [x] 4.1 回归测试：push 面 e2e（坏提交→push 拦、commit 放行）、UPS 双面、_guarded_mode 判定、rc127 unverified、四钩子去重
- [x] 4.2 全套终验：run_all / unittest / openspec --all / 门禁等价 lint
