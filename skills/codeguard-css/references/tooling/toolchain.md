# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "css",
  "name": "CSS / SCSS / Sass / LESS",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".css",
    ".scss",
    ".sass",
    ".less"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [
    "npx",
    "--no-install",
    "stylelint",
    "--version"
  ],
  "lint": [
    "npx",
    "--no-install",
    "stylelint",
    "**/*.css"
  ],
  "gate": [],
  "format": [
    "npx",
    "stylelint",
    "**/*.css",
    "--fix"
  ],
  "install_hint": "npm install --save-dev stylelint stylelint-config-standard"
}
```
