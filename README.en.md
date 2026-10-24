# CodeGuard (代码质量防护)

> 19 条 CLI 已实现；check/fix/cve/dockerfile/impact 有真实执行入口。

**Version**: 0.21.1 · **License**: Apache-2.0 · **Skills**: 68

[简体中文](README.md)

## Positioning

CodeGuard is an independent plugin in the Partme Guard family. Its command prefix is codeguard. It is installed, versioned and executed independently.

## CLI Commands

| Command | Type |
| :--- | :--- |
| install | 独立入口 |
| uninstall | 独立入口 |
| upgrade | 独立入口 |
| version | 独立入口 |
| doctor | 独立入口 |
| status | 独立入口 |
| discover | 独立入口 |
| init | 独立入口 |
| check | 独立入口 |
| fix | 独立入口 |
| cve | 独立入口 |
| dockerfile | 独立入口 |
| impact | 独立入口 |
| explain | 独立入口 |
| report | 独立入口 |
| hooks install | 独立入口 |
| hooks status | 独立入口 |
| engine | 独立入口 |
| completion | 独立入口 |

## Installation

~~~bash
codex plugin marketplace add partme-ai/full-stack-plugins
codex plugin add codeguard-plugin@full-stack-plugins
~~~

## Quick Start

~~~bash
codeguard version
codeguard doctor
codeguard status
~~~

## Current Status

19 条 CLI 已实现；check/fix/cve/dockerfile/impact 有真实执行入口。

No PASS without real execution evidence. Unimplemented capabilities report DESIGN_ONLY or UNVERIFIED.

## Architecture

See product-docs/CodeGuard/ and docs/ for command lifecycle, read-only checks and evidence boundaries.

## Boundaries

- Not merged into a single Partme Guard command.
- Does not replace another Guard's domain decision.
- Does not auto-commit, auto-push or modify user code.

## Verification

~~~bash
python3 -m pytest -q
~~~

## License

Apache-2.0
