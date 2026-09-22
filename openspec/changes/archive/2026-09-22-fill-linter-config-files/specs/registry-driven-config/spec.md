## ADDED Requirements

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