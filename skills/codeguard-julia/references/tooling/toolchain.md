# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "julia",
  "name": "Julia",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".jl"
  ],
  "file_names": [],
  "markers": [
    "Project.toml"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": null,
  "gate": [],
  "format": [
    "julia",
    "-e",
    "using JuliaFormatter; format('.')"
  ],
  "install_hint": "julia -e 'using Pkg; Pkg.add(\"JuliaFormatter\")'"
}
```
