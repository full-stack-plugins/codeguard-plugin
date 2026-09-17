---
name: codelint-swift
description: |
  Swift 代码规范：SwiftLint 强制（brew 安装），含 force_cast / force_try 限制。
  触发：用户说"Swift 规范"、"SwiftLint"。
---

# Swift 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
brew install swiftlint       # 一次性安装
swiftlint                    # codelint 钩子默认调用
swiftlint --fix              # 自动修复
```

### 2. 命名（Swift API Design Guidelines）

- 类型/协议：`UpperCamelCase`（`UserService`、协议 `UserProviding`）
- 函数/变量/常量：`lowerCamelCase`
- 枚举 case：`lowerCamelCase`（`case .success`）
- 避免缩写：`url` / `id` 可用；`usr` / `svc` 不可

### 3. 可选值处理

- **禁止** `!` 强制解包（`force_cast` / `force_try` 默认告警）
- 优先 `if let` / `guard let`：
  ```swift
  guard let user = user else { return }
  ```
- 多重解包合并：`if let a = a, let b = b`（Swift 5.7+ 可 `if let a, let b`）

### 4. 惯用写法

- 优先 `let`（不可变）
- 尾随闭包省略参数名：`map { $0.name }`
- 计算属性代替无参方法（只读场景）
- `extension` 按协议组织一致性

## 常见错误速查

| SwiftLint 规则 | 修复 |
|---|---|
| `force_cast` | `as?` + `guard` |
| `force_try` | `try?` 或 `do-catch` |
| `line_length` (>160) | 换行 |
| `type_body_length` (>300) | 拆分类型 |
| `identifier_name` (<2 字符) | 改有意义命名（id/to/at 豁免） |
