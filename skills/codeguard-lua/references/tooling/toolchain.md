# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "lua",
  "name": "Lua",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".lua"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "luacheck",
    "."
  ],
  "gate": [],
  "format": [
    "stylua",
    "."
  ],
  "install_hint": "luarocks install luacheck; cargo install stylua"
}
```
