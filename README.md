# codestyle-check

Cross-language code style enforcement for AI coding assistants (ZCode, Claude Code, Codex, Kimi Code).

**The plugin that makes "did it pass lint?" an automatic question, not a manual one.**

---

## What it does

codestyle-check is a plugin that:

1. **Detects** the languages used in your project (Java / Rust / TypeScript / Python)
2. **Runs the appropriate linter** on every file the AI writes (PostToolUse hook)
3. **Blocks** the AI from continuing when lint fails (strict mode, on by default)
4. **Auto-fixes** when possible (spotless / cargo fmt / eslint --fix / ruff --fix)
5. **Double-checks** before commit (UserPromptSubmit hook on commit/push keywords)
6. **One-line bootstrap** to any repo: `/init` copies the right config + pre-commit hook + AGENTS.md

It is **language-differentiated**: the strongest native linter for each language, no reinventing wheels.

---

## Languages supported

| Language | Linter | Formatter |
|---|---|---|
| **Java** | `mvn javadoc:jar` + Checkstyle P3C | `mvn spotless:apply` |
| **Rust** | `cargo clippy -- -D warnings` + `cargo fmt --check` | `cargo fmt` |
| **TypeScript** | `eslint --max-warnings 0` | `eslint --fix` |
| **Python** | `ruff check` | `ruff check --fix` |

---

## Hook coverage

The plugin activates 4 hook points, covering the full lifecycle of an AI writing code:

| Hook | When | What |
|---|---|---|
| `SessionStart` | Session begins | Detect project languages, inject lint rules into AI context |
| `UserPromptSubmit` | User types "commit / push / 部署" | Final gate check — block if any linter fails |
| **`PostToolUse`** | **AI writes/edits a file** | **Run language-specific linter on the changed file; auto-fix; block if still failing** |
| `Stop` | Session ends | Summary of linter results from this session |

**The `PostToolUse` hook is the core innovation** — it transforms "fix lint errors after AI finishes" into "fix lint errors before AI moves on".

---

## Quick start

### As a user

```bash
# Install the plugin (platform-specific — see your platform's docs)
# ZCode: copy this repo to ~/.zcode/plugins/codestyle-check/
# Codex CLI: register via /plugins
# Kimi Code: similar mechanism

# Inside any project, ask AI:
/init    # bootstrap: copy linter config + pre-commit hook + AGENTS.md
/check   # run full lint suite with report
/fix     # auto-fix what can be fixed
```

### As an AI

When the plugin is active, you don't need to do anything manually:

- Every file you write is auto-linted immediately
- If lint fails and can't be auto-fixed, you'll see the error and must fix it before continuing
- When the user says "commit", you'll get a final all-linters-must-pass gate check
- At session end, you'll see a summary of which lints passed/failed

---

## Repository layout

```
codestyle-check-plugin/
├── .zcode-plugin/plugin.json     # ZCode manifest (primary)
├── .codex-plugin/plugin.json    # Codex manifest
├── .mcp.json                     # MCP server entry
├── hooks/
│   ├── hooks.json                # 4 hook definitions
│   ├── session_start.py          # SessionStart: detect language + inject rules
│   ├── post_tool_lint.py         # PostToolUse: the core enforcement hook
│   ├── user_prompt_validator.py  # UserPromptSubmit: commit gate
│   └── stop_summary.py           # Stop: session summary
├── scripts/
│   ├── detect_lang.py            # language detection + linter command table (shared)
│   ├── run_check.py              # main CLI: detect + run all linters + report
│   └── fix.py                    # auto-fix CLI
├── skills/
│   ├── codestyle-check/          # main entry skill
│   ├── codestyle-java/           # Java-specific rules + javadoc quickref
│   ├── codestyle-rust/           # Rust clippy + deny warnings
│   ├── codestyle-typescript/     # ESLint recommended + TS strict
│   ├── codestyle-python/         # ruff config + Python rules
│   └── codestyle-init/           # one-line bootstrap to any repo
├── commands/
│   ├── check.json                # /check
│   ├── fix.json                  # /fix
│   └── init.json                 # /init
├── linters/                      # copy-paste templates for each language
│   ├── checkstyle/
│   │   ├── p3c-javadoc-enforced.xml    # Alibaba P3C + javadoc enforced
│   │   └── checkstyle-suppressions.xml # suppress test classes / generated code
│   ├── clippy/
│   │   └── strict.toml                   # deny warnings + unwrap/expect/panic
│   ├── eslint/
│   │   └── recommended.cjs               # ESM flat config + TS rules
│   ├── ruff/
│   │   └── pyproject-snippet.toml        # [tool.ruff] block
│   └── pre-commit/
│       └── .pre-commit-config.template.yaml   # copy + customize
├── README.md
├── README.zh-CN.md
├── LICENSE                       # Apache-2.0
├── PRIVACY.md
└── TERMS.md
```

---

## Design choices

### Why per-language native linters, not a unified one?

Because **the native linter has the best rules** for each language:
- Java: Checkstyle has 200+ rules including javadoc, naming, imports
- Rust: clippy is maintained by the Rust team itself
- TypeScript: ESLint + @typescript-eslint is the de facto standard
- Python: ruff is 10-100x faster than flake8 with stricter rules

Reinventing a multi-language linter is impossible to keep current. **Pin to native, compose with hooks**.

### Why `PostToolUse` is more important than pre-commit?

| Layer | Latency | Force |
|---|---|---|
| PostToolUse (this plugin) | <2s | Forces AI to fix |
| pre-commit | 30s | Blocks git commit |
| CI | minutes | Blocks PR merge |

`PostToolUse` is **immediate feedback to the agent** while it's still in problem-solving mode — much higher fix rate than delayed CI feedback.

### Why strict mode is on by default?

Strict mode is what makes the plugin valuable. Without it, the plugin is just a fancy wrapper around tools you could run yourself. With strict mode, **linter failure is non-negotiable** — the AI must fix before continuing. That's the whole point.

---

## Configuration

User config in `~/.zcode/settings.local.yaml`:

```yaml
codestyle-check:
  enabled_languages: auto      # or [java, rust, typescript, python]
  strict_mode: true            # PostToolUse exits 2 on lint fail (BLOCKS AI)
  auto_fix_on_save: true       # try spotless/cargo fmt/eslint --fix/ruff --fix first
  lint_timeout_seconds: 120
```

---

## License

Apache-2.0 — see [LICENSE](./LICENSE).
