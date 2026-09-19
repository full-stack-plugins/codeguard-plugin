# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "rust",
  "name": "Rust",
  "status": "stable",
  "since": "V0.1",
  "extensions": [
    ".rs"
  ],
  "file_names": [],
  "markers": [
    "Cargo.toml"
  ],
  "requiresConfig": [
    "Cargo.toml"
  ],
  "probe": [],
  "lint": [
    "cargo",
    "clippy",
    "--all-targets",
    "--",
    "-D",
    "warnings"
  ],
  "gate": [],
  "format": [
    "cargo",
    "fmt"
  ],
  "install_hint": null
}
```
