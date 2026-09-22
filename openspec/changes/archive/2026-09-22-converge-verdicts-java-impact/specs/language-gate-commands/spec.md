## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Diagnostics outside the diff SHALL NOT be assumed historical

没有独立基线证据时，系统 MUST NOT 仅因诊断落在未修改文件就跳过失败。

#### Scenario: Changed API breaks an unchanged caller
- **WHEN** 新修改接口导致未修改调用方报告错误
- **THEN** 保留失败结论，不自动标记存量债务
