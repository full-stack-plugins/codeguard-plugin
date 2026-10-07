## 1. 固定制品与可执行指引

- [x] 1.1 先验证旧锁拒绝 0.1.4，再固定注册表 tarball、程序、源码与许可证身份；原生版本不可从 PATH 替换。
- [x] 1.2 增加受限 init/next/task show/task verify 转发；未支持命令不运行，参数由 Rust 校验。

## 2. 默认生命周期接线

- [x] 2.1 默认 canonical Hook 接通五类非阻断事件、保留原 Git 兼容门禁；缺运行时明确未完成且不下载/回退。
- [x] 2.2 真实固定公开程序经 manifest 入口完成 init、编辑、重复任务、失败编辑、next、原生复检、Stop 重入；摘要脱敏有界，问题仍需可信复检关闭。
- [x] 2.3 测量默认入口冷/重复调用时间，核对子进程及宿主预算；记录无法核验的硬 I/O 与真实宿主范围。
- [ ] 2.4 用实际安装 Claude/Codex/ZCode/Kimi 等宿主验证自动触发、对话可见、权限及失败恢复；直接脚本重放不能代替。

## 3. 交付

- [x] 3.1 更新双语 README、canonical 协议和验收记录，区分当前默认入口与兼容宿主镜像。
- [ ] 3.2 执行 Node/Python 回归、vendor 离线/在线、OpenSpec strict、manifest/README/架构检查与远端 CI。
- [ ] 3.3 经生成器版本升级，发布 tag/release、同步市场并核对本地/远端身份；受保护分支限制真实反馈。

本机证据：`tests/rust-lifecycle-default.md`。2.4 真实宿主、3.2 远端 CI、3.3 发布/市场保留开放。
