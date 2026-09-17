---
name: codeguard-detect
license: Apache-2.0
description: |
  codeguard detect 命令：检测项目语言构成（扩展名扫描 + 项目标记文件），支持
  codeguard.json 自定义扩展映射与 exclude 排除。Use when users say "这是什么语言项目",
  "检测语言", or when initializing governance on a repo.
---

# codeguard detect

## Capability Boundaries

### ✅ Strengths
1. 55 种语言/文件类型识别（扩展名 + 文件名 + 项目标记文件三重）
2. 项目根 `codeguard.json` 自定义扩展映射（借鉴 codegraph 的零配置 + 可覆盖设计）
3. 输出 JSON，供其他工具/技能消费

### ⚠️ Prerequisites
1. 无（纯 Python 标准库）

### ❌ Out of Scope
1. 框架级识别（Spring/React 等框架探测在路线图）
2. 语言版本检测（.nvmrc / pom java.version 解析）

## 命令

```bash
bin/codeguard detect              # 当前目录
bin/codeguard detect path/to/pkg  # 指定目录
# 等价：python3 scripts/detect_lang.py path/
```

## 输出示例

```text
["java"]
["typescript", "vue"]
["go", "markdown"]
```

## 自定义扩展映射

项目根 `codeguard.json`：

```json
{
  "extensions": {
    ".dota_lua": "lua",
    ".tpl": "php"
  },
  "exclude": ["vendor/**", "generated/**"]
}
```

- `extensions`：合并/覆盖内置默认映射
- `exclude`：扫描时排除的文件模式（glob/正则字符串）
