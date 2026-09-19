# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "terraform",
  "name": "Terraform / OpenTofu",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".tf",
    ".tfvars",
    ".tofu"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "tflint"
  ],
  "gate": [],
  "format": [
    "terraform",
    "fmt"
  ],
  "install_hint": "brew install tflint"
}
```
