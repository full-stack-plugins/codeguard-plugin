# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "python",
  "name": "Python",
  "status": "stable",
  "since": "V0.1",
  "extensions": [
    ".py"
  ],
  "file_names": [],
  "markers": [
    "pyproject.toml",
    "setup.py",
    "requirements.txt"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "ruff",
    "check",
    "."
  ],
  "gate": [],
  "format": [
    "ruff",
    "check",
    ".",
    "--fix"
  ],
  "install_hint": "pip install ruff"
}
```
