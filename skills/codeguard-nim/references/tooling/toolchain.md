# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "nim",
  "name": "Nim",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".nim"
  ],
  "file_names": [],
  "markers": [
    ".nimble"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "nim",
    "check",
    "src"
  ],
  "gate": [],
  "format": [
    "nimpretty",
    "-r",
    "."
  ],
  "install_hint": "nimpretty 内置于 Nim"
}
```
