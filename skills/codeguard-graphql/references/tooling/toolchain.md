# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "graphql",
  "name": "GraphQL",
  "status": "stable",
  "since": "V0.4",
  "extensions": [
    ".graphql",
    ".gql"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
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
    "--ext",
    ".graphql",
    "."
  ],
  "gate": [],
  "format": [
    "npx",
    "eslint",
    "--ext",
    ".graphql",
    ".",
    "--fix"
  ],
  "install_hint": "graphql-eslint"
}
```
