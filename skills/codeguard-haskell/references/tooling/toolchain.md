# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "haskell",
  "name": "Haskell",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".hs",
    ".lhs"
  ],
  "file_names": [],
  "markers": [
    "stack.yaml",
    "cabal.project"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "hlint",
    "."
  ],
  "gate": [],
  "format": [
    "fourmolu",
    "-i",
    "."
  ],
  "install_hint": "brew install hlint fourmolu"
}
```
