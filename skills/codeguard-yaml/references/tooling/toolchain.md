# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "yaml",
  "name": "YAML",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".yml",
    ".yaml"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "yamllint",
    "."
  ],
  "gate": [],
  "format": [
    "yamllint",
    "."
  ],
  "install_hint": "pip install yamllint"
}
```
