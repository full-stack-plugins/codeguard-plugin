# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "ocaml",
  "name": "OCaml",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".ml",
    ".mli"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "ocamlformat",
    "--check",
    "."
  ],
  "gate": [],
  "format": [
    "ocamlformat",
    "-i",
    "."
  ],
  "install_hint": "opam install ocamlformat"
}
```
