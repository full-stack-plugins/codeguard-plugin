---
name: codeguard-elixir
license: Apache-2.0
description: |
  Elixir 代码规范：mix format 格式化 + Credo --strict 静态分析。
  Use when users write .ex/.exs files, hit credo warnings, or ask about Elixir idioms
  and formatting. Route Phoenix/OTP deep questions to official Elixir guides.
---

# Elixir 代码规范门禁

> 基于 [mix format](https://hexdocs.pm/mix/Mix.Tasks.Format.html)（内置）与 [Credo](https://hexdocs.pm/credo/)。

## Capability Boundaries

### ✅ Strengths
1. `mix format` 官方格式化（内置 code formatter，零配置基线）
2. Credo 静态分析：一致性/可读性/设计/警告 四大类
3. 项目内 `.credo.exs` 自定义规则

### ⚠️ Prerequisites
1. Elixir/OTP 工具链；项目 `mix.exs` 配置 `{:credo, "~> 1.7", only: [:dev, :test], runtime: false}`

### ❌ Out of Scope
1. Phoenix/OTP 深度设计 → 官方 Phoenix Guides / OTP 文档
2. 依赖 CVE → codeguard-security-code

## When to Use

- "elixir 规范" / "credo" / "mix format" / ".ex 文件检查"

## I. 强制项

```bash
mix format              # 格式化（codeguard 钩子默认 format 命令）
mix format --check-formatted   # CI 检查
mix credo --strict      # 静态分析（strict 提升部分规则优先级）
```

## II. Credo 规则族

| 类别 | 代表规则 |
|---|---|
| Consistency | 单引号 vs 双引号 一致性 |
| Readability | MaxLineLength（120）/ AliasOrder / ModuleNames |
| Design | AliasUsage（放 alias 顶部）/ DuplicatedCode |
| Warnings | UnusedVariableOperation / MapAccess |

## III. 模板要点

```elixir
defmodule MyApp.UserService do
  @moduledoc """
  用户业务逻辑。

  所有函数返回 `{:ok, result}` 或 `{:error, reason}`。
  """

  alias MyApp.Repo

  @max_retry 3

  @spec find_user(integer()) :: {:ok, map()} | {:error, :not_found}
  def find_user(id) do
    ...
  end
end
```

- `@moduledoc` / `@doc` 强制
- `@spec` 强制（Dialyzer 联动）
- 避免深层嵌套：`with` / `cond` / 早退模式

## Workflow

1. `mix format --check-formatted`（门禁）
2. `mix credo --strict`（静态分析）
3. 修复 → 复扫

## Gotchas

1. Credo 的 `Readability.ModuleNames` 对中文项目常误报 —— 按需 `--ignore` 并注释原因
2. `mix format` 会重排 import/alias —— 先 format 再人工精调
3. `strict` 模式的 Readability 规则优先级最高，团队可按需降级
