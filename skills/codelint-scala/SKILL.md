---
name: codelint-scala
description: |
  Scala 代码规范：scalafmt 强制（--check 即门禁）+ import 排序。
  触发：用户说"Scala 规范"、"scalafmt"、"scalafix"。
---

# Scala 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
coursier install scalafmt       # 一次性安装
scalafmt --check                # codelint 钩子默认调用
scalafmt                        # 自动格式化
```

静态分析推荐另配 scalafix（语义级规则）。

### 2. 命名

- 类型/特质：`UpperCamelCase`
- 方法/变量：`camelCase`
- 常量：`camelCase`（Scala 社区惯例，非 UPPER_SNAKE）或 UPPER_SNAKE（团队统一即可）

### 3. 惯用写法

- 优先不可变集合：`List` / `Vector` / `Map`（默认 `scala.collection.immutable`）
- **禁止** `null` / `getOrElse(null)`——用 `Option` / `Either`
- **禁止** `return`（最后表达式即返回值）
- 用 `for` 推导替代嵌套 `map`/`flatMap` 链
- 隐式转换克制使用；Scala 3 优先 `given` / `using`

### 4. import 规范

- scalafmt 自动排序（rewrite.rules = SortImports）
- **禁止** 通配 `import foo._` 除非确实需要全部

## 常见错误速查

| 问题 | 修复 |
|---|---|
| `scalafmt --check` 失败 | `scalafmt`（重新格式化） |
| 行宽超 120 | 调用链换行（`.map { ... }` 竖排） |
| `Type mismatch` | 多为 Option/Either 单子错配，用 for 推导理顺 |
| import 未排序 | scalafmt 自动修 |
