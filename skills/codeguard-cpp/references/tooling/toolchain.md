# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "cpp",
  "name": "C++",
  "status": "stable",
  "since": "V0.4",
  "extensions": [
    ".cpp",
    ".hpp",
    ".cc"
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
    "find . \\( -name '*.cpp' -o -name '*.hpp' -o -name '*.cc' \\) -type f -print0 | xargs -0 -r clang-tidy --quiet"
  ],
  "format": [
    "clang-format",
    "-i",
    "{file}"
  ],
  "install_hint": "clang-tidy + clang-format"
}
```
