# Terms of Service

## What this plugin does

codestyle-check runs code quality linters on files you (or your AI assistant) modify. It does not execute your code; it only checks your code's surface syntax, style, and documentation completeness.

## What this plugin does NOT do

- It does not upload your source code anywhere
- It does not modify your code without your consent (auto-fix runs only when `auto_fix_on_save: true` and only after a lint failure, and can be disabled)
- It does not require network access
- It does not collect telemetry

## No warranty

The plugin is provided "AS IS" without warranty of any kind. The authors are not responsible for:

- Linter misconfigurations that cause false positives
- Auto-fix actions that break your code (auto-fix is best-effort and should be reviewed before commit)
- CI failures caused by linter version drift

## Your responsibilities

- Review the plugin's actions before commit
- Keep your `~/.zcode/settings.local.yaml` configuration under your own control
- Audit the open-source code at https://github.com/partme-ai/codestyle-check-plugin

## License

Apache-2.0. See [LICENSE](./LICENSE).

## Contact

Issues: https://github.com/partme-ai/codestyle-check-plugin/issues
