---
name: codeguard-kotlin
description: |
  Kotlin 代码规范：detekt 静态分析 + ktlint 格式化（Gradle 插件）。
  触发：用户说"Kotlin 规范"、"detekt"、"ktlint"。
---

# Kotlin 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
./gradlew detekt           # codeguard 钩子默认调用（项目需配 detekt 插件）
./gradlew ktlintFormat     # 自动格式化
./gradlew lint             # Android 项目官方 lint
```

### 2. 命名

- 类/对象：`UpperCamelCase`
- 函数/变量：`lowerCamelCase`
- 常量（`const val` / 伴生对象）：`UPPER_SNAKE_CASE`
- 包：全小写

### 3. 惯用写法（detekt 会拦截）

- **禁止** `!!` 非空断言（用 `?.`、`?:`、`requireNotNull`）
- **禁止** 裸 `catch (e: Exception)` 吞异常
- 优先不可变：`val` 而非 `var`；集合用 `listOf` / `mapOf`
- 单表达式函数：`fun sum(a: Int, b: Int) = a + b`
- 数据类优先于手写 POJO：`data class User(val id: Long, val name: String)`

### 4. 作用域函数选择

| 函数 | 用途 |
|---|---|
| `let` | 空安全转换：`user?.let { ... }` |
| `apply` | 对象构建/配置：`Intent().apply { ... }` |
| `also` | 副作用（日志）：`user.also { log(it) }` |
| `run` / `with` | 计算并返回结果 |

## 常见错误速查

| detekt 规则 | 修复 |
|---|---|
| `MagicNumber` | 提取为命名常量 |
| `LongMethod` (>120 行) | 拆分函数 |
| `TooGenericExceptionCaught` | 捕获具体异常类型 |
| `UnusedPrivateMember` | 删除；`@Preview` 标注的 Compose 函数豁免 |
| `MaxLineLength` (>160) | 换行 |
