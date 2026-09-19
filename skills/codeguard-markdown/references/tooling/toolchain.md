# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "markdown",
  "name": "Markdown",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".md",
    ".markdown"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [
    "npx",
    "--no-install",
    "markdownlint-cli2",
    "--version"
  ],
  "lint": [
    "npx",
    "--no-install",
    "markdownlint-cli2"
  ],
  "gate": [],
  "format": [
    "markdownlint-cli2",
    "--fix"
  ],
  "install_hint": "npm install -g markdownlint-cli2"
}
```
