# Correct UserPromptSubmit trigger declarations

## Why

[Claude Code's Hooks reference](https://code.claude.com/docs/en/hooks) lists `UserPromptSubmit` among events without matcher support: the event fires for every submitted prompt. The plugin's three host manifests nevertheless declare a commit-keyword matcher. That declaration is not a host-side filter and makes the 120-second soft-gate timeout appear restricted to commit prompts.

## What Changes

Remove the unsupported matcher from all three mirrored manifests and state the real execution boundary: the Hook process starts for each prompt; its own `is_trigger` check must return before path probing, linter execution, Git inspection, or context output for ordinary questions. Preserve the existing soft commit-intent behavior and the separate PreToolUse Git gate. This correction does not claim that per-prompt process startup has been eliminated; the future Rust scheduler still needs a cheap default-host route.
