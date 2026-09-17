---
name: codeguard-yaml
license: Apache-2.0
description: |
  YAML 规范：yamllint（缩进/行宽/重复键/真值写法）检查与修复。
  Use when users write .yml/.yaml files (CI configs, k8s manifests, compose files),
  hit yamllint errors, or ask about YAML indentation and style.
  Route k8s resource semantics to kubeconform/kyverno; Ansible playbooks to ansible-lint.
---

# YAML 规范门禁

> 基于 [yamllint](https://yamllint.readthedocs.io/)。配置模板：`linters/yaml/.yamllint.yml`。

## Capability Boundaries

### ✅ Strengths
1. yamllint 全规则（缩进/行宽/重复 key/真值风格/空行）
2. GitHub Actions / k8s manifests / compose files 通用
3. `truthy.check-keys: false` 兼容 `on:` 键（Actions 触发器）

### ⚠️ Prerequisites
1. `pip install yamllint`

### ❌ Out of Scope
1. JSON schema 校验 → 各平台专用工具
2. YAML 内容语义（k8s 资源合法性）→ kubeconform/kyverno
3. Ansible playbook 语义 → ansible-lint

## When to Use

- "yaml 报错" / "yamllint" / "CI 配置检查" / "k8s yaml 规范"

## I. 强制项

```bash
yamllint .            # 门禁命令（codeguard 钩子默认）
yamllint -d relaxed . # 宽松模式（仅 error）
```

配置基线（.yamllint.yml，见 `linters/yaml/.yamllint.yml`）：
- 行宽 ≤160（warning 级）
- 缩进 2 空格；序列一致缩进
- `on:` 键不判 truthy（GitHub Actions 兼容）
- 不强制文件首 `---`

## II. 高频错误速查

| 规则 | 修复 |
|---|---|
| `dup` 重复 key | 合并或删除 |
| `indentation` 混用 tab/空格 | 统一空格 |
| `trailing-spaces` | 去除行尾空格 |
| `missing-new-line-at-end` | 文件末补换行 |
| `key-duplicates` | 同 key 只出现一次 |
| `octal-values` | 八进制 0 前缀加引号 |

## Workflow

1. 写/改 `.yml` → codeguard 钩子自动 yamllint
2. 有告警 → 按规则修复或 `yamllint -d relaxed` 排除噪音
3. 提交前复扫

## Gotchas

1. GitHub Actions 的 `on:` 在 YAML 1.1 里是布尔键——yamllint 默认 truthy 检查会误报；模板已配 `check-keys: false`
2. 多文档（`---` 分隔）文件需 `document-start: false` 或逐文档校验
3. Ansible playbook 建议改用 ansible-lint（语义级）而非 yamllint（格式级）
