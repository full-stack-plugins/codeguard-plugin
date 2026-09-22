# mcp-tool-server Specification

## Purpose
TBD - created by archiving change 2026-09-22-fix-gate-trigger-and-mcp. Update Purpose after archive.
## Requirements
### Requirement: The MCP server SHALL expose three tools over stdio JSON-RPC
`scripts/run_check.py --mcp` MUST start an stdio JSON-RPC server using the official `mcp` Python SDK and register exactly three tools: `check_code_style`, `auto_fix`, and `list_languages`. The server MUST NOT take any other CLI flag in MCP mode.

#### Scenario: Listing tools at startup

- **WHEN** a client sends `tools/list`
- **THEN** the response enumerates `check_code_style`, `auto_fix`, `list_languages` with their input schemas

### Requirement: `check_code_style` SHALL return a structured envelope with full stderr on disk
`check_code_style(path, languages?)` MUST run the configured linters, write the full stderr of any failing invocation to `<log_dir>/.codeguard-last.log` (default `<project>/out/.codeguard-last.log`), and return a JSON envelope with one entry per language: `{language, passed: bool, exit_code: int, stderr_path: str, log_path: str}`.

#### Scenario: One language fails

- **WHEN** the path contains a single Python project whose ruff lint fails
- **THEN** the envelope contains one entry with `passed=false`, `exit_code` from ruff, `stderr_path` pointing at the on-disk log, and `log_path` echoing the same path

#### Scenario: All languages pass

- **WHEN** every linter exits 0
- **THEN** every entry has `passed=true`, `exit_code=0`, and the log file is either empty or absent (no stderr written)

### Requirement: `auto_fix` SHALL run formatters and re-verify
`auto_fix(path, languages?)` MUST invoke the per-language formatter chain (`format` from `scripts/languages.json`) and then re-run `check_code_style` on the same scope before returning. The response envelope MUST contain both `fixed: bool` (whether any file was modified) and the `check_code_style` envelope for the post-fix re-check.

#### Scenario: Formatter succeeds and lint passes

- **WHEN** ruff `--fix` removes unused imports and the re-check passes
- **THEN** `fixed=true` and the embedded `check_code_style` envelope is all-pass

#### Scenario: Formatter succeeds but lint still fails

- **WHEN** ruff `--fix` ran but a remaining error is non-fixable
- **THEN** `fixed=true` and the embedded `check_code_style` envelope contains at least one failing entry

### Requirement: `list_languages` SHALL return id + name only
`list_languages()` MUST return a JSON array of `{id, name}` objects from `scripts/languages.json`, omitting the rest of each language record (lint command, format command, install hint, etc.) so internal commands are not exposed as part of the MCP surface.

#### Scenario: Listing all supported languages

- **WHEN** the client calls `list_languages`
- **THEN** the response enumerates every entry in `scripts/languages.json` with exactly two fields (`id`, `name`) per record

