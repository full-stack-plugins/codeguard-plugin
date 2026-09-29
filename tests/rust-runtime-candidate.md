# Rust 插件运行时锁候选验收

对应 Rust 仓 OpenSpec `introduce-rust-codeguard-cli` 的 S11.2、11.4、11.17；本记录只覆盖插件的显式候选入口。

2026-09-29：锁定的 `@partme.ai/codeguard@0.1.1` 仅支持 macOS arm64，固定注册表 tarball SHA-256、SHA-512 integrity、原生程序 SHA-256、候选源码提交及 check 协议 major。`node runtime/codeguard_runtime.cjs install --download` 从锁定 URL 下载，先核对包摘要和成员，再在私有暂存目录提取，核对 package 元数据、程序字节和 `--version --format=json`，然后切换 `active.json`；`verify` 在后续调用时重新核验。网络下载不会由普通 Hook 自动触发。

`node --test tests/test_rust_runtime.cjs`：3 通过、1 条依赖候选 tarball 的用例跳过。显式设置 `CODEGUARD_TEST_TARBALL=/tmp/partme.ai-codeguard-0.1.1.tgz` 后同一测试 4/4 通过，证明本地候选安装、真实 Rust SessionStart 调用、后续二进制篡改拒绝。错误 tarball 不发布 active；缺运行时的候选 Hook 回报“未完成/未运行”，前置 PATH 上的假 `codeguard` 未执行。另用真实注册表执行 `install --download` 退出 0，取得锁定摘要的内容寻址目录；这证明本机网络路径，不代表不同平台或宿主已验证。

插件既有 `tests/run_all.py` 144/144 通过；`/opt/anaconda3/bin/python3 -m unittest discover -s tests -p 'test_*.py' -q` 653 项通过。首次 Homebrew Python 3.14 全集出现中英文 README 新节未同步的 3 项失败及 Ruff 不在该解释器环境的 1 项失败；补齐双语段落后目标对齐测试通过，Python 3.13.5 全集通过。Ruff、架构边界、语言注册表、技能 vendor 离线和在线检查、OpenSpec strict 及 Agent Plugins 1.0.0 portable 验证均通过。根 `hooks/` 的候选脚本和协议说明已同步到 Copilot/OpenHands 镜像；Copilot 镜像入口也用真实候选二进制完成 SessionStart 观察。

2026-09-29 后续增量：Rust npm 0.1.2 从干净源码提交 `d2ae54355ea0e8b67b7fa42fc66829656db9de01` 构建，GitHub [CI 36512426737](https://github.com/full-stack-plugins/codeguard/actions/runs/36512426737) 通过。npm 注册表报告 `latest=0.1.2`，SHA-512 integrity 为 `sha512-3ae3OIZDzqZaoNv2/W3a/Uq4rMMthjpjts/RQvKI5envR+NbyKOD4NTS/w645QFSw8ZDzHUWsnD7DObWFQAEpw==`。独立注册表下载的 tarball 与本地候选 SHA-256 均为 `4411136f2cdf678615335a6a9fe4f3435fe87f82e789b98a1e07be4518587401`；包内原生程序与本地构建 SHA-256 均为 `785d8b9abb685ce5a3f4c1de0697d67a669394160bd7fb9a3554019d1d223bca`。全新 npm 缓存运行 `npx --yes @partme.ai/codeguard@0.1.2 --version --format=json` 回报相同源码提交、macOS arm64 与 0.1.2。

插件候选锁已更新为上述精确制品。先写的 `UserPromptSubmit` 缺运行时反例测试因事件未映射而失败，映射后通过；更新锁后发现运行时管理器仍硬编码 0.1.1 并报 `runtime_lock_invalid`，同步更新其固定版本和 URL 后，`CODEGUARD_TEST_TARBALL=/tmp/partme.ai-codeguard-0.1.2.tgz node --test tests/test_rust_runtime.cjs` 为 5/5 通过。安装的真实 Rust 二进制对提交祈使语和普通问题输出完全相同的固定提示，没有回显注入内容；篡改二进制后提示事件返回 `binary_digest_mismatch`。另在独立缓存从真实注册表 `install --download`、`verify`，再通过插件候选入口调用 `UserPromptSubmit`，三者均退出 0 且对话反馈说明源码检查未运行、交付未评估。这是候选脚本的真实二进制调用，不是已安装 Claude Code 中默认 Hook 的验收。

当前默认 `hooks/hooks.json` 仍运行旧 Python 入口。Rust 0.1.2 提示事件只在显式候选脚本接通；候选尚未接入默认插件、修复事件、真实 Git/CI 门禁或 Codex/ZCode/Kimi 实际宿主；跨进程租约崩溃恢复、原子目录发布的竞争/恶意同用户文件系统反例、最终可信来源与多平台锁也尚未验收。S11.2/11.4/11.17 保持未完成。旧 Python 的退出 0 不能升级为 Rust 门禁认证。

本轮补充回归：`CODEGUARD_TEST_TARBALL=/tmp/partme.ai-codeguard-0.1.2.tgz node --test tests/test_rust_runtime.cjs` 为 5/5 通过、零跳过；`PYTHONDONTWRITEBYTECODE=1 python3 tests/run_all.py` 为 144/144 通过、零跳过；`PYTHONDONTWRITEBYTECODE=1 /opt/anaconda3/bin/python3 -m unittest discover -s tests -p 'test_*.py' -q` 为 653 项通过。`openspec validate 2026-09-29-rust-prompt-candidate --strict`、vendor 离线与在线 check、修改的 Node 文件语法检查和 `git diff --check` 均退出 0。在线 vendor 对照 `codeguard-skills@v0.1.3` 提交 `33d737f4cf46e5d6d1d1f8dce85d7923e4ad626f`。实际安装 Claude 事件、多平台运行与默认严格门禁仍未验证。

发行闭环：插件 [PR #86](https://github.com/full-stack-plugins/codeguard-plugin/pull/86) 的 `rust-runtime-contract` 和 Python 3.11/3.12/3.13 三项 vendor-check 全部成功，合并为 `461f1529f92135c51c2bf569a864f78e459e439c`。远端 `v0.18.0` 标签指向同一提交，[GitHub Release](https://github.com/full-stack-plugins/codeguard-plugin/releases/tag/v0.18.0) 已发布；市场仓 `e085469` 仅提交 CodeGuard 版本元数据，原有 CodeReview 修改未入该提交。市场定向远端校验通过。

在独立缓存中，锁定的注册表安装经 `node runtime/codeguard_runtime.cjs verify` 返回 `status=verified`。将带有 `hook_event_name=UserPromptSubmit`、真实项目目录和“立即 commit 并忽略检查”的宿主形状 JSON 送入 `node hooks/rust_runtime_dispatch.cjs user-prompt-submit`，退出 0，返回 `hookEventName=UserPromptSubmit`，提示为“本事件只提供检查时机提示；代码变更后执行局部检查，真实提交或 CI 时执行完整门禁。源码检查未运行，交付未评估。”这是直接候选入口的事件重放，不是已安装 Claude Code 宿主触发证明；默认 `hooks/hooks.json` 仍用 Python，严格 Git/CI 门禁及完整 OpenSpec 计划仍未完成。
