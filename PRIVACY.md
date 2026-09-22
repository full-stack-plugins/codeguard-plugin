# Privacy Policy

**partme-codeguard-plugin** is a **client-side** plugin that runs entirely on your machine.

## What data we collect

**Nothing.** The plugin:

- Does not phone home
- Does not send telemetry, analytics, or crash reports
- Reads local source files and Git blobs for checking; does not include a built-in source-upload or LLM telemetry service
- Does not require authentication

All operations happen locally:
- Local process execution (Maven verify / Gradle check, cargo clippy, ESLint, ruff)
- File reads (the file the AI just wrote)
- State files under CODEGUARD_HOME (default ~/.codeguard), diagnostic logs and temporary Git-content snapshots

## Network requests

The Java planner only reads local build descriptions. Executed build tools, wrappers, project plugins and CVE scanners may access package registries, wrapper distributions and vulnerability databases. Online vendor verification contacts the skill source repository. A local subprocess is not a network sandbox.

Project-defined code and tools run with the invoking user's permissions and may have their own data practices. Review untrusted project commands before executing checks. Logs may contain file paths and tool diagnostics; review them before sharing.

If you opt into `pip install pre-commit`, pre-commit itself may download hook repositories from GitHub — but that's pre-commit's network policy, not ours.

## Source code

The plugin is open source under Apache-2.0. You can audit every line.

## Contact

Issues: https://github.com/partme-ai/plugins/issues
