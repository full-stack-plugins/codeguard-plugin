# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "solidity",
  "name": "Solidity",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".sol"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "solhint",
    "**/*.sol"
  ],
  "gate": [],
  "format": [
    "prettier",
    "--plugin=prettier-plugin-solidity",
    "--write"
  ],
  "install_hint": "npm install -g solhint prettier prettier-plugin-solidity"
}
```
