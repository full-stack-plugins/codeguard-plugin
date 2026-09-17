---
name: codelint-csharp
description: |
  C# 代码规范：dotnet format 强制 + .editorconfig 风格。需要 .NET SDK 6+。
  触发：用户说"C# 规范"、"dotnet format"、"editorconfig"。
---

# C# 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
dotnet format --verify-no-changes   # codelint 钩子默认调用（.NET SDK 6+ 内置）
dotnet format                       # 自动修复
dotnet build                        # 编译期警告也是门禁的一部分
```

### 2. 命名（.NET 官方约定）

| 元素 | 规则 | 示例 |
|---|---|---|
| 类/结构/记录/枚举 | PascalCase | `UserService` |
| 接口 | I + PascalCase | `IUserRepository` |
| 方法/属性/事件 | PascalCase | `GetUserAsync` |
| 私有字段 | _camelCase | `_userRepository` |
| 参数/局部变量 | camelCase | `userId` |
| 常量 | PascalCase（.NET 惯例） | `MaxRetryCount` |

### 3. 异步规范

- 异步方法后缀 `Async`：`GetUserAsync`
- **禁止** `async void`（除事件处理器）
- **禁止** `.Result` / `.Wait()`（会死锁）——一路 `await` 到底
- 传递 `CancellationToken`

### 4. 禁止使用

- `catch (Exception) {}` 吞异常
- `public` 字段（用属性）
- 魔法字符串（用 const / enum / 常量类）

## 常见错误速查

| 报错 | 修复 |
|---|---|
| `IDE0005: using 指令不必要` | 删除未使用 using |
| `IDE0055: 格式化不符合 .editorconfig` | `dotnet format` |
| `CS8618: 不可为空属性未初始化` | 构造器初始化或声明为 `= null!`（注明原因） |
| `CA2007: await 缺少 ConfigureAwait` | 库代码加 `.ConfigureAwait(false)`；应用代码可在 .editorconfig 关闭 |
