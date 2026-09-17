# codestyle-check

面向 AI 编程助手（ZCode、Claude Code、Codex、Kimi Code）的跨语言代码规范强制门禁。

**把「这玩意儿过了 lint 吗？」从一道手动作业题，变成自动问答。**

---

## 做什么

codestyle-check 是一个插件：

1. **检测**项目语言（Java / Rust / TypeScript / Python）
2. **运行**对应语言的 linter，每次 AI 写文件后自动触发（PostToolUse 钩子）
3. **阻塞**——lint 不通过时，AI 必须修复才能继续（严格模式，默认开启）
4. **自动修复**——能修的先修（spotless / cargo fmt / eslint --fix / ruff --fix）
5. **提交门禁**——用户说「commit / push」时再过一遍（UserPromptSubmit 钩子）
6. **一行接入**——`/init` 拷贝配置 + pre-commit + AGENTS.md 到任何仓库

**按语言分化**：每种语言用最强的原生 linter，不重复造轮子。

---

## 支持的语言

| 语言 | Linter | Formatter |
|---|---|---|
| **Java** | `mvn javadoc:jar` + Checkstyle P3C | `mvn spotless:apply` |
| **Rust** | `cargo clippy -- -D warnings` + `cargo fmt --check` | `cargo fmt` |
| **TypeScript** | `eslint --max-warnings 0` | `eslint --fix` |
| **Python** | `ruff check` | `ruff check --fix` |

---

## 钩子覆盖

4 类钩子，覆盖 AI 写代码的全生命周期：

| 钩子 | 触发时机 | 行为 |
|---|---|---|
| `SessionStart` | 会话开始 | 检测语言，把 lint 规则注入 AI 上下文 |
| `UserPromptSubmit` | 用户说"commit/push/部署" | 最终门禁——任一 linter 不过则阻塞 |
| **`PostToolUse`** | **AI 写/改文件** | **对变更文件跑对应 linter；自动修复；仍失败则阻塞** |
| `Stop` | 会话结束 | 本次会话 lint 结果总结 |

**PostToolUse 是这个插件的核心创新点**——把「lint 错误等 AI 写完再修」前移成「lint 错误 AI 必须立刻修」。

---

## 快速开始

### 作为用户

```bash
# 安装插件（平台特定，见对应平台文档）
# ZCode：复制本仓库到 ~/.zcode/plugins/codestyle-check/
# Codex CLI：通过 /plugins 注册
# Kimi Code：类似机制

# 在任何项目里，对 AI 说：
/init    # 一键接入：拷贝 linter 配置 + pre-commit + AGENTS.md
/check   # 运行全量 lint + 报告
/fix     # 自动修复
```

### 作为 AI

插件激活后，你不需要手动操作：

- 你写的每个文件会被立刻 lint
- lint 失败且无法自动修复时，你会看到错误，**必须修复才能继续**
- 用户说"commit"时，你会受到「所有 linter 必须通过」的最后门禁
- 会话结束时会看到本次 lint 通过/失败的总结

---

## 仓库结构

```
codestyle-check-plugin/
├── .zcode-plugin/plugin.json     # ZCode manifest（主）
├── .codex-plugin/plugin.json    # Codex manifest
├── .mcp.json                     # MCP server 入口
├── hooks/
│   ├── hooks.json                # 4 类钩子定义
│   ├── session_start.py          # SessionStart：检测语言 + 注入规则
│   ├── post_tool_lint.py         # PostToolUse：核心强制钩子
│   ├── user_prompt_validator.py  # UserPromptSubmit：commit 门禁
│   └── stop_summary.py           # Stop：会话总结
├── scripts/
│   ├── detect_lang.py            # 语言检测 + linter 命令表（共享）
│   ├── run_check.py              # 主 CLI：检测 + 跑全部 + 报告
│   └── fix.py                    # 自动修复 CLI
├── skills/
│   ├── codestyle-check/          # 主入口
│   ├── codestyle-java/           # Java 专项 + javadoc 速查
│   ├── codestyle-rust/           # Rust clippy + deny warnings
│   ├── codestyle-typescript/     # ESLint recommended + TS strict
│   ├── codestyle-python/         # ruff + Python 规则
│   └── codestyle-init/           # 一键接入
├── commands/
│   ├── check.json                # /check
│   ├── fix.json                  # /fix
│   └── init.json                 # /init
├── linters/                      # 各语言配置模板（拷贝即用）
│   ├── checkstyle/
│   │   ├── p3c-javadoc-enforced.xml    # 阿里 P3C + 强制 javadoc
│   │   └── checkstyle-suppressions.xml # 抑制测试类 / 生成代码
│   ├── clippy/strict.toml              # deny warnings + unwrap/expect/panic
│   ├── eslint/recommended.cjs          # ESM flat config + TS 规则
│   ├── ruff/pyproject-snippet.toml      # [tool.ruff] 块
│   └── pre-commit/.pre-commit-config.template.yaml   # 拷贝 + 裁剪
├── README.md
├── README.zh-CN.md
├── LICENSE                       # Apache-2.0
├── PRIVACY.md
└── TERMS.md
```

---

## 设计选择

### 为什么按语言用原生 linter，不用统一的一个？

因为**原生 linter 拥有每个语言最强的规则集**：
- Java：Checkstyle 有 200+ 规则，含 javadoc、命名、import
- Rust：clippy 由 Rust 团队自己维护
- TypeScript：ESLint + @typescript-eslint 是事实标准
- Python：ruff 比 flake8 快 10-100x，规则更严

重造一个多语言 linter 不可能保持最新。**绑定原生，用钩子组合**。

### 为什么 PostToolUse 比 pre-commit 更重要？

| 层 | 延迟 | 强制力 |
|---|---|---|
| PostToolUse（本插件） | <2s | 强制 AI 修复 |
| pre-commit | 30s | 阻塞 git commit |
| CI | 分钟级 | 阻塞 PR merge |

PostToolUse 是**对 agent 的即时反馈**——agent 还在解题模式下修复率最高，远高于延迟的 CI 反馈。

### 为什么严格模式默认开启？

严格模式是这个插件的价值所在。没有它，插件就是「你可以自己跑的 linter 的花哨包装」。有了它，**linter 失败不容商量**——AI 必须修复才能继续。这才是核心。

---

## 配置

`~/.zcode/settings.local.yaml`：

```yaml
codestyle-check:
  enabled_languages: auto      # 或 [java, rust, typescript, python]
  strict_mode: true            # PostToolUse 失败时退出码 2（阻塞 AI）
  auto_fix_on_save: true       # 先试 spotless/cargo fmt/eslint --fix/ruff --fix
  lint_timeout_seconds: 120
```

---

## 协议

Apache-2.0 — 见 [LICENSE](./LICENSE)。
