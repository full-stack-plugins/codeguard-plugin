# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "html",
  "name": "HTML",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".html",
    ".htm"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [
    "npx",
    "--no-install",
    "htmlhint",
    "--version"
  ],
  "lint": [
    "npx",
    "--no-install",
    "htmlhint",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . \\( -name '*.html' -o -name '*.htm' \\) -type f -not -path '*/node_modules/*' -exec grep -L '<%' {} + | xargs -0 -r npx --no-install htmlhint"
  ],
  "format": [
    "prettier",
    "--write"
  ],
  "install_hint": "npm install -g htmlhint"
}
```
