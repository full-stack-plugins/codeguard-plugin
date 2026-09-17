---
name: codeguard
license: Apache-2.0
description: |
  codeguard 主入口与全局路由中心：跨语言代码规范门禁（55 种语言识别，16 种 linter 强制）、
  CVE 依赖漏洞扫描编排、Git 分支与提交治理、安全规范检查。
  Use when users ask to run lint or code-style checks, fix style violations, scan dependencies
  for CVEs, or before any commit/push; route language-specific deep questions (syntax, framework,
  library usage) to the per-language skills, branch naming to codeguard-git-branch, commit format
  to codeguard-git-commit, and security findings to codeguard-security-{code,api,data}.
---

# codeguard 主入口：跨语言代码规范门禁

> 覆盖 **55 种语言识别 / 16 种 linter 强制**（完整表格：[docs/LANGUAGES.md](../../docs/LANGUAGES.md)）。

## Capability Boundaries

### ✅ Strengths
1. 项目语言自动检测（扩展名 + 标记文件双重识别）
2. 统一 lint 门禁：`bin/codeguard check`（或 scripts/run_check.py），失败即退出码 2
3. 统一自动修复：`bin/codeguard fix`（spotless / cargo fmt / eslint --fix / ruff --fix）
4. CVE 依赖漏洞编排：`bin/codeguard cve`（Maven dependency-check / npm audit / pip-audit / cargo audit，附修复指引）
5. 提交门禁：用户表达「提交/push」意图时全量复检（UserPromptSubmit 钩子）
6. 会话总结：Stop 钩子输出本轮 lint 通过/失败/自动修复计数

### ⚠️ Prerequisites
1. 各语言工具链已安装（mvn / cargo / node / ruff），缺失时门禁报告「无法验证」而非通过
2. Redis（仅安全钩子需要；lint 门禁不依赖）

### ❌ Out of Scope（路由表）
1. 语法学习、框架用法、库选型 → 对应语言的官方技能仓（如 full-stack-skills/java-skills）
2. 分支创建与命名 → `codeguard-git-branch`
3. commit message 格式 → `codeguard-git-commit`
4. 泄露/密钥/CVE → `codeguard-security-code`
5. 越权/鉴权注解/文件上传 → `codeguard-security-api`
6. 加密存储/脱敏/国密/等保密评 → `codeguard-security-data`

## When to Use

- "跑一下 lint" / "/check" / "代码规范检查"
- "修一下 style 问题" / "/fix"
- "扫一下依赖漏洞" / "codeguard cve"
- 提交前最后自检

## I. 标准工作流

```bash
# 1. 检测语言
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/detect_lang.py" "$(pwd)"

# 2. 全量 lint 门禁（主路径）
bin/codeguard check                     # 或 python3 scripts/run_check.py
bin/codeguard check --lang java         # 只跑某语言

# 3. 失败 → 自动修复 → 复扫
bin/codeguard fix --lang <name>

# 4. CVE 扫描（提交前必跑）
bin/codeguard cve --severity HIGH
```

## II. 门禁规则（不可协商）

| 规则 | 说明 |
|---|---|
| lint 失败 = 阻塞 | 严格模式下退出码 2，AI 必须修复后才能继续对话中的写码动作 |
| 无法验证 ≠ 通过 | 工具缺失（exit 127）输出「无法验证」并给出安装命令，不计入通过 |
| 检查出来得修 | CVE/HIGH 以上发现必须给出修复动作；禁止只报告不处理 |
| 禁止静默豁免 | 不得用 `@SuppressWarnings` / 调高阈值 / 改门禁配置来让失败消失；确需豁免须用户明确同意并在 suppressions 登记理由 |

## III. 修复决策树

```text
lint 失败
├─ 格式类（缩进/import 顺序/行宽）→ 自动修复（fix 命令）→ 复扫
├─ 缺失类（javadoc/@param 缺失）→ 补写注释/文档
└─ 逻辑类（unused 变量有语义/复杂度超标）→ 人工判断，禁止自动改业务代码
```

## Workflow

1. `bin/codeguard detect` 确认语言
2. `bin/codeguard check` 全量扫描
3. 失败项按上方决策树分类处理
4. 处理后复扫至全绿
5. 用户要求提交时，确认 `bin/codeguard cve` 也通过

## Gotchas

1. `mvn javadoc:jar` 的错误在 `mvn compile` 中不出现——不要用 compile 结果当门禁结论
2. 嵌套仓库/子模块会让 detect 扫描超时——对大仓库用 `--lang` 限定范围
3. 工具未装（exit 127）时门禁**不通过也不算漏洞**，先装工具再复扫
4. `npm audit fix` 可能引入破坏性升级——fix 后必须回归测试

## On-Demand Resources

- [语言支持总表](../../docs/LANGUAGES.md)：55 种语言的 lint/format 命令与状态
- [技能编写标准](../../docs/CODEGUARD_SKILLS_SPEC.md)：新增/修改技能的结构规范

## Official References

- 各语言工具官方文档见对应语言技能的 Official References 段
