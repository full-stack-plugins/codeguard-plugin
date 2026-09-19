# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "fsharp",
  "name": "F#",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".fs",
    ".fsi",
    ".fsx"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "dotnet",
    "fantomas",
    "--check"
  ],
  "gate": [],
  "format": [
    "dotnet",
    "fantomas"
  ],
  "install_hint": "dotnet tool install -g fantomas"
}
```
