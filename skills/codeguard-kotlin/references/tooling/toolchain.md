# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "kotlin",
  "name": "Kotlin",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".kt",
    ".kts"
  ],
  "file_names": [],
  "markers": [],
  "requiresConfig": [
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "pom.xml"
  ],
  "probe": [],
  "lint": [
    "./gradlew",
    "detekt"
  ],
  "gate": [],
  "format": [
    "./gradlew",
    "ktlintFormat"
  ],
  "install_hint": "项目需配置 detekt / ktlint 插件"
}
```
