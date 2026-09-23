# CodeGuard plugin

> Parity: README.md and README.zh-CN.md must keep the same heading structure, local links and version strings; enforced by tests/test_readme_parity.py.

[English](README.md) · [简体中文](README.zh-CN.md)

![CodeGuard](assets/banner.svg)

## Positioning

CodeGuard provides native check evidence and guards supported Git commit/push calls from AI coding assistants. PostToolUse gives feedback, not blocking. Verified violations block the Git call; unavailable checks remain explicitly UNVERIFIED. Passing a configured check is not proof of complete code correctness.

The installed plugin version is recorded in its manifests. The architecture refactor keeps the existing 68 managed skills and focuses on reliable evidence, clear module ownership and Java project awareness.

### Runtime boundaries

| Surface | What it checks | Result |
|---|---|---|
| PostToolUse | Edited file, for file-scoped tools | Feedback, exit 0; project-level checks deferred |
| UserPromptSubmit | Working-tree changes relevant to commit intent | Advisory, never blocks the user message |
| PreToolUse Git gate | Proposed index snapshot or HEAD snapshot for push | Verified violations exit 2; uncertain checks report UNVERIFIED and fail open |
| CLI check / MCP check_code_style | Project checks, including Java build verification | Explicit status, reason, raw exit code, ordered execution trace and output log |
| pre-commit / CI | Independently configured checks | Separate acceptance; not replaced by hook success |

Hooks do not run in every host command surface automatically. Historical V0.5.4 installation evidence is not acceptance of this version in Codex, ZCode or Kimi.

### Verdict contract

| Status | Meaning | passed |
|---|---|---|
| PASS | An actual check completed successfully | true |
| FAIL | The checker reported a violation | false |
| UNVERIFIED | Missing tool, timeout, invalid configuration, unavailable evidence | false |
| SKIPPED | No applicable changed files | false |
| PLANNED | A plan exists or no executable adapter is configured | false |

CLI exit priority: FAIL → 2; otherwise UNVERIFIED/PLANNED → 1; verified success or no applicable changes → 0. Never interpret “not exit 2” as “passed”. Tools have different exit-code contracts: pylint 2 is not ESLint 2.

## Java project awareness

The legacy import facades under `scripts/` (`verdict.py`, `user_config.py`, `run_per_language.py`) are Deprecated compatibility shims: new code must import from the `codeguard` package. They are scheduled for removal in the next major version.

### Read-only planning

```bash
codeguard java-plan /path/to/project --json
codeguard java-plan /path/to/project --json --changed api/src/main/java/Api.java
codeguard check --lang java /path/to/project
```

The planner reads Maven POM / Gradle Groovy or Kotlin DSL, prefers project wrappers, maps files to modules and computes reverse transitive dependencies. Changing api can require checking service and app even if their files did not change. Deletions, resources and build descriptors are included.

Maven plans use verify with -DskipTests (test code still compiles; only execution is skipped), with -pl and -am for a safe subset. Gradle plans use root check or affected :module:check tasks with -x test. The default level checks compilation, packaging and lifecycle-bound static checks; test execution belongs to CI or an explicit java.commands declaration. Profiles, unresolved properties, inherited dependencies or recognized dynamic/composite Gradle builds expand the plan conservatively. Planning never executes a build, downloads dependencies, installs tools or initializes CodeGraph.

### Explicit project commands

A root codeguard.json can declare authoritative argv lists:

```json
{
  "java": {
    "commands": [
      ["./mvnw", "verify", "-Pquality"]
    ]
  }
}
```

Commands run in order, stopping on failure. They are trusted project configuration, not shell strings. Declaring commands is also how a project opts into a stronger level than the default — for example the full verify including test execution shown above. Running check or the Git gate executes project builds and may run project plugins; the default level skips test execution (-DskipTests / -x test), but configured commands or plugin-bound tasks may run tests, and package registries may be accessed — this is **not a sandbox**.

Coverage is module-level, not a symbol call graph or business-semantic proof. A successful verify/check does not establish that Checkstyle, PMD, SpotBugs or tests are configured comprehensively. Inspect the plan's gaps and reasons.

## Git content integrity

A plain commit checks the index, not an unstaged repair. Supported preceding git add operations overlay predicted worktree paths; in a direct command chain without shell substitution, an add after the final commit is not projected backward into that commit or a following push. Pure push checks HEAD and upstream differences. Without a resolvable upstream, the HEAD tree is checked. Sensitive-file rules use the same proposed scope; removing a sensitive file is not treated as introducing it.

Checks materialize temporary Git blobs without stash, checkout or modifying the real index. The exact-content gate does not reuse the soft working-tree cache. Missing ignored dependencies remain UNVERIFIED rather than silently falling back to different source content.

Limits: 20,000 tracked files / 256 MiB Git content / 32 MiB per overlay file. Symlinks, submodules, conflicts and unsupported content need separate validation. Complex shell rewrites, arbitrary Git refspecs, dynamic aliases and concurrent edits are not a fully modeled transaction. A hook is not a replacement for protected-branch CI.
One statically readable layer of bash/sh/zsh `-c` or script execution is included in repository and staging analysis; unmodelled indirect Git operations are blocked as UNVERIFIED. Dynamic scripts and subprocess calls assembled by Python/Node remain outside this static model.

There is no “historical debt” exemption based only on an unchanged diagnostic filename; a modified API can break an unchanged caller.

## CLI and MCP

### CLI

```bash
# Run directly from this checkout; no global installation required.
./bin/codeguard detect /path/to/project
./bin/codeguard check /path/to/project
./bin/codeguard fix /path/to/project --dry-run
./bin/codeguard fix /path/to/project
./bin/codeguard fix /path/to/project --all
./bin/codeguard cve /path/to/project --json
./bin/codeguard cve /path/to/project --ecosystem universal --severity HIGH
```

fix defaults to Git-changed files; project-wide formatters require explicit --all. A non-Git CLI directory retains the legacy full-scope behavior. --fix may modify files; it is not a preview.

CVE exits: 0 pass, 1 unverified, 2 findings, 3 invalid ecosystem. Maven/npm/pip-audit/cargo-audit/Trivy results require structured report evidence. Network failures are not vulnerabilities. npm moderate maps to MEDIUM; after npm audit fix the new scan controls the verdict. Native Python/Rust findings without comparable severity remain UNVERIFIED above LOW, with findings preserved; explicitly select Trivy to assess severity. Python audits project requirements/pyproject, not the host environment.

### MCP server

```bash
# Requires the dependencies declared in requirements.txt.
python3 scripts/run_check.py --mcp /path/to/project
```

| Tool | Contract |
|---|---|
| check_code_style | Per-language status/reason/passed/raw exit code, per-command status metadata and full failure log path |
| auto_fix | Format Git-changed files and recheck the same scope; refuse unbounded project formatters; fixed means actual modifications |
| list_languages | Registry ids and display names |
| analyze_java_impact | Read-only plan; accepts path and optional changed array |

Output logs default to <project>/out/.codeguard-last.log; CLI --quiet disables log writing. A failed multi-command check logs output from every executed check. Diagnostic logs, including truncated PostToolUse output, are replaced atomically with owner-only file permissions on POSIX; a symlinked output directory disables log writing without changing the check verdict. The MCP execution trace reports phase, sequence, program, exit/failure and output lengths; it does not echo argv, environment overrides or captured output. MCP auto_fix also keeps formatter argv/stderr out of its JSON result; available formatter diagnostics are written to a private <project>/out/.codeguard-fix.log and returned by path. Local logs can contain sensitive checker output: keep them out of version control. MCP auto_fix does not write when a Git scope cannot be established.

## Configuration and coverage

Root codeguard.json may set gate_scope to delta or repo and customize extension/exclusion detection. User settings retain enabled_languages, auto_fix_on_save and lint_timeout_seconds. See the [hook protocol](hooks/__protocol__.md).

The registry contains **54 Stable adapters and 3 Planned entries**. “Stable” does not certify every toolchain or project. Markdown/YAML require project configuration; missing configuration is UNVERIFIED. Markdown findings are advisory. Generated and dependency directories are excluded from ordinary lint scope, not automatically accepted for commit. Python checks honor the project's own ruff configuration (ruff.toml / .ruff.toml / [tool.ruff]); when none exists, codeguard injects a default rule set pinned to the CI baseline (ruff==0.16.8) so verdicts do not drift with whichever ruff version a machine happens to have. Full command inventory: [languages](docs/LANGUAGES.md).

The explicit escape hatch git config codeguard.skipGate true bypasses the hook's language gate and is recorded in session summaries. It does not cover the commit-content safety scan (secret/credential path patterns): that scan runs regardless of config, inline `-c codeguard.skipGate=true` or chained escapes — only the process environment variable `CODEGUARD_SKIP_GATE` (1/true/yes, set by the user; inline assignment does not reach the hook process) suppresses it. Shared hook state lives under CODEGUARD_HOME (default ~/.codeguard).
The Git gate statically inspects one readable shell-wrapper layer, including bare assignment, env, command and sudo prefixes; the same prefix rules apply to skipGate changes and one-shot bypasses. It does not execute or fully interpret shell scripts.

## External skills

The **68** portable skills are authored in [full-stack-skills/codeguard-skills](https://github.com/full-stack-skills/codeguard-skills). This plugin packages immutable **v0.1.2** through skills.lock.json, pinning tag, commit and per-skill digests.

Do not edit locked skill directories. Update/release the source skills, update the lock and run the vendor tool. Only declared entries in plugin-local-skills.json may be plugin-owned; currently none are declared. See [authoring rules](docs/CODEGUARD_SKILLS_SPEC.md).

```bash
python3 scripts/vendor/skill_vendor.py check --offline
python3 scripts/vendor/skill_vendor.py check
```

## Verification and remaining work

```bash
python3 -m unittest discover -s tests -q
python3 tests/run_all.py
python3 scripts/validate_languages_json.py
python3 scripts/check_architecture.py
ruff check hooks scripts tests
```

Tests include real temporary Git repositories, native subprocess fixtures and official-SDK stdio MCP calls. Fixture wrapper success is not a real Maven/Gradle integration build. Live Codex/ZCode/Kimi loading, real project builds, online CVE scanner runs and precision/recall benchmarks require separate acceptance.

Current implementation and evidence: [architecture and extension guide](docs/current-architecture.md), [refactor verification](openspec/changes/archive/2026-09-23-refactor-codeguard-architecture/verification.md). Earlier documents remain historical context: [verdict and Java architecture](docs/verdict-java-architecture.md), [prior verification](docs/verification-verdict-java.md), [original architecture](docs/partme-codeguard-plugin-Architecture.zh_CN.md), [roadmap](docs/technical-roadmap.zh_CN.md).

Version history: see [CHANGELOG.md](CHANGELOG.md) for release highlights by version.

## License and privacy

Apache-2.0 — [LICENSE](./LICENSE). Native build/scanning tools may access dependency registries and vulnerability databases; review [PRIVACY.md](./PRIVACY.md) and [TERMS.md](./TERMS.md).
