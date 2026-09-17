---
name: codeguard-shell
license: Apache-2.0
description: |
  Shell 脚本规范：shellcheck 静态分析（quote 展开词分割、未使用变量、subshell 陷阱）
  + shfmt 格式化。Use when users write .sh/.bash/.zsh scripts, hit shellcheck SC codes,
  or ask about shell quoting and POSIX portability.
  Route CI pipeline design to codeguard-security-api; dependency CVEs to codeguard-security-code.
---

# Shell 代码规范门禁

> 基于 [ShellCheck](https://www.shellcheck.net/wiki) 与 [shfmt](https://github.com/mvdan/shfmt)。

## Capability Boundaries

### ✅ Strengths
1. shellcheck 全规则（SC 系列错误与告警）
2. shfmt 格式化（缩进/二元行首/重定向空格）
3. POSIX / bash / zsh 方言检查

### ⚠️ Prerequisites
1. `brew install shellcheck shfmt`（或 apt 对应包）

### ❌ Out of Scope
1. Bash 脚本编写教学 → GNU Bash 手册 / ShellCheck wiki
2. 运行时容器化打包 → codeguard 不做镜像构建

## When to Use

- "shell 脚本报错" / "shellcheck SCxxxx" / "格式化 shell" / "POSIX 兼容"

## I. 强制项（shellcheck 全开，warning 也需处理或注释豁免）

```bash
shellcheck script.sh          # codelint 钩子默认调用
shfmt -i 2 -ci -bn -sr -w .   # 格式化（i=2 缩进，ci=case 缩进，bn=二元行首，sr=重定向空格）
```

### 高频 SC 错误速查

| 规则 | 含义 | 修复 |
|---|---|---|
| SC2086 | 变量未加引号（词分割/glob 风险） | `"$var"` |
| SC2046 | 命令替换未引号 | 同上加引号，或显式 `eval` 场景注释豁免 |
| SC2006 | 反引号 `` ` ` `` | 改 `$(...)` |
| SC2181 | 用 `$?` 判断上条命令 | 改 `if cmd; then` |
| SC2164 | `cd` 失败未处理 | `cd path \|\| exit` 或 `set -e` |
| SC2034 | 变量赋值后未使用 | 删除或导出 |

## II. 团队基线（每个新脚本模板）

```bash
#!/usr/bin/env bash
set -euo pipefail                 # e=出错即退, u=未定义变量报错, o pipefail=管道失败即失败
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
    local arg="$1"
    # ...
}

main "$@"
```

## III. 禁止使用

- `eval` 处理不可信输入（代码注入）
- 反引号嵌套（改 `$()`，可嵌套）
- 裸 `cd` 无错误处理
- 未引号 glob 展开传参

## Workflow

1. 写完脚本 → codeguard 钩子自动 shellcheck
2. 有告警 → 按 SC 编号查上表修复
3. 格式 → `shfmt -w .`
4. 提交前 `shellcheck` 复扫至零输出

## Gotchas

1. `shellcheck` 对动态 source/路径给 SC1090/1091 —— `.shellcheckrc` 里 disable 即可
2. `set -e` 在 `if cmd; then` 内不生效（expected）——不要误以为是 bug
3. zsh 脚本要 `#!/usr/bin/env zsh` 并注意 shfmt 默认按 bash 解析（`--shell zsh` 可指定）
