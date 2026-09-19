# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "swift",
  "name": "Swift",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".swift"
  ],
  "file_names": [],
  "markers": [
    "Package.swift"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "swiftlint"
  ],
  "gate": [],
  "format": [
    "swiftlint",
    "--fix"
  ],
  "install_hint": "brew install swiftlint"
}
```
