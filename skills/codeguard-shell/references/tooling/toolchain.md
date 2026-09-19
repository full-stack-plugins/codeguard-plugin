# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "shell",
  "name": "Shell",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".sh",
    ".bash",
    ".zsh"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "shellcheck",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . \\( -name '*.sh' -o -name '*.bash' -o -name '*.zsh' \\) -type f -not -path '*/node_modules/*' -print0 | xargs -0 shellcheck --severity=warning"
  ],
  "format": [
    "shfmt",
    "-w",
    "."
  ],
  "install_hint": "brew install shellcheck shfmt"
}
```
