# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "typescript",
  "name": "TypeScript / JavaScript",
  "status": "stable",
  "since": "V0.1",
  "extensions": [
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs"
  ],
  "file_names": [],
  "markers": [
    "package.json",
    "deno.json"
  ],
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
    ".",
    "--max-warnings",
    "0"
  ],
  "gate": [],
  "format": [
    "npx",
    "eslint",
    ".",
    "--fix"
  ],
  "install_hint": "项目需安装 eslint"
}
```
