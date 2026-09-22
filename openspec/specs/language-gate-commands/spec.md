# language-gate-commands Specification

## Purpose
定义语言注册表中每个条目所声明命令的可执行性要求：`lint` / `format` / `probe` 必须能以声明的方式真正运行，需要路径或文件参数时必须以显式占位符或 glob 表达；并定义语言声明配置前置条件的能力，使「项目未接入」与「检查失败」不再混为一谈。
## Requirements
### Requirement: Declared commands must be runnable as written

注册表声明的 `lint` / `format` / `probe` 命令 SHALL 能按声明形式直接执行；需要文件或路径参数的 SHALL 以 `{file}` 占位符或显式 glob 表达，不得依赖调用方补全。

#### Scenario: 缺少必需参数

- **WHEN** 某语言的 `lint` 命令在无参数调用下返回工具用法错误（而非 lint 结论）
- **THEN** 门禁不得把它作为「lint 失败」上报，因为该结果与仓库内容无关

#### Scenario: markdown 的 lint 命令

- **WHEN** 门禁在已接入 markdown 的项目上运行
- **THEN** markdownlint 实际检查文件并以 lint 结论作为退出码，而不是返回用法错误

### Requirement: Probe must not confirm availability through a misinterpreted argument

`probe` 命令 SHALL 使用目标工具真实支持的可用性查询方式。当命令中的 flag 不被工具识别、因而被解释为路径或 glob 参数时，SHALL NOT 据此判定工具可用。

#### Scenario: 无效 flag 被当成路径

- **WHEN** probe 命令包含该工具不认识的 flag，导致其被当作文件或 glob 处理并仍然成功退出
- **THEN** 该探测结果不得被用作「工具已安装且可用」的证据

### Requirement: Auto-fix command must be executable and scoped

`format` 命令 SHALL 可通过注册表声明的入口直接执行，包括在工具未全局安装时经包管理器解析；且 SHALL 明确其作用范围是单文件还是整个项目，不得使调用方无从判断影响面。

#### Scenario: 工具未全局安装

- **WHEN** `format` 命令引用一个未全局安装的工具
- **THEN** 自动修复 SHALL 经包管理器解析执行，而不是以 command not found 失败

### Requirement: Languages may declare a configuration prerequisite

注册表 SHALL 允许为语言声明 `requiresConfig`。对以风格偏好为主、其默认规则会大面积误报的工具（如 markdown、yaml），SHALL 声明该前置条件。

#### Scenario: 已声明前置条件且项目未接入

- **WHEN** 项目缺少该语言声明的配置文件
- **THEN** 该语言判定为未接入 / 未验证，安全跳过且不阻塞提交，并在结果中说明未验证的原因

#### Scenario: 已声明前置条件且项目已接入

- **WHEN** 项目存在该语言声明的配置文件
- **THEN** 门禁按该配置正常检查，结论作为 lint 结果上报

#### Scenario: 未声明前置条件的语言不受影响

- **WHEN** 某语言未声明 `requiresConfig`
- **THEN** 其行为与现状一致，不被本要求改变

### Requirement: Process PATH enrichment SHALL live in scripts/paths.py

The function `ensure_user_path(from_login_shell: bool = False) -> None` SHALL be defined in `scripts/paths.py` and re-exported from `scripts/detect_lang.py` so existing call sites continue to work without modification.

#### Scenario: Hooks import ensure_user_path from detect_lang

- **WHEN** any hook script imports `ensure_user_path` from `scripts/detect_lang`
- **THEN** the import resolves to the symbol defined in `scripts/paths.py` without behavioral change

#### Scenario: Direct import from scripts/paths

- **WHEN** a new script needs to enrich PATH without depending on language detection
- **THEN** it can `from paths import ensure_user_path` with no other dependencies required

### Requirement: User configuration loading SHALL live in scripts/user_config.py

The functions `load_user_config`, `load_project_overrides`, and `get_overrides` SHALL be defined in `scripts/user_config.py` and re-exported from `scripts/detect_lang.py`.

#### Scenario: Hooks import load_user_config from detect_lang

- **WHEN** any hook script imports configuration helpers from `scripts/detect_lang`
- **THEN** the import resolves to the symbol defined in `scripts/user_config.py`

### Requirement: scripts/detect_lang.py SHALL retain language-detection surface only

`scripts/detect_lang.py` SHALL expose only the language-detection and command-table API: `LANG_COMMANDS`, `detect_languages`, `detect_language`, `find_project_root`, `probe_toolchain`, `project_uses_linter`, `extract_tool_binaries`, and the internal `_load_registry`. It SHALL NOT define PATH enrichment or configuration helpers in its own body.

#### Scenario: Refactor introduces a third responsibility

- **WHEN** a new function in `scripts/detect_lang.py` mixes PATH handling, config loading, or other unrelated concerns with language detection
- **THEN** the change SHALL be rejected because it violates the single-responsibility boundary

### Requirement: Gates in git repositories SHALL default to changed-file scope

git 仓库内的门禁 MUST 缺省只检查本次改动涉及的文件（staged + 未暂存 + 未跟踪，按语言归属过滤）；存量问题 MUST NOT 阻塞无关的新提交。项目可用 `codeguard.json` 的 `gate_scope`（`delta`/`repo`）显式覆盖；非 git 目录缺省为全量。全量模式 MUST 从 ruff 扫描中剔除依赖快照与构建产物目录（vendor/build/dist 等）。

#### Scenario: A committed legacy issue is untouched by a clean change

- **WHEN** 仓内 HEAD 已含存量 lint 问题，本次提交只涉及无问题的文档文件
- **THEN** 门禁判定通过，存量问题不拦截本次提交

#### Scenario: A new staged file introduces a problem

- **WHEN** 新增或修改的文件被暂存且含 lint 问题
- **THEN** 门禁按改动集检出该问题并正常拦截

### Requirement: A toolchain crash SHALL be recorded as unverified, not as a lint failure

linter 以 exit 2（用法/依赖/配置崩溃）退出时，门禁 MUST 记为未验证（hook 路径归 skipped；CLI/MCP 标记 unverified 且不计为失败），MUST NOT 作为 lint 失败上报或触发自动修复。

#### Scenario: An npx tool crashes with exit 2

- **WHEN** 某语言的检查命令因包/运行时问题以 exit 2 退出且无 lint 结论
- **THEN** 结果为"工具链异常未验证"，不阻塞提交、不计入失败

### Requirement: Single-file hook commands MUST NOT silently expand to whole-repository scans

PostToolUse 的 lint 与 format 命令 MUST 物化到被编辑文件的单文件作用域：存在 `{file}` 或全仓扫描 token（`.`、`**/*.md`）时 MUST 收敛为该文件，裸命令 MUST 追加该文件路径。自动修复成功后，若改动波及被编辑文件之外的文件，MUST 把文件清单注入返回上下文。

#### Scenario: Editing one Python file triggers format

- **WHEN** AI 保存单个 `.py` 文件且该文件 lint 失败触发自动修复
- **THEN** format 命令只作用于该文件；若仍有其它文件被改动，返回上下文列出被改动文件并要求重新读取

