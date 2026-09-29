# Rust 插件运行时锁候选验收

对应 Rust 仓 OpenSpec `introduce-rust-codeguard-cli` 的 S11.2、11.4、11.17；本记录只覆盖插件的显式候选入口。

2026-09-29：锁定的 `@partme.ai/codeguard@0.1.1` 仅支持 macOS arm64，固定注册表 tarball SHA-256、SHA-512 integrity、原生程序 SHA-256、候选源码提交及 check 协议 major。`node runtime/codeguard_runtime.cjs install --download` 从锁定 URL 下载，先核对包摘要和成员，再在私有暂存目录提取，核对 package 元数据、程序字节和 `--version --format=json`，然后切换 `active.json`；`verify` 在后续调用时重新核验。网络下载不会由普通 Hook 自动触发。

`node --test tests/test_rust_runtime.cjs`：3 通过、1 条依赖候选 tarball 的用例跳过。显式设置 `CODEGUARD_TEST_TARBALL=/tmp/partme.ai-codeguard-0.1.1.tgz` 后同一测试 4/4 通过，证明本地候选安装、真实 Rust SessionStart 调用、后续二进制篡改拒绝。错误 tarball 不发布 active；缺运行时的候选 Hook 回报“未完成/未运行”，前置 PATH 上的假 `codeguard` 未执行。另用真实注册表执行 `install --download` 退出 0，取得锁定摘要的内容寻址目录；这证明本机网络路径，不代表不同平台或宿主已验证。

插件既有 `tests/run_all.py` 144/144 通过；`/opt/anaconda3/bin/python3 -m unittest discover -s tests -p 'test_*.py' -q` 653 项通过。首次 Homebrew Python 3.14 全集出现中英文 README 新节未同步的 3 项失败及 Ruff 不在该解释器环境的 1 项失败；补齐双语段落后目标对齐测试通过，Python 3.13.5 全集通过。Ruff、架构边界、语言注册表、技能 vendor 离线和在线检查、OpenSpec strict 及 Agent Plugins 1.0.0 portable 验证均通过。根 `hooks/` 的候选脚本和协议说明已同步到 Copilot/OpenHands 镜像；Copilot 镜像入口也用真实候选二进制完成 SessionStart 观察。

当前默认 `hooks/hooks.json` 仍运行旧 Python 入口。候选尚未接入默认插件、修复事件、提示事件、真实 Git/CI 门禁或 Codex/ZCode/Kimi 实际宿主；跨进程租约崩溃恢复、原子目录发布的竞争/恶意同用户文件系统反例、最终可信来源与多平台锁也尚未验收。S11.2/11.4/11.17 保持未完成。旧 Python 的退出 0 不能升级为 Rust 门禁认证。
