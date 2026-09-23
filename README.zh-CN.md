# CodeGuard 插件

> 结构对齐：README.md 与 README.zh-CN.md 的标题层级、本地链接和版本串必须一致，由 tests/test_readme_parity.py 检查。

[English](README.md) · [简体中文](README.zh-CN.md)

![CodeGuard](assets/banner.svg)

## 定位

CodeGuard 为 AI 编程助手提供原生检查证据，守护已支持的 Git 提交/推送调用。PostToolUse 只反馈、不阻断；确定违规会拦截 Git 调用；检查无法完成时明确 UNVERIFIED。某项检查通过，不等于代码完全正确。

已安装插件的版本以各清单为准。本次架构重构保留现有 68 个受管技能，重点收敛判定证据、模块职责与 Java 项目感知。

### 运行边界

| 入口 | 检查对象 | 结果 |
|---|---|---|
| PostToolUse | 文件型工具检查本次编辑文件 | 反馈、exit 0；项目级检查延后 |
| UserPromptSubmit | 与提交意图相关的工作树变更 | 建议，不阻断用户消息 |
| PreToolUse Git 门禁 | 拟提交 index 快照或推送 HEAD 快照 | 确定违规 exit 2；不确定项明确 UNVERIFIED 并 fail-open |
| CLI check / MCP check_code_style | 项目检查，含 Java 构建验证 | 明确状态、原因、原始退出码、顺序执行证据和日志 |
| pre-commit / CI | 独立配置的检查 | 单独验收，不能由钩子成功代替 |

钩子不会自动覆盖宿主的每个命令入口。历史 V0.5.4 安装证据不能代表当前版本已在 Codex、ZCode、Kimi 验收。

### 判定契约

| 状态 | 含义 | passed |
|---|---|---|
| PASS | 检查实际执行成功 | true |
| FAIL | 检查器发现违规 | false |
| UNVERIFIED | 缺工具、超时、配置错误、证据不可用 | false |
| SKIPPED | 没有适用的改动文件 | false |
| PLANNED | 已有计划，或尚未配置可执行适配器 | false |

CLI 优先级：FAIL → 2；否则有 UNVERIFIED/PLANNED → 1；验证成功或无须检查 → 0。不能把“非 2”解释为“通过”。工具退出码各有语义：pylint 的 2 不等于 ESLint 的 2。

## Java 项目感知

### 只读规划

```bash
codeguard java-plan /path/to/project --json
codeguard java-plan /path/to/project --json --changed api/src/main/java/Api.java
codeguard check --lang java /path/to/project
```

规划器读取 Maven POM / Gradle Groovy、Kotlin DSL，优先项目 wrapper，将文件映射到模块，再计算反向传递依赖。修改 api 可能要求复查 service 和 app，即使调用方文件没有变化。删除、资源与构建描述变更均纳入分析。

Maven 使用 verify 并追加 -DskipTests（测试代码仍编译，仅跳过执行），安全子集增加 -pl、-am；Gradle 使用根 check 或受影响的 :module:check 并追加 -x test。默认等级检查编译、打包与生命周期绑定的静态检查；测试执行属于 CI 或显式 java.commands 声明的职责边界。profiles、未解析属性、父依赖继承或识别到的动态/复合 Gradle 构建会保守扩大范围。规划不会执行构建、下载依赖、安装工具或初始化 CodeGraph。

### 项目权威命令

仓根 codeguard.json 可声明明确的 argv 列表：

```json
{
  "java": {
    "commands": [
      ["./mvnw", "verify", "-Pquality"]
    ]
  }
}
```

命令顺序执行，失败停止。它们是可信项目配置，不是 shell 字符串。声明命令也是项目升级检查等级的途径——例如上例执行含测试的完整 verify。执行 check 或 Git 门禁会运行项目构建、可能触发项目插件；默认等级跳过测试执行（-DskipTests / -x test），但配置命令或插件绑定任务可能运行测试，并可能访问依赖仓库；**这不是沙箱**。

本轮覆盖模块级，不是符号调用图或业务语义证明。verify/check 成功不代表 Checkstyle、PMD、SpotBugs 或测试配置完整；应查看计划的 gaps 和 reasons。

## Git 内容一致性

纯 commit 检查 index，不会拿未暂存的修复冒充提交内容。已支持的前序 git add 操作叠加预测工作树路径；纯 push 检查 HEAD 和上游差异。无可解析上游时检查 HEAD 树。敏感文件规则采用同一预测范围；删除敏感文件不视为新增入库。

检查在临时目录物化 Git blobs，不 stash、不 checkout、不更改真实 index。精确内容门禁不复用软提醒的工作树缓存。快照缺 ignored 依赖时保持 UNVERIFIED，不改查另一份源码。

限制：20,000 个已跟踪文件 / 256 MiB Git 内容 / 每个覆盖文件 32 MiB。符号链接、子模块、冲突及不支持的内容需要独立验证。复杂 shell 写入、任意 Git refspec、动态别名与并发编辑尚未完整建模；钩子不能替代受保护分支 CI。
仓库归属与拟暂存分析覆盖一层静态可读的 bash/sh/zsh `-c` 或脚本执行；无法建模的间接 Git 操作会以 UNVERIFIED 阻断。动态脚本以及 Python/Node 中拼接的 subprocess 调用仍不在此静态模型内。

不再仅凭“报错文件没修改”豁免历史债：变更 API 也会破坏未修改的调用方。

## CLI 与 MCP

### CLI

```bash
# 直接在此仓运行，不需要全局安装。
./bin/codeguard detect /path/to/project
./bin/codeguard check /path/to/project
./bin/codeguard fix /path/to/project --dry-run
./bin/codeguard fix /path/to/project
./bin/codeguard fix /path/to/project --all
./bin/codeguard cve /path/to/project --json
./bin/codeguard cve /path/to/project --ecosystem universal --severity HIGH
```

fix 默认只修 Git 改动文件；整项目 formatter 需要显式 --all。非 Git 的 CLI 目录保留旧的全量行为。--fix 可能修改文件，不是预览。

CVE 退出码：0 通过、1 未验证、2 发现漏洞、3 非法生态。Maven/npm/pip-audit/cargo-audit/Trivy 必须有结构化报告证据；网络错误不是漏洞。npm moderate 映射 MEDIUM；npm audit fix 后以新扫描为准。Python/Rust 原生发现没有可比较严重度时，高于 LOW 的阈值返回 UNVERIFIED 并保留发现，可显式选择 Trivy 复核。Python 检查项目 requirements/pyproject，不扫宿主环境。

### MCP 服务

```bash
# 需要 requirements.txt 已声明的依赖。
python3 scripts/run_check.py --mcp /path/to/project
```

| 工具 | 契约 |
|---|---|
| check_code_style | 逐语言状态、原因、passed、原始退出码、逐命令状态元数据与完整失败日志路径 |
| auto_fix | 只修 Git 改动文件、同范围复检，拒绝无界项目 formatter；fixed 表示实际修改 |
| list_languages | 注册表语言标识和名称 |
| analyze_java_impact | 只读计划，接受 path 和可选 changed 数组 |

日志默认在 <project>/out/.codeguard-last.log；CLI --quiet 关闭写日志。多命令检查失败时，日志保存每条已执行检查的完整输出。MCP 执行轨迹只返回阶段、序号、程序名、退出/故障及输出长度，不回显 argv、环境覆盖或检查器输出。本地日志可能含敏感文本，应排除出版本控制。MCP auto_fix 无法确定 Git 范围时不会写入。

## 配置与覆盖

仓根 codeguard.json 的 gate_scope 可选 delta/repo，也可定制扩展名和排除规则。用户设置保留 enabled_languages、auto_fix_on_save、lint_timeout_seconds。strict_mode 是保留字段，不会令 PostToolUse 阻断，详见[钩子协议](hooks/__protocol__.md)。

注册表含 **54 个 Stable 适配器和 3 个 Planned 项**。“Stable” 不证明全部工具链或项目已验证。Markdown/YAML 需要项目配置，缺配置为 UNVERIFIED；Markdown 违规只告警。生成物和依赖目录从普通 lint 范围排除，不等于允许入库。Python 检查优先使用项目自有 ruff 配置（ruff.toml / .ruff.toml / [tool.ruff]）；项目无自有配置时注入钉扎在 CI 基线（ruff==0.16.8）的默认规则集，判定不随机器上 ruff 版本漂移。完整命令见[语言清单](docs/LANGUAGES.md)。

显式逃生门 git config codeguard.skipGate true 会绕过钩子门禁，并在会话总结中记录。共享状态位于 CODEGUARD_HOME（默认 ~/.codeguard）。
Git 门禁静态读取一层 Shell 包装命令，支持可解析的裸环境赋值、env、command 和 sudo 前缀；同一前缀规则也用于 skipGate 状态变更和单次豁免。它不执行或完整解释脚本。

## 外部技能

**68** 个可复用技能在 [full-stack-skills/codeguard-skills](https://github.com/full-stack-skills/codeguard-skills) 编写。本插件通过 skills.lock.json 打包不可变的 **v0.1.2**，固定 tag、commit 与逐技能摘要。

不得直接编辑受管技能。先修改并发布技能源，再更新 lock 并运行 vendor。只有 plugin-local-skills.json 显式登记项归插件自有，目前为空。详见[编写规范](docs/CODEGUARD_SKILLS_SPEC.md)。

```bash
python3 scripts/vendor/skill_vendor.py check --offline
python3 scripts/vendor/skill_vendor.py check
```

## 验证与剩余工作

```bash
python3 -m unittest discover -s tests -q
python3 tests/run_all.py
python3 scripts/validate_languages_json.py
python3 scripts/check_architecture.py
ruff check hooks scripts tests
```

测试包含真实临时 Git 仓库、原生子进程 fixture 与官方 SDK stdio MCP 调用。fixture wrapper 成功不是真实 Maven/Gradle 集成构建。Codex/ZCode/Kimi 当前版本加载、真实项目构建、在线漏洞扫描与准确率/召回率基准仍需独立验收。

当前实现与证据：[架构及扩展指南](docs/current-architecture.md)、[重构验证记录](openspec/changes/refactor-codeguard-architecture/verification.md)。旧文档保留为历史参考：[判定与 Java 架构](docs/verdict-java-architecture.md)、[此前验证报告](docs/verification-verdict-java.md)、[原架构](docs/partme-codeguard-plugin-Architecture.zh_CN.md)、[路线图](docs/technical-roadmap.zh_CN.md)。

## 许可与隐私

Apache-2.0 — [LICENSE](./LICENSE)。原生构建器/扫描器可能访问依赖仓库和漏洞数据库，请查看 [PRIVACY.md](./PRIVACY.md) 与 [TERMS.md](./TERMS.md)。
