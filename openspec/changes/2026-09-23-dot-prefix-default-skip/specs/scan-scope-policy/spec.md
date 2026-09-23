# scan-scope-policy：检查作用域与点前缀默认忽略

## Purpose

定义 codeguard 检查作用域的点前缀默认忽略规则：哪些路径面默认不检查、哪些例外面必须照常生效，以及该约束在提示词面的声明要求，使「宿主工具目录与配置文件不再产生与仓库内容无关的结论」成为可测试契约。

## ADDED Requirements

### Requirement: Check and save faces MUST skip dot-prefixed paths by default

相对项目根，任一路径段以 `.` 开头（`.`、`..` 段除外）的目录与文件为点前缀路径，默认忽略：不扫描、不检查、不报告。适用于 PostToolUse 保存面、提交门禁 delta 面、语言发现面，以及全量扫描的 ruff 与 `find` 型 gate 通道。项目根本身位于点前缀父目录下（如 `~/.config/proj/`）不构成点前缀命中。

#### Scenario: PostToolUse skips dot-prefixed files

- **WHEN** AI 保存 `.cursor/rules.py` 或 `.eslintrc.js`
- **THEN** 保存面静默跳过，不触发 lint、不产生告警

#### Scenario: Delta gate face excludes dot-prefixed paths

- **WHEN** 本次提交同时改动 `.github/workflows/ci.yml` 与 `src/main.py`
- **THEN** 门禁检查面只含 `src/main.py`

#### Scenario: Language discovery ignores dot-prefixed files

- **WHEN** 项目根仅有 `.eslintrc.js` 与 `main.py`
- **THEN** 发现面只计入 python，不因 `.eslintrc.js` 计入 javascript

#### Scenario: Full-scan channels exclude dot-prefixed subtrees

- **WHEN** 全量扫描执行 ruff 或 `find` 型 gate
- **THEN** ruff 命令带点前缀排除参数，`find` 表达式注入 `-not -path '*/.*'`，`.agents/` 等子树不产生结论

#### Scenario: Project under a dot-prefixed parent is not skipped

- **WHEN** 项目根为 `~/.config/proj/` 且检查 `main.py`
- **THEN** 不因父目录点前缀跳过，正常检查

### Requirement: Commit safety face MUST NOT be weakened by dot-prefix skipping

点前缀默认忽略只作用于检查面。入库安全检查独立收集拟入库路径：密钥/凭据类文件模式（`.env`、`*.pem`、`.DS_Store` 等）无论点前缀与否照常拦截；点前缀目录（宿主插件清单与第一方配置）照常可入库。

#### Scenario: Secret files remain blocked

- **WHEN** 拟提交 `.env` 或 `id_rsa`
- **THEN** 入库安全检查照常给出违规与修复指令

#### Scenario: Host manifest dirs remain committable

- **WHEN** 拟提交 `.agents/plugins/marketplace.json`
- **THEN** 不因目录点前缀被判「不应入库」

### Requirement: Config discovery MUST keep matching dot-prefixed config files

linter 配置发现（`requiresConfig`、`linter_config_files` 项目级匹配）不受点前缀忽略影响：点前缀配置文件照常使语言判定为已接入。

#### Scenario: requiresConfig matches dot files

- **WHEN** 项目根存在 `.markdownlint-cli2.jsonc` 且 markdown 声明 `requiresConfig` 含该文件名
- **THEN** markdown 判定为已接入，进入正常检查流程

### Requirement: Prompt surfaces MUST state the constraint

点前缀默认忽略规则 MUST 出现在提示词面：SessionStart「codeguard 项目记忆」上下文与 `AGENTS.md` 硬性禁令，且须同时声明两个例外面（入库安全照拦、配置发现照常），并有测试锚定提示词包含该声明。

#### Scenario: SessionStart context states the rule

- **WHEN** SessionStart 生成项目记忆文本
- **THEN** 文本含默认忽略声明及例外说明

#### Scenario: AGENTS.md hard rules state the rule

- **WHEN** 读取 `AGENTS.md` 硬性禁令
- **THEN** 含点前缀默认忽略条目
