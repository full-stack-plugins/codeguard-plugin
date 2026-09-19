# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "r",
  "name": "R",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".r"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "Rscript",
    "-e",
    "lintr::lint_dir('.')"
  ],
  "gate": [],
  "format": [
    "styler",
    "::",
    "style_dir"
  ],
  "install_hint": "Rscript -e 'install.packages(c(\"lintr\",\"styler\"))'"
}
```
