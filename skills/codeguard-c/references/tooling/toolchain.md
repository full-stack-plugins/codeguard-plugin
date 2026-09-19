# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "c",
  "name": "C",
  "status": "stable",
  "since": "V0.4",
  "extensions": [
    ".c",
    ".h"
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
    "find . -name '*.c' -o -name '*.h' | xargs -r clang-tidy --quiet"
  ],
  "format": [
    "clang-format",
    "-i",
    "{file}"
  ],
  "install_hint": "clang-tidy + clang-format"
}
```
