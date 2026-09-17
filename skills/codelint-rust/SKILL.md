---
name: codestyle-rust
description: |
  Rust 专项代码规范：clippy strict + rustfmt 强制。禁止 unwrap/expect/panic 在业务代码。
  触发：用户说"clippy"、"rustfmt"、"rust 规范"、"cargo clippy"。
---

# Rust 代码规范

## 强制项（违反必须修复）

### 1. clippy deny warnings

```bash
cargo clippy --all-targets -- -D warnings
```

- **`#![deny(warnings)]`** 或 `clippy.toml` 设 `deny-warnings = true`
- **禁止**业务代码使用 `unwrap()`、`expect()`、`panic!()`
- **禁止** `dbg!()` 调试代码遗留
- **禁止** `unimplemented!()`、`todo!()`（CI 必须通过）

### 2. rustfmt

```bash
cargo fmt --all -- --check   # CI 检查
cargo fmt                    # 本地自动修复
```

### 3. 命名

- 函数/变量：`snake_case`
- 类型/枚举：`UpperCamelCase`
- 常量：`UPPER_SNAKE_CASE`
- 模块：`snake_case`
- 生命周期：`'a`、`'static` 等单引号小写

### 4. 错误处理

- 业务代码必须 `Result<T, E>` + `?` 操作符，**不用 unwrap**
- 库代码 `panic!` 仅限不可恢复错误
- 自定义错误用 `thiserror` 派生

### 5. 推荐工具

- **cargo-deny**：依赖审计
- **cargo-audit**：安全漏洞扫描
- **cargo-machete**：检测未使用的依赖

## clippy.toml 模板

```toml
deny(warnings)
warn(clippy::all, clippy::pedantic)
deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::dbg_macro,
    clippy::todo,
    clippy::unimplemented,
)
```

## 测试代码豁免

`tests/` 目录允许 `unwrap` / `expect`（测试期望失败是正常用例）：

```rust
#[cfg(test)]
mod tests {
    #[test]
    fn should_fail() {
        let result = std::panic::catch_unwind(|| {
            do_thing() // 内部 unwrap 在测试里可以
        });
        assert!(result.is_err());
    }
}
```

## 常见错误速查

| clippy lint | 含义 | 修复 |
|---|---|---|
| `unwrap_used` | 用了 `.unwrap()` | 改 `?` 或 `match` |
| `expect_used` | 用了 `.expect()` | 改 `Result` 传播 |
| `panic` | 用了 `panic!()` | 改返回 `Err` |
| `dbg_macro` | 用了 `dbg!()` | 删除或换 `eprintln!` |
| `needless_return` | 函数末尾无意义的 `return` | 改为表达式返回 |
| `too_many_arguments` | 函数参数过多（>7） | 引入参数对象 |
