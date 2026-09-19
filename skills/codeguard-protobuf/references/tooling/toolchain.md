# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "protobuf",
  "name": "Protobuf",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".proto"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [
    "buf.yaml",
    "buf.gen.yaml",
    "buf.work.yaml"
  ],
  "probe": [],
  "lint": [
    "buf",
    "lint"
  ],
  "gate": [],
  "format": [
    "buf",
    "format"
  ],
  "install_hint": "brew install bufbuild/buf/buf"
}
```
