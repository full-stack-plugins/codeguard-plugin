## ADDED Requirements

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