# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "zig",
  "name": "Zig",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".zig"
  ],
  "file_names": [],
  "markers": [
    "build.zig"
  ],
  "requiresConfig": [],
  "probe": [
    "zig",
    "version"
  ],
  "lint": [
    "zig",
    "fmt",
    "--check",
    "."
  ],
  "gate": [],
  "format": [
    "zig",
    "fmt"
  ],
  "install_hint": "内置于 Zig 工具链"
}
```
