---
name: codelint-ruby
description: |
  Ruby 代码规范：RuboCop 强制（单引号、行宽 160、method 长度 20）。
  触发：用户说"Ruby 规范"、"RuboCop"。
---

# Ruby 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
gem install rubocop       # 一次性安装
rubocop                   # codelint 钩子默认调用
rubocop -A                # 自动修复（-a 只修安全项）
rubocop -L                # 只列违规文件
```

### 2. 命名

| 元素 | 规则 | 示例 |
|---|---|---|
| 类/模块 | CamelCase | `UserService` |
| 方法/变量 | snake_case | `find_user` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY` |
| 文件名 | snake_case.rb，与类名对应 | `user_service.rb` |

### 3. 惯用写法（RuboCop 默认拦截）

- 字符串用单引号（除非需要插值）
- 用 `Symbol#to_proc`：`names.map(&:upcase)`
- 条件修饰符（短行）：`return if user.nil?`
- **禁止** `for` 循环（用 `each`）
- **禁止** `unless` 带 `else`
- 方法最后一行表达式即返回值，不写 `return`

### 4. 方法长度

- `Metrics/MethodLength` 上限 20 行——超了就拆分
- `Metrics/AbcSize` 上限 20

## 常见错误速查

| Cop | 修复 |
|---|---|
| `Style/StringLiterals` | 双引号 → 单引号 |
| `Layout/LineLength` (>160) | 换行 |
| `Style/Documentation` | 本配置已关闭（模块顶层）；业务类靠 review |
| `Lint/UselessAssignment` | 删除无效赋值 |
| `Style/BlockDelimiters` | 多行块统一 `do...end` |
