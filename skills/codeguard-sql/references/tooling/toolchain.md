# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "sql",
  "name": "SQL",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".sql"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "sqlfluff",
    "lint",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . -name '*.sql' -type f -not -path '*/node_modules/*' -print0 | xargs -0 -r sqlfluff lint"
  ],
  "format": [
    "sqlfluff",
    "fix"
  ],
  "install_hint": "pip install sqlfluff"
}
```
