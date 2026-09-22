# registry-driven-config Specification

## Purpose
TBD - created by archiving change add-linter-config-from-registry. Update Purpose after archive.
## Requirements
### Requirement: Per-language linter config files SHALL live in scripts/languages.json

Every language entry in `scripts/languages.json` SHALL have a `linter_config_files: list[str]` field. The default empty list `[]` SHALL be accepted for languages that have no project-level linter configuration files; for languages that historically had a hardcoded list in `hooks/env_check.py`, the field SHALL be populated with the same paths.

#### Scenario: A language entry is missing linter_config_files

- **WHEN** a contributor adds a new stable language without a `linter_config_files` field
- **THEN** the validator accepts it (defaults to empty list) but `env_check` will not report linter config for that language until the field is filled

### Requirement: env_check SHALL derive linter config from registry, not a hardcoded dict

`hooks/env_check.py::detect_linter_config` SHALL NOT maintain its own `LINTER_CONFIG_FILES` constant. It SHALL iterate over the loaded language registry and read each entry's `linter_config_files` field. Adding a new language to the registry with the field filled automatically updates env_check's report without any env_check change.

#### Scenario: A new stable language is added with linter_config_files

- **WHEN** a contributor adds a new language entry to `scripts/languages.json` with a non-empty `linter_config_files`
- **THEN** `env_check` on the next run includes that language in the linter-config report without any change to `env_check.py`

#### Scenario: env_check runs against a project with only one linter configured

- **WHEN** the project's root contains `ruff.toml` but no other linter configs
- **THEN** `env_check.detect_linter_config` returns `{"python": ["ruff.toml"]}` (or equivalent from the registry) and excludes all other languages

### Requirement: Known linter config filenames SHALL be populated for stable/beta languages

For each stable/beta language whose linter has well-known project-level configuration filenames, `scripts/languages.json` SHALL populate that entry's `linter_config_files` with those filenames. The population SHALL be conservative: only filenames that genuinely exist as that linter's configuration. Entries whose linter has no standard config filename (or where the filename is uncertain) MAY keep the empty list. `hooks/env_check.py` SHALL continue to report only files that actually exist, so an over-guessed filename never produces a false report.

#### Scenario: A Go project carries .golangci.yml

- **WHEN** the SessionStart hook runs in a repository whose root contains `.golangci.yml`
- **THEN** `detect_linter_config` reports `{"go": [".golangci.yml"]}` because `go.linter_config_files` includes it

#### Scenario: A guessed filename does not exist in the project

- **WHEN** a language lists a config filename that the current project does not contain
- **THEN** the hook reports nothing for that language/file pair — existence filtering prevents false positives

### Requirement: Linter config coverage SHALL be guarded against regression

`tests/test_validate_languages_json.py` SHALL assert that at least 25 stable/beta languages have a non-empty `linter_config_files` list, so a registry refactor cannot silently wipe the populated coverage.

#### Scenario: A refactor drops the populated fields

- **WHEN** a future edit removes `linter_config_files` from most stable/beta entries
- **THEN** the coverage test fails with the current populated count

