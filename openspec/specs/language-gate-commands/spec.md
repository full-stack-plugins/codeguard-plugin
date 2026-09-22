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

Git 门禁 MUST 默认 delta，项目可用 gate_scope=repo 选择全量；构建产物/依赖目录继续使用 scope.FULL_SCAN_EXCLUDES 单源排除。纯 commit 取 index 改动，预测 add 叠加工作树，纯 push 取 HEAD 中的未推送差异，无可解析上游时检查 HEAD 树。提交+推送检查两者并集。精确快照不复用软门禁缓存。只提醒的 UserPromptSubmit 可用工作树宽口径。项目级检查失败不得仅凭未修改文件位置豁免。

#### Scenario: A committed legacy issue is untouched by a clean change
- **WHEN** 改动只有文档且项目检查不适用
- **THEN** 无须执行的检查跳过；不伪称完成项目验证

#### Scenario: A new staged file introduces a problem
- **WHEN** staged 内容违规但工作树已修好
- **THEN** index 快照检出违规

#### Scenario: A bad commit made outside the gate must not slip through the push
- **WHEN** HEAD 含未推送违规内容
- **THEN** HEAD 快照检出违规，不读取工作树修复冒充通过

#### Scenario: Push with no resolvable upstream does not crash
- **WHEN** 没有可解析上游
- **THEN** 精确硬门禁检查 HEAD 树，不因空基线跳过全部文件

#### Scenario: A chained commit-and-push takes the wider face
- **WHEN** 可识别链中同时提交和推送
- **THEN** 预测快照包含拟提交内容与未推送差异

### Requirement: A toolchain crash SHALL be recorded as unverified, not as a lint failure

检查器退出码 MUST 结合工具契约判定。配置/依赖/用法错误、缺失工具和超时 MUST 记为 UNVERIFIED，禁止自动修复；不得把所有工具的 exit 2 一概视为配置错误。无法验证不计为 PASS，CLI 返回 1，MCP 保留原因，hook 放行时必须明确提示未验证。

#### Scenario: An npx tool crashes with exit 2
- **WHEN** ESLint 因配置问题以 exit 2 退出
- **THEN** 结果为 UNVERIFIED，不作为 lint 违规也不作为通过

### Requirement: Single-file hook commands MUST NOT silently expand to whole-repository scans

PostToolUse MUST 将文件型命令限制到编辑文件；项目级命令 MUST 保留 append_files=false，不追加源码文件参数，并推迟到显式仓库检查或 Git 门禁。不得因单文件事件自动执行全项目 formatter。所有 CLI/MCP/hook 命令构造 MUST 保留注册表作用域约束。

#### Scenario: Editing one Python file triggers format
- **WHEN** AI 保存单个 Python 文件且该文件存在可修复 lint 违规
- **THEN** formatter 仅处理该文件并复检

#### Scenario: Editing a Java file
- **WHEN** Java 检查/修复是项目级命令
- **THEN** 保存事件提示项目级检查入口，不生成 mvn 加源码文件的错误命令，不自动格式化全仓

### Requirement: Diagnostics outside the diff SHALL NOT be assumed historical

没有独立基线证据时，系统 MUST NOT 仅因诊断落在未修改文件就跳过失败。

#### Scenario: Changed API breaks an unchanged caller
- **WHEN** 新修改接口导致未修改调用方报告错误
- **THEN** 保留失败结论，不自动标记存量债务
