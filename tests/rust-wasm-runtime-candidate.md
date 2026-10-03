# 32 语法 WASM 候选运行时验收

对应 `openspec/changes/2026-10-03-rust-wasm-runtime-candidate/`。本记录验证插件显式候选安装器对 CodeGuard CLI `0.1.3` 的调用，不代表默认 Hook 已自动执行 WASM 检查。

## 制品与边界

- 来源提交：`7900a1a8ccd5b4f5b54de8b5db3ccba16a356d3b`；npm 包：`@partme.ai/codeguard@0.1.3`，macOS arm64。
- 本地与注册表 tarball 的 SHA-256 均为 `37509cdd108fee631eebb9ebcd794a6e8d63652801b3522625d0909c3da2ae12`；包内程序 SHA-256 为 `04bdea8c489693a8e97b451df8d0c2b7a89ba82372db5a4d1fed277ba19b0f4d`。
- 锁定 38 个普通 tar 成员：原有 6 个文件、32 个 grammar 许可证文件。压缩包上限 16 MiB、程序上限 128 MiB、单份许可证上限 16 KiB。先核对完整 tarball 摘要及精确成员，再提取到私有暂存目录；激活及后续调用均复核程序和 32 份许可证摘要。
- 使用 `node runtime/codeguard_runtime.cjs install --download` 与 `verify` 从注册表完成独立缓存安装和核验，均退出 0。普通 Hook 不自动下载。

## 候选能力与测试

- `CODEGUARD_TEST_TARBALL=/tmp/partme.ai-codeguard-0.1.3.tgz node --test tests/test_rust_runtime.cjs`：5/5 通过、零跳过。覆盖错误 tarball、缺运行时、现有 Claude 候选事件、活动许可证及程序篡改拒绝。
- 安装后的真实程序 `grammar status --format=json` 返回 32 个候选、0 个已发布、`delivery_decision=not_evaluated`，退出 3；通过插件的 `exec grammar status --format=json` 得到同样的库存和退出码。
- 插件 `exec check all <项目物理绝对路径> --format=json` 对 Zig 样例返回 `delivery_decision=incomplete`，`syntax_candidates.observations` 含 `candidate_observed`；不会把候选观察升级为通过。
- 真实 Zig 文件的 `grammar probe zig <物理绝对路径> --format=json` 返回 `grammar_candidate_probe`、`grammar_qualified=false`、`delivery_decision=not_evaluated`，退出 3。macOS `/var` 为 `/private/var` 的别名，测试以 `realpath` 传入源码，避免路径安全校验与 grammar 能力混淆。
- CodeGuard Rust 仓以 `CODEGUARD_WASM_BIN=$PWD/target/release/codeguard node --test --test-name-pattern='统一 check all 调用全部 32' tests/npm_pack_wasm.test.mjs` 运行真实离线 npm 包，1/1 通过。测试按每组 8 个文件调用统一 `check all`，最终观察语言集合精确等于 32 份 manifest 资产；该能力属于 CLI 0.1.3，插件默认 Hook 尚未接通。
- 插件 `PYTHONDONTWRITEBYTECODE=1 python3 tests/run_all.py` 为 144/144 通过；Python unittest 为 654/654 通过；README 中英文对齐 7/7 通过；技能 vendor 离线与在线检查、OpenSpec strict、修改的 Node 语法检查及 `git diff --check` 均通过。
- 本机五次新进程 `verify` 耗时 86.1、78.8、78.5、79.9、80.3 ms，中位数 79.9 ms；这是安装器复核耗时，不是宿主 Hook 端到端延迟。

## 未验收能力

32 份 WASM 均为**可调用候选资产**，不是 32 种已验收语法检查。当前默认 `hooks/hooks.json` 仍调用 Python；现有 Rust `PostToolUse` 尚未把 32 种 WASM 的检查结果自动注入智能体对话，候选也未接严格 Git 门禁。原生 lint 优先级、各语言误报率、真实宿主事件、跨平台制品与 CI 门禁仍须分别验证。候选返回 `not_evaluated` 不能被解释为代码通过或替代原生 lint。
