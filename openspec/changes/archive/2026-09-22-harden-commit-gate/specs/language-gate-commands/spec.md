## ADDED Requirements

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
