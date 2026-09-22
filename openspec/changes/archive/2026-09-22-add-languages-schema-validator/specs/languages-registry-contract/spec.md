## ADDED Requirements

### Requirement: languages.json SHALL be validated by scripts/validate_languages_json.py

A standalone validator SHALL live at `scripts/validate_languages_json.py`. It SHALL exit 0 on success and exit 1 when one or more schema or consistency rules fail. It SHALL accept `--path PATH` (default `scripts/languages.json`) and `--help`, with exit code 2 for argument errors.

#### Scenario: A clean registry passes

- **WHEN** `scripts/validate_languages_json.py` runs against the current `scripts/languages.json`
- **THEN** exit code is 0 and the output reports zero errors

#### Scenario: A duplicate id is rejected

- **WHEN** two language entries share the same `id`
- **THEN** the validator exits 1 and prints one `ERROR` line identifying the duplicated id

### Requirement: The validator SHALL enforce 11 schema and consistency rules

The validator SHALL check, at minimum:
1. top-level structure (`version`, `languages`, `status_levels` present)
2. id uniqueness across languages
3. status ∈ `status_levels`
4. extensions uniqueness across stable/beta languages
5. markers uniqueness across stable/beta languages
6. stable/beta require at least one non-empty `lint` or `format`; planned allows all-empty
7. `requiresConfig` is a list of strings (globs allowed)
8. id follows kebab-case
9. `since` present for stable/beta
10. extensions entries start with `.`
11. `lint` and `format` entries are non-empty strings when present

#### Scenario: A planned language registers a linter

- **WHEN** a `status: "planned"` entry has a non-empty `lint` field
- **THEN** the validator exits 1 with `ERROR` identifying the entry

### Requirement: languages.json validation SHALL run in CI

The `skills-check.yml` workflow SHALL run the validator and its unit tests on every push to `main` and on every PR.

#### Scenario: A PR introduces a duplicate id

- **WHEN** a contributor adds an entry with an existing `id`
- **THEN** `skills-check.yml` reports the validator failure and blocks merge via required status check