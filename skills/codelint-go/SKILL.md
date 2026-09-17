---
name: codelint-go
description: |
  Go 代码规范：go vet 基线 + golangci-lint 聚合 + gofmt 强制。禁止忽略 error 返回值。
  触发：用户说"Go 规范"、"go vet"、"golangci-lint"、"gofmt"。
---

# Go 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
go vet ./...                                    # codelint 钩子默认调用（内置）
golangci-lint run                               # 推荐的聚合 lint（可选安装）
gofmt -w .                                      # 自动格式化
gofmt -l .                                      # 列出未格式化文件
```

### 2. error 处理（Go 最重要的规范）

- **禁止** `_ = doThing()` 忽略 error 返回值（errcheck 会拦截）
- **禁止** `panic()` 在库代码中（只允许 main / init / 测试）
- 错误要包装上下文：`fmt.Errorf("load config: %w", err)`
- 哨兵错误用 `errors.Is` / `errors.As` 判断

### 3. 命名

- 导出标识符：`UpperCamelCase`；非导出：`lowerCamelCase`
- 缩写词保持一致大小写：`URL`、`ID`、`HTTP`（`userID` 而非 `userId`/`userId`）
- Getter 不加 `Get` 前缀：`user.Name()` 而非 `user.GetName()`
- 文件名：`snake_case.go`

### 4. 项目布局

- `cmd/<name>/main.go` 入口、`internal/` 私有包、`pkg/` 可导出包
- 一个目录一个包；包名与目录名一致、全小写、不用复数

### 5. 禁止使用

- `interface{}` / `any` 除非必要（Go 1.18+ 优先具体类型或泛型约束）
- `fmt.Println` 在生产代码（用 `log` / `slog`）
- 循环内 `defer`（易泄漏；确需则包一层函数）

## 常见错误速查

| 报错 | 含义 | 修复 |
|---|---|---|
| `declared and not used` | 声明未使用 | 删除或用 `_` 接收 |
| `errcheck: Error return value not checked` | error 未检查 | `if err != nil { return ... }` 或显式 `_ =`（注释原因） |
| `staticcheck: SA*` | 静态分析问题 | 按编号查 staticcheck 文档 |
| `gofmt: file is not formatted` | 格式不符 | `gofmt -w .` |
