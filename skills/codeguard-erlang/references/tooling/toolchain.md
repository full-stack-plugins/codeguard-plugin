# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "erlang",
  "name": "Erlang",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".erl",
    ".hrl"
  ],
  "file_names": [],
  "markers": [
    "rebar.config"
  ],
  "requiresConfig": [
    "elvis.config",
    "elvis.config.js"
  ],
  "probe": [],
  "lint": [
    "elvis",
    "rock"
  ],
  "gate": [],
  "format": [
    "erlfmt"
  ],
  "install_hint": "rebar3 plugins / escript"
}
```
