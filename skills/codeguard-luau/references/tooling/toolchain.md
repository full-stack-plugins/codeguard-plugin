# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "luau",
  "name": "Luau",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".luau"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "luau-analyze",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . -name '*.luau' -type f -print0 | xargs -0 -r luau-analyze"
  ],
  "format": [
    "stylua",
    "--syntax",
    "luau",
    "."
  ],
  "install_hint": "luau-lsp / luau-analyze"
}
```
