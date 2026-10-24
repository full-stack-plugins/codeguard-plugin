# CodeGuard（代码质量防护）

> 19 条 CLI 已实现；check/fix/cve/dockerfile/impact 有真实执行入口。

**版本**：0.21.1 · **许可证**：Apache-2.0 · **技能**：68 个

> README parity note: tests/test_readme_parity.py

54 Stable adapters and 3 Planned adapters are recorded in scripts/languages.json.

54 个 Stable 适配器和 3 个 Planned 适配器记录在 scripts/languages.json.

[English](README.en.md)

## 项目定位

CodeGuard 是 Partme Guard 研发防护体系中的独立插件，命令前缀为 codeguard。它不依赖统一总命令，可独立安装、独立发版、独立执行。

## CLI 命令

退出码：0 通过 / 1 无法验证 / 2 存在漏洞 / 3 参数错误。

| 命令 | 类型 |
| :--- | :--- |
| install | 独立入口 |
| uninstall | 独立入口 |
| upgrade | 独立入口 |
| version | 独立入口 |
| doctor | 独立入口 |
| status | 独立入口 |
| discover | 独立入口 |
| init | 独立入口 |
| check | 独立入口 |
| fix | 独立入口 |
| cve | 独立入口 |
| dockerfile | 独立入口 |
| impact | 独立入口 |
| explain | 独立入口 |
| report | 独立入口 |
| hooks install | 独立入口 |
| hooks status | 独立入口 |
| engine | 独立入口 |
| completion | 独立入口 |

## 安装

~~~bash
codex plugin marketplace add partme-ai/full-stack-plugins
codex plugin add codeguard-plugin@full-stack-plugins
~~~

## 快速开始

~~~bash
codeguard version
codeguard doctor
codeguard status
~~~

## 当前状态

19 条 CLI 已实现；check/fix/cve/dockerfile/impact 有真实执行入口。

没有真实执行证据时，不报告 PASS；未实现能力报告 DESIGN_ONLY 或 UNVERIFIED。

## 架构

命令入口、生命周期、只读检查和证据边界见 product-docs/CodeGuard/ 与 docs/。

## 边界

- 不合并为 Partme Guard 总命令。
- 不替代其他 Guard 的专业判断。
- 不自动提交、推送或修改用户代码。

## 验证

~~~bash
python3 -m pytest -q
~~~

## 许可证

Apache-2.0
