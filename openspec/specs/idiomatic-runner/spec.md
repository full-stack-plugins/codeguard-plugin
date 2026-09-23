# idiomatic-runner Specification

## Purpose
定义按语言执行的运行器契约：per-language 子进程执行收口在 scripts/run_per_language.py，入口（run_check.py/fix.py）不再自建 subprocess 运行器，退出码统一归一化，避免同一执行语义多处漂移。
## Requirements
### Requirement: Per-language execution SHALL live in scripts/run_per_language.py

The functions `run_check(languages, project_root, *, timeout=120, fix=False, dry_run=False) -> list[dict]` and `run_fix(languages, project_root, *, timeout=120, dry_run=False) -> list[dict]` SHALL be defined in `scripts/run_per_language.py`. They SHALL encapsulate the per-language subprocess invocation, exit-code normalization, and result aggregation.

#### Scenario: A CLI script delegates to run_per_language

- **WHEN** `scripts/run_check.py` parses args, identifies the project's languages, and needs to execute the lint pass
- **THEN** it calls `run_per_language.run_check(languages, project_root, timeout=args.timeout, fix=args.fix)` and prints the results

#### Scenario: fix.py delegates the format pass

- **WHEN** `scripts/fix.py` is invoked with a project root and detected languages
- **THEN** it calls `run_per_language.run_fix(languages, project_root, dry_run=args.dry_run)` and prints the results

### Requirement: run_check.py and fix.py SHALL NOT define subprocess-level runners themselves

After the refactor, `scripts/run_check.py` SHALL NOT define its own `run` / `check_one` / `fix_one` functions or invoke `subprocess.run` directly. Same for `scripts/fix.py`. Any subprocess execution lives in `run_per_language.py`.

#### Scenario: A new CLI flag is added to run_check.py

- **WHEN** a new flag (e.g. `--json`) requires reusing the lint pass
- **THEN** the implementer calls `run_per_language.run_check(...)` and converts the list of dicts to JSON, without re-implementing the subprocess loop

### Requirement: subprocess exit codes SHALL be normalized

`run_per_language` SHALL map subprocess outcomes to:
- 0 for success
- 124 for `subprocess.TimeoutExpired`
- 127 for `FileNotFoundError`

When a command is not found, the result SHALL include `stderr_tail == "command not found: <cmd>"`.

#### Scenario: linter binary is missing

- **WHEN** the project's linter binary is not installed
- **THEN** `run_per_language.run_check` returns a dict with `exit_code == 127` and `passed == False`

### Requirement: dry_run SHALL only print would-run lines

When `dry_run=True`, neither `run_check` nor `run_fix` SHALL spawn a subprocess; they SHALL emit one line per language showing the command that would have been executed.

#### Scenario: fix.py invoked with --dry-run on a mixed-language project

- **WHEN** the user passes `--dry-run` to `scripts/fix.py`
- **THEN** the output contains one `would run: ...` line per detected language and no subprocess is launched

