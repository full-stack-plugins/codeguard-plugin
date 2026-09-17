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
| Current version | `0.2.0` |
| ZCode manifest | `.zcode-plugin/plugin.json` |
| Codex manifest | `.codex-plugin/plugin.json` |
| MCP server | `python3 scripts/run_check.py --mcp` (stdio JSON-RPC) |
| Primary language | Python 3.10+ (hooks), YAML/JSON (config) |
| License | Apache-2.0 |

## Supported languages

Language coverage is **aligned with [codegraph supported-languages](https://github.com/colbymchenry/codegraph#supported-languages)** — all 32 languages are detected; 11 have active linter enforcement (more per release, see [docs/LANGUAGES.md](docs/LANGUAGES.md)).

| Status | Languages |
|---|---|
| **Stable** (auto-enforced, V0.1) | Java, Rust, TypeScript/JavaScript, Python |
| **Beta** (enforced, V0.2) | Go, C#, Kotlin, Swift, PHP, Ruby, Scala |
| **Planned** (detected, linter on roadmap) | C, C++, Objective-C, Dart, Vue, Svelte, Astro, Solidity, Terraform/OpenTofu, Nix, Lua, Luau, CFML, COBOL, VB.NET, Erlang, Pascal/Delphi, R, ArkTS, Metal, Liquid, CUDA |

Full table with per-language lint/format commands: [docs/LANGUAGES.md](docs/LANGUAGES.md).

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
├── .mcp.json                     # MCP server entry (stdio)
├── hooks/
│   ├── hooks.json                # 4 hook definitions
│   ├── session_start.py          # SessionStart: detect language + inject rules
│   ├── post_tool_lint.py         # PostToolUse: core enforcement hook
│   ├── user_prompt_validator.py  # UserPromptSubmit: commit gate
│   └── stop_summary.py           # Stop: session summary
├── scripts/
│   ├── detect_lang.py            # language detection + linter command table (shared)
│   ├── run_check.py              # main CLI: detect + run all linters + report
│   └── fix.py                    # auto-fix CLI
├── skills/                       # 6 SKILL.md (主入口 + 4 语言 + init)
│   ├── codeguard/
│   ├── codestyle-init/
│   ├── codestyle-java/
│   ├── codestyle-rust/
│   ├── codestyle-typescript/
│   └── codestyle-python/
├── commands/                     # 3 slash commands (/check /fix /init)
│   ├── check.json
│   ├── fix.json
│   └── init.json
├── linters/                      # copy-paste templates per language
│   ├── checkstyle/               # Alibaba P3C + javadoc enforced
│   ├── clippy/                   # deny warnings + unwrap/expect/panic
│   ├── eslint/                   # recommended + TS rules
│   ├── ruff/                     # [tool.ruff] block
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
| **ZCode** | `.zcode-plugin/plugin.json` | `~/.zcode/plugins/partme-codeguard-plugin/` | ✅ V0.1 |
| **Codex CLI** | `.codex-plugin/plugin.json` | `~/.codex/plugins/partme-codeguard-plugin/` | ✅ V0.1 |
| **Claude Code** | (uses Codex manifest via marketplace) | `~/.claude/plugins/partme-codeguard-plugin/` | 🔧 V0.2 |
| **Kimi Code** | (uses Codex manifest) | `~/.kimi/plugins/partme-codeguard-plugin/` | 🔧 V0.2 |

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
