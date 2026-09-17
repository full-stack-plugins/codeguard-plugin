# Privacy Policy

codestyle-check is a **client-side** plugin that runs entirely on your machine.

## What data we collect

**Nothing.** The plugin:

- Does not phone home
- Does not send telemetry, analytics, or crash reports
- Does not read or transmit your source code
- Does not require authentication

All operations happen locally:
- Linter execution (`mvn javadoc:jar`, `cargo clippy`, `npx eslint`, `ruff check`)
- File reads (the file the AI just wrote)
- State files (`.session_state.json` for Stop hook summary)

## Network requests

The plugin **does not make network requests**. All linters it invokes are local binaries installed on your machine.

If you opt into `pip install pre-commit`, pre-commit itself may download hook repositories from GitHub — but that's pre-commit's network policy, not ours.

## Source code

The plugin is open source under Apache-2.0. You can audit every line.

## Contact

Issues: https://github.com/partme-ai/codestyle-check-plugin/issues
