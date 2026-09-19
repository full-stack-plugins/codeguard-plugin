# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "elixir",
  "name": "Elixir",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".ex",
    ".exs"
  ],
  "file_names": [],
  "markers": [
    "mix.exs"
  ],
  "requiresConfig": [
    "mix.exs"
  ],
  "probe": [],
  "lint": [
    "mix",
    "credo",
    "--strict"
  ],
  "gate": [],
  "format": [
    "mix",
    "format"
  ],
  "install_hint": "项目需配置 credo 依赖"
}
```
