# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "crystal",
  "name": "Crystal",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".cr"
  ],
  "file_names": [],
  "markers": [
    "shard.yml"
  ],
  "requiresConfig": [
    "shard.yml"
  ],
  "probe": [],
  "lint": [
    "ameba"
  ],
  "gate": [],
  "format": [
    "crystal",
    "tool",
    "format"
  ],
  "install_hint": "brew install crystal-ameba"
}
```
