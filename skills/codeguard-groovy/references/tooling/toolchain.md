# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "groovy",
  "name": "Groovy",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".groovy"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [
    "build.gradle",
    "build.gradle.kts",
    "pom.xml"
  ],
  "probe": [],
  "lint": [
    "npm-groovy-lint",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . -name '*.groovy' -type f -not -path '*/node_modules/*' -print0 | xargs -0 -r npm-groovy-lint --no-insight"
  ],
  "format": [
    "npm-groovy-lint",
    "--fix"
  ],
  "install_hint": "npm install -g npm-groovy-lint"
}
```
