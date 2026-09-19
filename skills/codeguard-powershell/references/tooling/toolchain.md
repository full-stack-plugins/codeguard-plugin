# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "powershell",
  "name": "PowerShell",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".ps1",
    ".psm1"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "pwsh",
    "-NoProfile",
    "-Command",
    "Invoke-ScriptAnalyzer -Path . -Severity Error"
  ],
  "gate": [],
  "format": [
    "pwsh",
    "-NoProfile",
    "-Command",
    "Invoke-Formatter"
  ],
  "install_hint": "Install-Module PSScriptAnalyzer"
}
```
