# partme-codeguard-plugin Plugin

<p align="center">
  <img src="assets/banner.svg" alt="partme-codeguard-plugin — Make AI-written code pass lint on first try. Supports ZCode, Claude Code, Codex CLI, and Kimi Code." width="100%">
</p>

<p align="center">
  <strong>Lint on every AI-written file. Block on failure. Strict by default.</strong><br>
  Cross-language code style enforcement for AI coding assistants: Java / Rust / TypeScript / Python.
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="docs/partme-codeguard-plugin-Architecture.zh_CN.md">Architecture</a> ·
  <a href="docs/5、partme-codeguard-plugin-技术方案与路线.md">Technical roadmap</a>
</p>

---

## Positioning

`partme-codeguard-plugin` makes AI coding assistants (ZCode, Claude Code, Codex CLI, Kimi Code) produce code that **passes linters on the first attempt**. Instead of finding out at commit-time that your AI forgot a Javadoc tag or used `unwrap()`, this plugin runs the right linter the moment the AI writes a file — and blocks the AI from continuing until the lint passes.

It is a **constraint-type plugin** for AI assistants, not a productivity-type plugin: it produces no code itself, but enforces rules on the code the AI produces.

### Who it is for

- Backend engineers whose AI assistant writes Java but skips Javadoc tags.
- Rust teams where `cargo clippy` is non-negotiable, but AI reaches for `unwrap()` out of habit.
- TypeScript / frontend teams tired of `any` types and unused imports from AI.
- Python teams who want `ruff` discipline on AI-generated code.
- Engineering leads who want **CI-like lint feedback inside the AI's "thinking mode"** instead of minutes later in PR review.

### What problem it solves

| Problem | What this plugin provides | Verifiable entry point |
|---|---|---|
| AI skips Javadoc tags, javadoc errors only surface on `mvn install` | PostToolUse hook auto-runs `mvn javadoc:jar` after each AI-written `.java` | `hooks/post_tool_lint.py`, [Architecture §3.2](docs/partme-codeguard-plugin-Architecture.zh_CN.md) |
| AI uses `unwrap()` in Rust business code | `cargo clippy -- -D warnings` runs on each `.rs` file | [Architecture §2.1](docs/partme-codeguard-plugin-Architecture.zh_CN.md) |
| AI introduces `any` and unused vars in TypeScript | `eslint --max-warnings 0` blocks the AI | `linters/eslint/recommended.cjs` |
| "did it pass lint?" is asked manually after every AI session | Stop hook summarizes lint pass/fail counts | `hooks/stop_summary.py` |
| pre-commit and CI catch issues 30s+5min late, by then the AI has moved on | Three-layer defense: hook (<2s) → pre-commit (30s) → CI (5min) | [Technical roadmap §1](docs/5、partme-codeguard-plugin-技术方案与路线.md) |

## At a glance

```text
AI writes file
      │
      ▼
┌──────────────────────────────────────────────────────────┐
│ partme-codeguard-plugin                                    │
│  ① detect  project language (java / rust / ts / python)  │
│  ② lint    run native linter on the file                 │
│  ③ auto-fix spotless / cargo fmt / eslint / ruff          │
│  ④ block   exit 2 if lint still fails (strict mode)      │
│  ⑤ summary session-end lint pass/fail counts             │
└──────────────────────────────────────────────────────────┘
      │
      ▼
AI code that passes lint on first try
```

| Property | Value |
|---|---|
| Plugin ID | `partme-codeguard-plugin` |
| Hosts | ZCode, Claude Code, Codex CLI, Kimi Code |
| Current version | `0.5.3` |
| ZCode manifest | `.zcode-plugin/plugin.json` |
| Codex manifest | `.codex-plugin/plugin.json` |
| MCP server | Not published until the SDK-backed protocol implementation is ready; use the CLI and hooks |
| Primary language | Python 3.10+ (hooks), YAML/JSON (config) |
| License | Apache-2.0 |

## Supported languages

**53 languages Stable (auto-enforced) + 4 Planned with platform tooling** — the widest coverage of any code-governance plugin. Every registered language has a SKILL; Planned languages are the ones without an independent CLI linter (platform IDE diagnostics only). Full per-language table: [docs/LANGUAGES.md](docs/LANGUAGES.md).

| Status | Languages |
|---|---|
| **Stable** (53, auto-enforced) | Java, Rust, TypeScript/JavaScript, Python, Go, C#, Kotlin, Swift, PHP, Ruby, Scala, Shell, Dockerfile, YAML, Elixir, CSS/SCSS, Markdown, SQL, TOML, HTML, Protobuf, Terraform/OpenTofu, Nix, Dart, Solidity, Ansible-playbooks, Perl, Groovy, Clojure, PowerShell, Zig, Nim, Crystal, Julia (format-only), Pascal (format-only), Elm, Lua, Luau, C++ (clang-tidy), Objective-C, CUDA, GraphQL, Protobuf digest, VB.NET, Erlang, R, CFML — and more; see LANGUAGES.md |
| **Planned** (4, no independent CLI linter) | Metal, ArkTS (HarmonyOS), COBOL, Liquid (Shopify theme-check 已列为工具，待接通) |
## Governance skills (Git & Security) (Git & Security)

Beyond linting, codeguard ships standalone governance skills sourced from the team's engineering-standards wiki:

| Skill | Covers |
|---|---|
| `codeguard-git-branch` | 7 mainstream models — Gitflow, Gitflow+ (team), GitLab branch rules, GitHub Flow, GitLab Flow, Trunk-Based Development, OneFlow, Release Flow — with model detection, branch naming gates (`feature/{version}_{function}_{author}_{datetime}`), merge-direction gates, merge strategy (merge/squash/rebase) |
| `codeguard-git-commit` | Conventional Commits (Angular regex gate `linters/git/commit-msg`), Gitmoji prefixes, Udacity long-form, commitlint tooling |
| `codeguard-security-code` | Source & config leakage prevention, CVE dependency scanning (dependency-check / trivy / npm audit / MurphySec) |
| `codeguard-security-api` | Privilege-escalation guards (Shiro / Spring Security annotations), data-permission checks, 3-layer file-upload control, apikey+timestamp+signature |
| `codeguard-security-data` | Encrypted-at-rest fields (SM2/SM3/SM4 国密), response masking, single-device login, MLPS (等保) & commercial-crypto evaluation (密评) notes |
| `codeguard-dockerfile` | Dockerfile security risks — root user, latest tag, ADD abuse, sudo, secrets in layers, missing HEALTHCHECK (hadolint + trivy config) |

The commit gate is pre-wired in the pre-commit template (`stages: [commit-msg]`); branch and security skills guide the AI during branch creation, interface development, and pre-merge review.

### External skill source

The 68 portable skills are authored in [full-stack-skills/codeguard-skills](https://github.com/full-stack-skills/codeguard-skills), not independently inside this plugin. This repository vendors the complete `v0.1.0` snapshot so installed plugins work offline:

- `skills.lock.json` pins the upstream repository, immutable tag, resolved commit, managed skill names, and per-skill SHA-256 digests.
- `python3 scripts/vendor/skill_vendor.py update` refreshes only the skill names listed in the lock.
- `python3 scripts/vendor/skill_vendor.py check --offline` verifies the packaged snapshot; omit `--offline` to verify the upstream ref and content too.
- Do not directly edit a locked skill directory. Change and release `codeguard-skills`, update the lock ref, then run the vendor update.
- Plugin-specific skills may remain under `skills/` only when they are intentionally absent from `skills.lock.json` and explicitly listed in `plugin-local-skills.json`; the vendor preserves declared directories and rejects undeclared exceptions.

Hooks, linters, commands, MCP wiring, and executable scripts remain plugin-owned. The authoring standard is documented in [docs/CODEGUARD_SKILLS_SPEC.md](docs/CODEGUARD_SKILLS_SPEC.md).

## Capabilities and boundaries

### Supported

| Capability | Input | Output | Limit | Status |
|---|---|---|---|---|
| Per-file language detection | file path from hook payload | language string (`java`/`rust`/`typescript`/`python`) | — | Stable |
| Language-specific lint | `mvn javadoc:jar` / `cargo clippy` / `npx eslint` / `ruff check` | exit code + stderr | timeout configurable (default 120s) | Stable |
| Auto-fix on failure | `mvn spotless:apply` / `cargo fmt` / `eslint --fix` / `ruff --fix` | retry lint with fixed files | best-effort, no business-logic changes | Stable |
| Commit/push gate | "commit" / "push" / "deploy" keyword in user prompt | run all linters, exit 2 if any fails | — | Stable |
| One-line project bootstrap | `/init` slash command | copy linter configs + `.pre-commit-config.yaml` + AGENTS.md snippet | — | Stable |
| Session-end summary | Stop hook | table of lint pass/fail/auto-fix counts | — | Stable |

### Three-layer defense

The plugin does not replace pre-commit or CI — it adds a **faster** layer in front of them.

| Layer | Latency | Force | Purpose |
|---|---|---|---|
| **PostToolUse hook (this plugin)** | <2s | Block AI from continuing | Catch errors while the AI is still in "fix it now" mode |
| pre-commit | 30s | Block git commit | Catch errors when the user is ready to commit |
| CI | minutes | Block PR merge | Last-resort gate |

PostToolUse is the **highest-ROI** layer because it gives the AI feedback **while it still cares**.

### Not responsible for

- Running your code. This plugin lints; it does not execute.
- Generating code. This plugin enforces rules on what AI generates.
- Replacing peer review. Linters catch mechanical errors; humans catch design errors.
- Cloud / SaaS linter services. This plugin is **strictly client-side** (see [PRIVACY.md](./PRIVACY.md)).
- Languages without an active linter yet (Planned tier above — their files are detected but safely skipped by the hook).

## Quick start

### CLI (codeguard)

```bash
# Optional one-time setup: put the CLI on PATH
ln -s $PWD/bin/codeguard /usr/local/bin/codeguard

codeguard check                     # multi-language lint gate
codeguard fix                       # auto-fix lint issues
codeguard cve                       # CVE dependency scan (Maven/npm/Python/Rust orchestration)
codeguard cve --fix                 # scan + auto-fix (npm audit fix)
codeguard cve --severity MEDIUM     # gate threshold down to medium
codeguard detect                    # detect project languages
```

Maven CVE scanning uses OWASP dependency-check (pom snippet in
`linters/maven/dependency-check-pom-snippet.xml`; build fails at `CVSS>=7`).
**A finding must be fixed, not filed away**: every report ships with the fix command
per ecosystem (upgrade paths / suppression filing); npm supports `audit fix` auto-repair.

### As a user

```bash
# Step 1: install (one of these, per your host)
ln -s $PWD ~/.zcode/plugins/partme-codeguard-plugin
ln -s $PWD ~/.codex/plugins/partme-codeguard-plugin
ln -s $PWD ~/.kimi/plugins/partme-codeguard-plugin

# Step 2: in any project, ask the AI:
/init    # copy linter configs + .pre-commit + AGENTS.md
/check   # run full lint suite with report
/fix     # auto-fix what can be fixed
```

### As an AI

When this plugin is active, you do **not** need to do anything manually:

- Every file you write is auto-linted immediately.
- If lint fails and cannot be auto-fixed, you will see the error and **must fix before continuing**.
- When the user says "commit", you will receive a final all-linters-must-pass gate check.
- At session end, you will see a summary of which lints passed/failed.

## Configuration

User config in `~/.zcode/settings.local.yaml` (ZCode) or equivalent for other hosts:

```yaml
codeguard:
  enabled_languages: auto      # or [java, rust, typescript, python]
  strict_mode: true            # PostToolUse exit 2 on lint fail (BLOCKS AI)
  auto_fix_on_save: true       # try spotless/cargo fmt/eslint --fix/ruff --fix first
  lint_timeout_seconds: 120
```

| Key | Default | Effect |
|---|---|---|
| `enabled_languages` | `auto` (detect) | Restrict which linters run |
| `strict_mode` | `true` | Whether lint failure blocks AI |
| `auto_fix_on_save` | `true` | Whether to attempt auto-fix before reporting failure |
| `lint_timeout_seconds` | `120` | Per-linter timeout |

## Repository layout

```
partme-codeguard-plugin/
├── .zcode-plugin/plugin.json     # ZCode manifest (primary)
├── .codex-plugin/plugin.json    # Codex CLI manifest
├── hooks/
│   ├── hooks.json                # 4 hook definitions
│   ├── env_check.py              # SessionStart: detect language + inject rules
│   ├── post_tool_lint.py         # PostToolUse: core enforcement hook
│   ├── user_prompt_validator.py  # UserPromptSubmit: commit gate
│   └── stop_summary.py           # Stop: session summary
├── scripts/
│   ├── detect_lang.py            # language detection + linter command table (shared)
│   ├── run_check.py              # main CLI: detect + run all linters + report
│   ├── fix.py                    # auto-fix CLI
│   └── vendor/skill_vendor.py    # lock-driven external skill vendor/check
├── skills.lock.json              # upstream tag/commit + managed skills + SHA-256 digests
├── plugin-local-skills.json      # explicit plugin-only skill exceptions (currently empty)
├── skills/                       # 68 vendored skills from codeguard-skills v0.1.0
│   ├── codeguard/                # main entry
│   ├── codeguard-init/           # one-line bootstrap
│   ├── codeguard-{java,rust,typescript,python}/
│   ├── codeguard-{go,csharp,kotlin,swift,php,ruby,scala}/   # V0.2 languages
│   ├── codeguard-git-{branch,commit}/                      # branch & commit governance
│   └── codeguard-security-{code,api,data}/                 # security governance
├── commands/                     # 3 slash commands (/check /fix /init)
│   ├── check.json
│   ├── fix.json
│   └── init.json
├── bin/codeguard                 # CLI entry (check / fix / cve / detect / init)
├── linters/                      # copy-paste templates per language
│   ├── checkstyle/               # Alibaba P3C + javadoc enforced
│   ├── clippy/                   # deny warnings + unwrap/expect/panic
│   ├── eslint/                   # recommended + TS rules
│   ├── ruff/                     # [tool.ruff] block
│   ├── maven/                     # OWASP dependency-check pom snippet
│   └── git/                        # commit-msg gate script
│   └── pre-commit/               # .pre-commit-config.template.yaml
├── docs/
│   ├── partme-codeguard-plugin-Architecture.zh_CN.md
│   └── 5、partme-codeguard-plugin-技术方案与路线.md
├── README.md                     # this file
├── README.zh-CN.md               # Chinese
├── LICENSE                       # Apache-2.0
├── PRIVACY.md                    # zero data collection
└── TERMS.md
```

## Compatibility

| Host | Plugin manifest | Install path | Status |
|---|---|---|---|
| **ZCode** | `.zcode-plugin/plugin.json` | `~/.zcode/cli/plugins/cache/<marketplace>/codeguard/<version>/` | ✅ V0.5.3 verified |
| **Codex CLI** | `.codex-plugin/plugin.json` | `~/.codex/plugins/cache/<marketplace>/codeguard/<version>/` | ✅ V0.5.3 verified |
| **Claude Code** | (uses Codex manifest via marketplace) | `~/.claude/plugins/partme-codeguard-plugin/` | 🔧 V0.2 |
| **Kimi Code** | `kimi.plugin.json` | `~/.kimi-code/plugins/managed/codeguard/` | ✅ V0.5.3 verified |

The hooks, scripts, linters, and skills are **shared across all hosts** — only the manifest differs.

## Verification

After install, smoke-test in any project:

```bash
# Should output ["java"] (or similar) and exit 0
python3 scripts/detect_lang.py /path/to/java-project

# Should print table of pass/fail per language
python3 scripts/run_check.py --timeout 60

# Should auto-fix what can be fixed and re-run lint
python3 scripts/fix.py --dry-run   # see what would change
python3 scripts/fix.py             # actually change
```

In any AI session, after writing a `.java` file, you should see in the AI log:

```
[codeguard] lint java: src/main/java/Foo.java
[codeguard] ❌ java lint failed for src/main/java/Foo.java
[codeguard] fix with: mvn -q spotless:apply
```

Exit code 2 if strict mode is on (the AI must fix); exit code 0 with warnings if strict mode is off.

## Related skills

- **[full-stack-doc](https://github.com/partme-ai/skills/tree/main/full-stack-doc)** — Documentation standard this plugin's `docs/` follows.
- **partme-blender-plugin** — Sibling plugin using the same hook/manifest/skills pattern.

## License

Apache-2.0 — see [LICENSE](./LICENSE).
