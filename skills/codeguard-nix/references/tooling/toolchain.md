# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "nix",
  "name": "Nix",
  "status": "stable",
  "since": "V0.3",
  "extensions": [
    ".nix"
  ],
  "file_names": [],
  "markers": [
    "flake.nix"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "deadnix",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . -name '*.nix' -type f -print0 | xargs -0 -r deadnix"
  ],
  "format": [
    "nixpkgs-fmt",
    "{file}"
  ],
  "install_hint": "nix-env -iA nixpkgs.nixpkgs-fmt nixpkgs.deadnix"
}
```
