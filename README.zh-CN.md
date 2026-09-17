# partme-codelint 插件

<p align="center">
  <img src="assets/banner.svg" alt="partme-codelint — 让 AI 写的代码一次过 lint。支持 ZCode、Claude Code、Codex CLI、Kimi Code。" width="100%">
</p>

<p align="center">
  <strong>AI 写完每个文件自动 lint。失败即阻塞。严格模式默认开启。</strong><br>
  面向 AI 编程助手的跨语言代码规范强制门禁：Java / Rust / TypeScript / Python。
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="docs/partme-codelint-Architecture.zh_CN.md">架构文档</a> ·
  <a href="docs/5、partme-codelint-技术方案与路线.md">技术方案</a>
</p>

---

## 定位

`partme-codelint` 让 AI 编程助手（ZCode、Claude Code、Codex CLI、Kimi Code）**第一次写出的代码就能通过 linter**。传统模式下你只能在 commit 时才发现 AI 漏写了 Javadoc 标签或者用了 `unwrap()`；本插件在 AI 写完文件的那一刻就跑对应 linter，**不通过则阻塞 AI 继续**。

它不是生产力插件，是**约束型插件**——它自己不产代码，而是对 AI 产出的代码执行规范。

### 适合谁

- **Java 后端工程师**：AI 写 Java 但漏 Javadoc 标签。
- **Rust 团队**：`cargo clippy` 不容商量，但 AI 习惯用 `unwrap()`。
- **TS / 前端团队**：受够了 AI 写 `any` 类型和未使用的 import。
- **Python 团队**：希望 AI 写出的代码也守 `ruff` 规范。
- **Tech Lead**：希望在 AI「思考模式」内就给反馈，而不是 PR review 时才发现。

### 解决什么问题

| 问题 | 本插件提供 | 可验证入口 |
|---|---|---|
| AI 漏 Javadoc，`mvn install` 时才报 | PostToolUse 钩子在每个 `.java` 写完自动跑 `mvn javadoc:jar` | `hooks/post_tool_lint.py`，[架构文档 §3.2](docs/partme-codelint-Architecture.zh_CN.md) |
| AI 在 Rust 业务代码用 `unwrap()` | `cargo clippy -- -D warnings` 跑每个 `.rs` 文件 | [架构文档 §2.1](docs/partme-codelint-Architecture.zh_CN.md) |
| AI 写 `any` 和未用变量 | `eslint --max-warnings 0` 阻塞 AI | `linters/eslint/recommended.cjs` |
| 每次会话都要手工问「过 lint 了吗？」 | Stop 钩子自动总结本会话 lint 通过/失败次数 | `hooks/stop_summary.py` |
| pre-commit / CI 发现时 AI 已切走，修复率 <30% | **三层防御**：钩子（<2s）→ pre-commit（30s）→ CI（5min） | [技术方案 §1](docs/5、partme-codelint-技术方案与路线.md) |

## 一览

```text
AI 写文件
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ partme-codelint                                    │
│  ① detect  检测项目语言（java / rust / ts / python）     │
│  ② lint    对文件跑对应原生 linter                       │
│  ③ auto-fix spotless / cargo fmt / eslint --fix / ruff    │
│  ④ block   仍失败则退出码 2（严格模式默认开启）          │
│  ⑤ summary 会话结束总结本轮 lint 通过/失败次数           │
└──────────────────────────────────────────────────────────┘
   │
   ▼
AI 一次写出就过 lint 的代码
```

| 属性 | 值 |
|---|---|
| 插件 ID | `partme-codelint` |
| 宿主 | ZCode、Claude Code、Codex CLI、Kimi Code |
| 当前版本 | `0.1.0` |
| ZCode manifest | `.zcode-plugin/plugin.json` |
| Codex manifest | `.codex-plugin/plugin.json` |
| MCP 服务 | `python3 scripts/run_check.py --mcp`（stdio JSON-RPC） |
| 主要语言 | Python 3.10+（钩子）、YAML/JSON（配置） |
| 协议 | Apache-2.0 |

## 能力与边界

### 已支持

| 能力 | 输入 | 输出 | 限制 | 状态 |
|---|---|---|---|---|
| 按文件检测语言 | 钩子 payload 中的 file_path | 语言字符串（`java`/`rust`/`typescript`/`python`） | — | Stable |
| 语言专属 lint | `mvn javadoc:jar` / `cargo clippy` / `npx eslint` / `ruff check` | 退出码 + stderr | 超时可配置（默认 120s） | Stable |
| 自动修复失败 | `mvn spotless:apply` / `cargo fmt` / `eslint --fix` / `ruff --fix` | 重跑 lint | 尽力修复，不改业务代码 | Stable |
| commit/push 门禁 | 用户 prompt 含 "commit" / "push" / "deploy" 关键词 | 全量 lint + 退出码 2（失败时） | — | Stable |
| 一行项目接入 | `/init` slash 命令 | 拷贝 linter 配置 + `.pre-commit-config.yaml` + AGENTS.md 片段 | — | Stable |
| 会话结束总结 | Stop 钩子 | 表格化 lint 通过/失败/自动修复次数 | — | Stable |

### 三层防御

本插件**不**取代 pre-commit 和 CI——它在它们前面加一个**更快**的层。

| 层 | 延迟 | 强制力 | 作用 |
|---|---|---|---|
| **PostToolUse 钩子（本插件）** | <2s | 阻塞 AI 继续 | AI 还在「立刻修」的模式时就抓住错误 |
| pre-commit | 30s | 阻塞 git commit | 用户准备提交时再次拦截 |
| CI | 分钟级 | 阻塞 PR merge | 最后兜底 |

PostToolUse 是 **最高 ROI** 的层，因为 AI 在它「还在乎这个问题」时收到反馈。

### 不做的事

- **不执行**你的代码。本插件只 lint，不运行。
- **不生产**代码。本插件强制 AI 产出的代码遵守规范。
- **不取代** code review。linter 抓机械错误，code review 抓设计错误。
- **不接**云端 linter 服务。本插件**严格客户端运行**（见 [PRIVACY.md](./PRIVACY.md)）。
- **V0.1 只支持 Java / Rust / TypeScript / Python**。V0.3 会加 Go / Kotlin / Swift / PHP（见 [技术方案 §4.3](docs/5、partme-codelint-技术方案与路线.md)）。

## 快速开始

### 作为用户

```bash
# 第一步：安装（按你用的平台选其一）
ln -s $PWD ~/.zcode/plugins/partme-codelint
ln -s $PWD ~/.codex/plugins/partme-codelint
ln -s $PWD ~/.kimi/plugins/partme-codelint

# 第二步：在任何项目里对 AI 说：
/init    # 拷贝 linter 配置 + .pre-commit + AGENTS.md
/check   # 跑全量 lint + 报告
/fix     # 自动修复
```

### 作为 AI

插件激活后，**你不需要**任何手动操作：

- 你写的每个文件会被立刻 lint
- lint 失败且无法自动修复时，你会看到错误，**必须修复才能继续**
- 用户说「commit」时，你会受到「所有 linter 必须通过」的最后门禁
- 会话结束时会看到本会话 lint 通过/失败的总结

## 配置

`~/.zcode/settings.local.yaml`（ZCode）或各平台对应文件：

```yaml
codelint:
  enabled_languages: auto      # 或 [java, rust, typescript, python]
  strict_mode: true            # PostToolUse 失败时退出码 2（阻塞 AI）
  auto_fix_on_save: true       # 先试 spotless/cargo fmt/eslint --fix/ruff --fix
  lint_timeout_seconds: 120
```

| 键 | 默认 | 作用 |
|---|---|---|
| `enabled_languages` | `auto`（自动检测） | 限定只跑哪些语言的 linter |
| `strict_mode` | `true` | lint 失败时是否阻塞 AI |
| `auto_fix_on_save` | `true` | 是否在报错前先尝试自动修复 |
| `lint_timeout_seconds` | `120` | 每次 linter 调用的超时秒数 |

## 仓库结构

```
partme-codelint/
├── .zcode-plugin/plugin.json     # ZCode manifest（主）
├── .codex-plugin/plugin.json    # Codex CLI manifest
├── .mcp.json                     # MCP 服务入口（stdio）
├── hooks/
│   ├── hooks.json                # 4 类钩子定义
│   ├── session_start.py          # SessionStart：检测语言 + 注入规则
│   ├── post_tool_lint.py         # PostToolUse：核心强制钩子
│   ├── user_prompt_validator.py  # UserPromptSubmit：commit 门禁
│   └── stop_summary.py           # Stop：会话总结
├── scripts/
│   ├── detect_lang.py            # 语言检测 + linter 命令表（共享）
│   ├── run_check.py              # 主 CLI：检测 + 跑全量 + 报告
│   └── fix.py                    # 自动修复 CLI
├── skills/                       # 6 个 SKILL.md（主入口 + 4 语言 + init）
│   ├── codelint/
│   ├── codestyle-init/
│   ├── codestyle-java/
│   ├── codestyle-rust/
│   ├── codestyle-typescript/
│   └── codestyle-python/
├── commands/                     # 3 个斜杠命令（/check /fix /init）
│   ├── check.json
│   ├── fix.json
│   └── init.json
├── linters/                      # 各语言配置模板（拷贝即用）
│   ├── checkstyle/               # 阿里 P3C + 强制 javadoc
│   ├── clippy/                   # deny warnings + 禁 unwrap/expect/panic
│   ├── eslint/                   # recommended + TS 规则
│   ├── ruff/                     # [tool.ruff] 块
│   └── pre-commit/               # .pre-commit-config.template.yaml
├── docs/
│   ├── partme-codelint-Architecture.zh_CN.md
│   └── 5、partme-codelint-技术方案与路线.md
├── README.md                     # 本文件（英文）
├── README.zh-CN.md               # 本文件（中文）
├── LICENSE                       # Apache-2.0
├── PRIVACY.md                    # 零数据收集承诺
└── TERMS.md
```

## 三端兼容性

| 平台 | 插件 manifest | 安装路径 | 状态 |
|---|---|---|---|
| **ZCode** | `.zcode-plugin/plugin.json` | `~/.zcode/plugins/partme-codelint/` | ✅ V0.1 |
| **Codex CLI** | `.codex-plugin/plugin.json` | `~/.codex/plugins/partme-codelint/` | ✅ V0.1 |
| **Claude Code** | （复用 Codex manifest，经 marketplace 安装） | `~/.claude/plugins/partme-codelint/` | 🔧 V0.2 |
| **Kimi Code** | （复用 Codex manifest） | `~/.kimi/plugins/partme-codelint/` | 🔧 V0.2 |

钩子、脚本、linter、skills 在所有平台**共享**——只有 manifest 不同。

## 验证

装好后，在任何项目里跑烟雾测试：

```bash
# 应输出 ["java"]（或类似）并退出码 0
python3 scripts/detect_lang.py /path/to/java-project

# 应输出表格化的通过/失败报告
python3 scripts/run_check.py --timeout 60

# 应自动修复能修的并重跑 lint
python3 scripts/fix.py --dry-run   # 看会改什么
python3 scripts/fix.py             # 实际改
```

在任何 AI 会话里，写完一个 `.java` 文件后，AI 日志里应看到：

```
[codelint] lint java: src/main/java/Foo.java
[codelint] ❌ java lint failed for src/main/java/Foo.java
[codelint] fix with: mvn -q spotless:apply
```

严格模式下退出码 2（AI 必须修）；非严格模式下退出码 0 仅警告。

## 相关资源

- **[full-stack-doc](https://github.com/partme-ai/skills/tree/main/full-stack-doc)** — 本插件 `docs/` 遵循的文档规范
- **partme-blender-plugin** — 同范式的兄弟插件（hooks/manifest/skills 模式）

## 协议

Apache-2.0 — 见 [LICENSE](./LICENSE)。
