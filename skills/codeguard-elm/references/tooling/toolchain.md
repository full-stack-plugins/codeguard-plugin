# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "elm",
  "name": "Elm",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".elm"
  ],
  "file_names": [],
  "markers": [
    "elm.json"
  ],
  "requiresConfig": [
    "elm.json"
  ],
  "probe": [],
  "lint": [
    "elm-review"
  ],
  "gate": [],
  "format": [
    "elm-format",
    "--yes"
  ],
  "install_hint": "npm install -g elm-review elm-format"
}
```
