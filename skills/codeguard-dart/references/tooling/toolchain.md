# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "dart",
  "name": "Dart / Flutter",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".dart"
  ],
  "file_names": [],
  "markers": [
    "pubspec.yaml"
  ],
  "requiresConfig": [
    "pubspec.yaml"
  ],
  "probe": [],
  "lint": [
    "dart",
    "analyze"
  ],
  "gate": [],
  "format": [
    "dart",
    "format",
    "."
  ],
  "install_hint": "Dart SDK 内置"
}
```
