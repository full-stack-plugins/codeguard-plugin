# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "toml",
  "name": "TOML",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".toml"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "taplo",
    "lint",
    "."
  ],
  "gate": [],
  "format": [
    "taplo",
    "format"
  ],
  "install_hint": "cargo install taplo-cli --locked"
}
```
