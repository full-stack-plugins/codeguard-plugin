# Codeguard 能力注册表摘要

本摘要用于路由，不替代运行时 `languages.json`。发布前应由 `references/languages.json` 重新核对。

## 当前快照

| 项目 | 数量 |
|---|---:|
| 语言/文件类型配置 | 57 |
| `stable` | 53 |
| `planned` | 4 |
| 核心治理技能 | 11 |
| 包内技能总数 | 68 |

`planned`：Ansible、ArkTS、COBOL、Metal。它们可以被识别和路由，但在运行时注册表没有可执行门禁前，不得报告 lint PASS。

## 路由顺序

1. 不知道项目语言：`codeguard-detect`。
2. 需要只读质量结论：`codeguard-check`。
3. 已有确定性 lint 失败且允许修改：`codeguard-fix`。
4. 依赖漏洞与供应链：`codeguard-cve`。
5. 新仓库接入：`codeguard-init`。
6. 分支/提交治理：`codeguard-git-branch` / `codeguard-git-commit`。
7. 代码、API、数据安全：三个 `codeguard-security-*` 技能。
8. 语言门禁细节：`codeguard-<language>`。

## 证据边界

- 注册表中的 `stable` 表示运行时有门禁命令，不表示目标项目已安装工具或检查已通过。
- 技能中的命令是操作契约，不表示 `codeguard-skills` 包携带 CLI。
- 任何 PASS 仍需目标仓库中的真实命令、作用域、工具版本和退出码。
