# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "java",
  "name": "Java",
  "status": "stable",
  "since": "V0.1",
  "extensions": [
    ".java"
  ],
  "file_names": [],
  "markers": [
    "pom.xml",
    "build.gradle"
  ],
  "requiresConfig": [
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle"
  ],
  "probe": [],
  "lint": [
    "mvn",
    "-q",
    "javadoc:jar",
    "-DskipTests"
  ],
  "gate": [],
  "format": [
    "mvn",
    "-q",
    "spotless:apply"
  ],
  "install_hint": null
}
```
