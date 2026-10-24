# CodeGuard (Code Quality)

> Evidence-backed lint, CVE scanning, controlled fixes, and Maven/Gradle impact analysis. Results distinguish pass, fail, unverified, and planned.

**Version**: 0.21.0 · **License**: Apache-2.0 · **Skills**: 68

[简体中文](README.md) · [Install](#installation) · [Quick start](#quick-start) · [Project layout](#project-layout)

## Positioning

CodeGuard is for teams that need a verifiable quality result before commit, push, or release. It does not stop at "lint ran"; it identifies the repository language and toolchain, runs the checks that actually exist, records command, version, dependency path, and result, and separates pass, fail, unverified, and planned.

Use it for:

- Multi-language lint and formatting gates
- Dependency CVE scanning and thresholds
- Controlled autofix and re-verification
- Maven/Gradle change-impact analysis
- Commit message, branch flow, and pre-release checks
- Explaining and reproducing CI failures

Do not use it for:

- Claiming a check passed when the tool is not installed
- Changing business semantics through autofix
- Bypassing branch protection or commit hooks

## At a glance

```text
repository / change / dependency manifest
        │
        ▼
CodeGuard skill (detect → select chain → execute → verify)
        │
        ├── language linter / formatter
        ├── CVE scanner
        └── architecture and impact analysis
        │
        ▼
PASS / FAIL / UNVERIFIED / PLANNED + evidence
```

## Capabilities and boundaries

| Capability | What it does | Boundary |
|---|---|---|
| Detection | Identify stack from extensions and project markers | Does not guess unconfigured languages |
| Lint | Run the checks actually available | Mark unverified when tools are missing |
| Fix | Reversible formatting and static-rule fixes | Never change business logic automatically |
| CVE | Scan dependencies and apply thresholds | Never hide HIGH/CRITICAL |
| Impact | Maven/Gradle module and call impact | Static inference is not runtime fact |
| Commit/branch | Validate messages and branch flow | Not a substitute for human review |

## Architecture and core flow

```text
Host / agent
   │  invokes codeguard-* skills
   ▼
skills/codeguard-*  ──►  CodeGuard engine
                              │
                              ├── linter / formatter
                              ├── CVE scanner
                              └── impact analyzer
                              │
                              ▼
                     result + command + version + evidence
```

Rules:

1. Detect the repository and available tools before choosing a chain.
2. When a tool is missing, report "unverified"; never claim pass.
3. Re-run the original command after every fix.
4. Never use `--no-verify` or admin rights to bypass a gate.

## Compatibility

| Item | Status |
|---|---|
| Host | Coding hosts with MCP support |
| Languages | 60+ languages, based on installed linters |
| Runtime | Follow the plugin manifest and repository environment |

## Installation

```bash
codex plugin marketplace add partme-ai/full-stack-plugins
codex plugin add codeguard@full-stack-plugins
```

Restart the host and start read-only:

> Detect this repository's languages and available checks. Do not modify files.

## Quick start

1. Detect language, build system, and existing configuration.
2. Run read-only lint and record command and version.
3. Separate PASS, FAIL, UNVERIFIED, and PLANNED.
4. Fix only reversible issues and keep a baseline.
5. Re-run the original command and report remaining risk.

## Configuration

Follow the repository's existing configuration; do not overwrite user files. Read credentials from secure environment only; never write them into `codeguard.json`.

## Extension contract

New language skills use the `codeguard-` prefix and declare the check command, missing-tool state, fix boundary, and re-verification requirement.

## Retry, idempotency, and recovery

- Read the log first: missing tool, bad configuration, or real code issue.
- Keep a baseline before fixing; re-verify after.
- Do not loop on unexplained failures.

## Data and state

- Checks write reports, not source changes.
- Fixes touch only allowed files.
- Reports keep command, version, path, and conclusion.

## Security

- Never write tokens into the repository or reports.
- Apply CVE thresholds honestly.
- On a suspected leak, rotate before cleaning.

## Observability and operation

Record check command, tool version, dependency path, exit code, and conclusion; review once before release.

## Development and verification

```bash
node --test
python3 -m pytest
```

## Packaging and release

Version matches manifests, marketplace, and tag; after release, reinstall and run one read-only check.

## Upgrade and migration

Confirm new language chains and tool versions before upgrading; re-run the baseline and compare conclusions.

## Troubleshooting

| Symptom | Check |
|---|---|
| Check did not run | Tool installed, command exists |
| Result unverified | Dependencies, network, permissions, config |
| Still failing after fix | Re-run original command and inspect diff |
| CI differs from local | Tool versions, lockfile, environment |

## Project layout

```text
codeguard-plugin/
├── .zcode-plugin/      # ZCode manifest
├── .codex-plugin/      # Codex manifest
├── skills/             # 68 skills
├── docs/               # check chains and verification
└── assets/             # icons and static assets
```

## Contributing and support

Include repository language, tool version, command, log, and conclusion. Do not attach credentials or production code.

## License

Apache-2.0. See [LICENSE](LICENSE).
