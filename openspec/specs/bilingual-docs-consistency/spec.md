# bilingual-docs-consistency Specification

## Purpose
TBD - created by archiving change add-readme-parity-gate. Update Purpose after archive.
## Requirements
### Requirement: README structural parity SHALL be enforced by tests/test_readme_parity.py

`tests/test_readme_parity.py` SHALL assert that `README.md` and `README.zh-CN.md` have: (1) identical heading-level sequences outside fenced code blocks, (2) identical sets of local link targets, and (3) identical sets of `x.y.z` version strings. Any single-sided edit to one README SHALL fail this test.

#### Scenario: The technical roadmap doc is renamed

- **WHEN** `docs/5、partme-codeguard-plugin-技术方案与路线.md` is renamed and only `README.md` links are updated
- **THEN** `test_readme_parity` fails on the local-link-target set difference

#### Scenario: The current version row is bumped in one language only

- **WHEN** `| Current version | 0.6.7 |` is updated in `README.md` but `README.zh-CN.md` still says `0.5.4`
- **THEN** `test_readme_parity` fails on the version-string set difference

### Requirement: README mirror edits SHALL land in the same commit

Any change to one README's structure, links, or version strings SHALL be mirrored into the other README in the same commit. Both files SHALL carry a parity note near the top pointing at `tests/test_readme_parity.py`.

#### Scenario: A contributor adds a new section to README.md

- **WHEN** a new `## Section` is added to `README.md` with links and version strings
- **THEN** the same commit adds the translated `## 章节` to `README.zh-CN.md` at the same position, and CI passes

