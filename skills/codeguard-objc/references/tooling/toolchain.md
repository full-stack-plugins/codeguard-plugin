# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "objc",
  "name": "Objective-C",
  "status": "stable",
  "since": "V0.4",
  "extensions": [
    ".m",
    ".mm"
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
    "find . -name '*.m' -o -name '*.mm' | xargs -r clang-tidy --quiet"
  ],
  "format": [
    "clang-format",
    "-i",
    "{file}"
  ],
  "install_hint": "clang-tidy + clang-format"
}
```
