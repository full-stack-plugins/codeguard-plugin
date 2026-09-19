# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "dockerfile",
  "name": "Dockerfile",
  "status": "stable",
  "since": "V0.2",
  "extensions": [],
  "file_names": [
    "Dockerfile"
  ],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "hadolint",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . \\( -name 'Dockerfile' -o -name 'Dockerfile.*' -o -name 'Containerfile' \\) -type f -not -path '*/node_modules/*' -print0 | xargs -0 -r hadolint"
  ],
  "format": [
    "hadolint"
  ],
  "install_hint": "brew install hadolint"
}
```
