# mcp-tool-server Specification

## Purpose
定义官方 SDK stdio MCP 的四个工具、带状态和原因的检查结果、受限修复作用域，以及只读 Java 模块影响规划，避免协议转换丢失不确定性。

## Requirements

### Requirement: The MCP server SHALL expose three tools over stdio JSON-RPC

服务 MUST 使用官方 SDK stdio 暴露原有 check_code_style、auto_fix、list_languages，并新增只读 analyze_java_impact。既有工具名保持兼容。

#### Scenario: Listing tools at startup
- **WHEN** 客户端请求 tools/list
- **THEN** 返回四个工具及其输入 schema

### Requirement: `check_code_style` SHALL return a structured envelope with full stderr on disk

结果 MUST 保留 language、passed、exit_code、stderr_path、log_path，增加 status 和 reason；UNVERIFIED/PLANNED 不得变成 passed=true。非 PASS 的执行输出 MUST 可追溯。

#### Scenario: One language fails
- **WHEN** Python 检查发现违规
- **THEN** 返回 status=FAIL、passed=false 与实际退出码和完整日志路径

#### Scenario: All languages pass
- **WHEN** 每个检查真实退出 0
- **THEN** 返回 status=PASS、passed=true

#### Scenario: A tool cannot run
- **WHEN** 缺少工具或检查超时
- **THEN** 返回 status=UNVERIFIED、passed=false 和原因，不丢弃未验证信息

### Requirement: `auto_fix` SHALL run formatters and re-verify

auto_fix MUST 默认仅处理 Git 改动文件并按相同范围复检；无法确定范围或项目 formatter 无法限制范围时不得默默扩展写入。fixed MUST 表示实际文件修改，而非只表示进程退出 0。结果包含 check 信封与逐语言修复结果。

#### Scenario: Formatter succeeds and lint passes
- **WHEN** formatter 修改变更文件且复检成功
- **THEN** fixed=true，check 中结果 PASS，干净文件不变

#### Scenario: Formatter succeeds but lint still fails
- **WHEN** 已修改文件仍有不可修复问题
- **THEN** fixed=true 且复检 FAIL，不宣称完成

#### Scenario: Git scope is unavailable
- **WHEN** 不能确定 Git 改动范围
- **THEN** fixed=false、UNVERIFIED，提示显式 CLI 全量修复，不执行 formatter

### Requirement: `list_languages` SHALL return id + name only
`list_languages()` MUST return a JSON array of `{id, name}` objects from `scripts/languages.json`, omitting the rest of each language record (lint command, format command, install hint, etc.) so internal commands are not exposed as part of the MCP surface.

#### Scenario: Listing all supported languages

- **WHEN** the client calls `list_languages`
- **THEN** the response enumerates every entry in `scripts/languages.json` with exactly two fields (`id`, `name`) per record

### Requirement: Portable MCP discovery SHALL use root mcp.json

提供已有 MCP 服务的发布包 MUST 在根目录包含标准 `mcp.json`，声明 Agent Plugins 1.0.0 MCP Schema、`stdio` 传输、单独的 Python 可执行命令与参数，指向包内 `scripts/run_check.py --mcp`。不得在可移植 `plugin.json` 中内嵌 `mcpServers`。

#### Scenario: A portable client discovers CodeGuard
- **WHEN** 客户端读取根目录 `mcp.json`
- **THEN** 可发现 `codeguard` stdio 服务，配置中的脚本存在于插件包内，Schema 版本与 `plugin.json` 一致
- **AND** 项目工具调用由客户端显式传入目标项目的绝对 `path`；配置工作目录为插件根，不代表用户项目
- **AND** MCP SDK 依赖仍通过 `requirements.txt` 声明，不自动安装
