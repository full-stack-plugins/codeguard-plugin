# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "svelte",
  "name": "Svelte",
  "status": "stable",
  "since": "V0.4",
  "extensions": [
    ".svelte"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    "eslint.config.ts",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.yml",
    ".pre-commit-config.yaml"
  ],
  "probe": [
    "npx",
    "--no-install",
    "eslint",
    "--version"
  ],
  "lint": [
    "npx",
    "--no-install",
    "eslint",
    "."
  ],
  "gate": [],
  "format": [
    "npx",
    "eslint",
    ".",
    "--fix"
  ],
  "install_hint": "eslint-plugin-svelte"
}
```
