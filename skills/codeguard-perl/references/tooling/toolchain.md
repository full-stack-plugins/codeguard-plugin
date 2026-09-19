# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "perl",
  "name": "Perl",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".pl",
    ".pm",
    ".t"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "perlcritic",
    "{file}"
  ],
  "gate": [
    "perlcritic",
    "."
  ],
  "format": [
    "perltidy",
    "-b",
    "{file}"
  ],
  "install_hint": "cpanm Perl::Critic Perl::Tidy"
}
```
