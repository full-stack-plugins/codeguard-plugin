# asset-canonicalization Specification

## Purpose
TBD - created by archiving change consolidate-marketing-assets. Update Purpose after archive.
## Requirements
### Requirement: Zero-reference marketing assets SHALL be removed

Files in `assets/` with no references in any tracked file (manifests, READMEs, docs, market manifests) SHALL be removed. After removal, every remaining `assets/*` file SHALL appear in at least one `assets/README.md` row.

#### Scenario: Removing logo.png breaks no consumer

- **WHEN** `assets/logo.png` is deleted
- **THEN** no source file (README, manifest, marketplace, docs) refers to it; no image 404 appears in GitHub README rendering

#### Scenario: Removing official-logo.svg breaks no consumer

- **WHEN** `assets/official-logo.svg` is deleted
- **THEN** no manifest or marketplace entry refers to the SVG variant; no CDN URL points at the file

### Requirement: assets/README.md SHALL document every remaining file

After consolidation, `assets/README.md` SHALL list every remaining asset with: filename, role, current consumer(s), and source (where it was originally generated or acquired). Future asset additions SHALL update this file in the same commit.

#### Scenario: Adding a new marketing asset

- **WHEN** a contributor adds `assets/example.png`
- **THEN** the same commit updates `assets/README.md` to include the new file with its role and consumer

