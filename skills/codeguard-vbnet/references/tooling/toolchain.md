# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "vbnet",
  "name": "Visual Basic .NET",
  "status": "stable",
  "since": "V0.4",
  "extensions": [
    ".vb"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [
    "*.sln",
    "*.csproj",
    "*.vbproj"
  ],
  "probe": [],
  "lint": [
    "dotnet",
    "format",
    "--verify-no-changes"
  ],
  "gate": [],
  "format": [
    "dotnet",
    "format"
  ],
  "install_hint": ".NET SDK 6+"
}
```
