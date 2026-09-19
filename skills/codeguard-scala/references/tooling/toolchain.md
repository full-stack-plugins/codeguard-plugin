# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "scala",
  "name": "Scala",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".scala",
    ".sc"
  ],
  "file_names": [],
  "markers": [
    "build.sbt"
  ],
  "requiresConfig": [
    ".scalafmt.conf"
  ],
  "probe": [],
  "lint": [
    "scalafmt",
    "--check",
    "."
  ],
  "gate": [],
  "format": [
    "scalafmt"
  ],
  "install_hint": "coursier install scalafmt"
}
```
