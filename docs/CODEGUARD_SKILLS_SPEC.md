# codeguard 技能编写标准（CODEGUARD_SKILLS_SPEC）

> **文档说明**：定义 Codeguard 技能的抽象标准与结构规范。可复用技能的事实源是 [full-stack-skills/codeguard-skills](https://github.com/full-stack-skills/codeguard-skills)；插件内 `skills/` 是由 `skills.lock.json` 固定并校验的离线 vendor 快照。
>
> **版本**：V1.1　**最后更新**：2026-09-19

---

## 1. 技能是什么

一个技能（skill）= 一个目录 = 一个 `SKILL.md` + 可选 `references/` + 可选 `examples/`：

```text
skills/codeguard-java/
├── SKILL.md                        # 主文件：触发元数据 + 工作流 + 门禁规则
├── references/                     # 渐进披露：AI 按需加载的深度资料
│   ├── javadoc-error-quickref.md   #   错误码速查
│   └── checkstyle-p3c-mapping.md   #   规则映射表
└── examples/                       # 可编译/可运行的黄金示例（可选）
```

核心思想（学自 rust-skills）：**SKILL.md 保持精瘦可一次读完，深度资料放 references/ 按需加载**——让 AI 快速拿到 80% 高频规则，需要 20% 深度时再展开。

### 1.1 所有权与发布边界

| 内容 | 事实源 | 修改方式 |
|---|---|---|
| 可复用 Codeguard 技能 | `full-stack-skills/codeguard-skills` | 在外部仓修改、评估、发布新 tag，再更新插件 lock |
| 插件离线技能快照 | 本仓 `skills/` 中被 lock 列出的目录 | 只允许由 `scripts/vendor/skill_vendor.py update` 生成 |
| 插件内部定制技能 | 本仓 `skills/` 中未被 lock 列出、但在 `plugin-local-skills.json` 显式登记的目录 | 可在插件仓直接维护，vendor 会保留；未登记目录会被拒绝 |
| Hooks、linters、commands、MCP、运行脚本 | `codeguard-plugin` | 在插件仓开发、测试和发布 |

禁止直接修改 lock 管理的技能目录，否则离线/在线 vendor check 会失败。

## 2. SKILL.md 结构规范（九段式）

```markdown
---
name: <必须等于目录名>
license: Apache-2.0
description: |
  一段长触发描述：列出本技能能做什么、何时触发（Use when ...）、
  以及把不相关请求路由到哪个技能（Route X to Y skill）。
---

# 标题

> 来源引用（官方文档 / 团队 wiki 链接）

## Capability Boundaries
### ✅ Strengths       — 明确能做什么（编号列表）
### ⚠️ Prerequisites   — 需要预装的工具/配置
### ❌ Out of Scope    — 明确不做什么，并路由到对应技能

## When to Use
- 用户可能说的触发短语列表

## I. 主题章节（编号，含可复制命令与对照表）
## II. ...
## III. ...

## Workflow
1. 编号步骤（AI 执行的标准顺序）

## Gotchas
1. 编号坑点（实测踩过的坑必须沉淀在此）

## On-Demand Resources
- [references/xxx.md](references/xxx.md)：说明

## Official References
- 官方文档链接
```

### 硬性要求（市场校验器强制）

| 要求 | 说明 |
|---|---|
| frontmatter `name` == 目录名 | 否则 sync-marketplaces 校验失败 |
| frontmatter 有 `description` | 且尽量写全触发短语（AI 靠它路由） |
| 目录内 SKILL.md 存在 | 每个 skills/<dir>/ 一个 |

### 质量要求（团队约定）

| 要求 | 说明 |
|---|---|
| 命令必须可复制执行 | 示例命令贴进终端就能跑 |
| 坑点必须来自实战 | 每条 Gotcha 附一句「怎么发现的」更好 |
| 不写无法验证的规则 | 规则要有对应 lint 工具或来源链接 |

## 3. 技能族划分

| 族 | 技能 | 职责 |
|---|---|---|
| **元** | codeguard（主入口）、codeguard-init | 全局路由、项目接入 |
| **语言/文件族**（57） | codeguard-{java,rust,typescript,python,...} | 53 个 stable 与 4 个 planned 的 lint/format 门禁及规范速查 |
| **Git 治理族**（2） | codeguard-git-branch、codeguard-git-commit | 分支模型门禁、提交格式门禁 |
| **安全治理族**（3） | codeguard-security-{code,api,data} | 泄露/CVE、越权/上传、加密/脱敏/等保密评 |

### 技能间路由规则（写在 description 尾部）

- 语言的**深度语言问题**（语法、框架、库用法）→ 路由到对应语言技能仓（如 full-stack-skills/java-skills）
- codeguard 只负责「规范门禁」：lint/format/安全检查/提交与分支治理

## 4. Vendor 工作流

```bash
# 上游发布新不可变 tag 后，先更新 skills.lock.json 中的 ref
python3 scripts/vendor/skill_vendor.py update
python3 scripts/vendor/skill_vendor.py check --offline
python3 scripts/vendor/skill_vendor.py check
```

`update` 只替换 lock 中列出的目录，不会触碰未列出的插件内部定制技能。CI 同时执行离线与在线校验，并拒绝未同步 lock 的受管技能直接编辑。

## 5. 结构升级路线

| 阶段 | 状态 | 说明 |
|---|---|---|
| V1 基础结构 | ✅ 已完成 | 全部技能具备 frontmatter + 强制项 + 常见错误速查 |
| V2 标准结构（本轮） | ✅ 核心完成 | 主入口/java/git-commit/git-branch/security-code 重写为九段式 + references |
| V3 全量 references | ⏳ | 语言族全部补 references/（各语言错误码速查、工具策略文件） |
| V4 examples/ | ⏳ | 黄金示例目录（CI 可跑通的规范样板） |

---

**文档版本**：V1.1　**状态**：✅ 生效
