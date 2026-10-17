# Rust 0.1.4 默认生命周期接线验收

对应 `2026-10-04-rust-lifecycle-default`；源码与清单接线不等于已安装宿主自动触发。

锁定 CLI 来源 `1cd458f6e01a44a74388243e964e3f45290ac18e`，tarball SHA-256 `a0d605f4a102e78d42766afaef61c6bd002556ccc5d16881c7553a91d6e20c80`，程序 SHA-256 `34c2490ff4ccaa04bce9e91efd6ccabff6d679e97b08966b1edba9b6aec37266`。38 普通成员与 32 许可证身份保持精确核对；程序与许可证每次调用复核。

先 RED：旧锁拒绝真实 0.1.4 注册表 tarball，默认 canonical Hook 未接 Rust；回归记录保留。GREEN 与注册表安装、延迟、全回归、远端 CI 和发行证据完成后在下方追加，未运行项不勾选。

当前默认 canonical SessionStart/UserPromptSubmit/PostToolUse/PostToolUseFailure/Stop 调用 Rust。Git PreToolUse、旧 CLI/MCP 与显式旧 Python Hook保留兼容入口。5 秒内部预算、8 秒子进程、10 秒 Hook 预算；全硬 I/O、缓存/性能和真实宿主仍待验收。未安装运行时显式反馈未完成，不自动下载或回退 Python。原生 Ruff/ESLint 的已实现范围优先，其它语种候选任务保留原生 adapter 缺口；32 grammar 仍未验收。

## 本机实际结果（2026-10-04）

- 固定注册表 0.1.4 tarball 的 8 项 Node 回归全部通过、0 failed、0 skipped：默认 manifest 选择、五类缺运行时反馈、真实公开包安装、真实保存/重复稳定任务、可执行 init/next/show/verify、真实 Zig 0.16.0 原生复检、Stop 重入、错误包及活动许可证/程序篡改拒绝。
- 实际默认入口读取 canonical manifest 的命令运行，不用单独候选入口替代默认接线；每次输出限 1200 字符，不回显宿主源码。init 返回 3/partial、next/show 返回操作成功 0，均不解释为质量通过。无可信政策时原生零诊断保留 open。
- 注册表 HTTPS 另在独立缓存安装并 activeBinary 核验成功，约 4068 ms；未写入用户的全局运行时缓存。普通生命周期没有下载。
- 三次独立 PostToolUse 本机重放耗时 406.7/337.8/337.0 ms；最终日志的更新测量见下列日志。此为小 Zig 文件、当前机器、直接默认入口重放，不是冷启动分布或实际宿主 p95。
- Python 兼容 unittest：655 passed、0 failed、0 skipped（使用已有 Framework Python 3.13，具备 Ruff/MCP）；插件集成：144 passed、0 failed、0 skipped；README 对齐 7/7。默认 Homebrew Python 3.14 缺 Ruff/MCP 的首次运行 1 failed/4 skipped，已保留该环境失败，不计成功。
- 技能 vendor 离线/在线检查、架构、Ruff、57 语言/11 schema 规则、便携插件与两份 Hook 镜像、两项 OpenSpec strict、diff 检查通过。未修改外部受管技能。
- 版本经生成器从已合并的未发布候选升级到插件 0.20.0，各平台 manifest 与市场 CodeGuard 元数据同步。远端 CI、GitHub release/tag、市场推送与已安装宿主证据须按后续真实结果补充。

## 日志身份

- `/tmp/codeguard-plugin-014-lock-red.log`：SHA-256 `116108f52fa9f47329e73941d9507869241764be9211c4d6058aa68088052f3c`。
- `/tmp/codeguard-plugin-default-green-final.log`：SHA-256 `8520d1e6a301bfc63d2ebd7682618ed77221711f3708c41d74633c7868f1a05e`。
- `/tmp/codeguard-plugin-lifecycle-unittest-final.log`：SHA-256 `5bd4a7de4e2075b1d92c14b472a55e3cb33db4176ee5eea02d0d6dd684472e55`。
- `/tmp/codeguard-plugin-lifecycle-e2e.log`：SHA-256 `920e7950d58d9f2aa4963429e4e0d56c188e15a657fb16d0d7d36505c12f53fc`。
