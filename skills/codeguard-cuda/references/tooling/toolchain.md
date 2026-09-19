# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "cuda",
  "name": "CUDA",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".cu",
    ".cuh"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "clang-tidy",
    "--quiet",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . -name '*.cu' | xargs -r clang-tidy --quiet"
  ],
  "format": [
    "clang-format",
    "-i",
    "{file}"
  ],
  "install_hint": "CUDA Toolkit + clangd"
}
```
