# UserPromptSubmit matcher 纠错验收

2026-09-29：[Claude Code Hooks reference](https://code.claude.com/docs/en/hooks) 明确把 `UserPromptSubmit` 列为不支持 matcher、每次事件均触发的类型。改动前，根 `hooks/hooks.json` 与 Copilot/OpenHands 镜像都声明了提交关键词 matcher；该字段不能承担宿主侧提示过滤，且默认超时为 120 秒。

先增加反例：三份清单必须无 `matcher`，普通问题即使带 `session_id` 也不得进入会话/worktree 归属、PATH 探测、仓库发现、软检查或对话输出。初次目标测试因三份清单的 matcher 失败；移除字段后，再把 `session_scope` 设为失败哨兵，测试因普通问题先做会话归属而失败。`user_prompt_validator.main` 将意图预检前移后，目标测试通过。提交意图仍由旧 `prompt_application` 处理；实际 Git 命令仍由 PreToolUse 守卫。没有把关键词 matcher 换成对话内容信任源。

最终本地证据：目标测试通过；`tests/run_all.py` 144/144 通过、零跳过；Python 3.13.5 `unittest discover` 654 项通过；`tests.test_readme_parity` 7 项通过；真实候选 tarball 的 Node runtime 测试 5/5 通过。Ruff、OpenSpec strict、vendor 离线/在线 check、协议文档三份镜像比较、市场定向生成校验和 `git diff --check` 均退出 0。在线 vendor 对照 `codeguard-skills@v0.1.3` 提交 `33d737f4cf46e5d6d1d1f8dce85d7923e4ad626f`。

本次减少的是普通提示进入仓库观察的工作量，并纠正无效配置；**宿主仍会为每条提示启动 Hook 进程**。未在已安装 Claude Code 中测量启动延迟，未切换默认 Rust 候选，也未证明完整交付门禁或 Rust OpenSpec 总计划已完成。
