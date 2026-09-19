# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "cfml",
  "name": "CFML (ColdFusion)",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".cfc",
    ".cfm",
    ".cfs"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "cflint",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . \\( -name '*.cfc' -o -name '*.cfm' \\) -type f -print0 | xargs -0 -r cflint"
  ],
  "format": null,
  "install_hint": "brew install cflint"
}
```
