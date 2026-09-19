# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "go",
  "name": "Go",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".go"
  ],
  "file_names": [],
  "markers": [
    "go.mod"
  ],
  "requiresConfig": [
    "go.mod"
  ],
  "probe": [],
  "lint": [
    "go",
    "vet",
    "./..."
  ],
  "gate": [],
  "format": [
    "gofmt",
    "-w",
    "."
  ],
  "install_hint": "内置于 Go 工具链；聚合 lint 可装 golangci-lint"
}
```
