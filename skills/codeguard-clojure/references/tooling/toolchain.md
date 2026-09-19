# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "clojure",
  "name": "Clojure",
  "status": "stable",
  "since": "V0.5",
  "extensions": [
    ".clj",
    ".cljs",
    ".cljc",
    ".edn"
  ],
  "file_names": [],
  "markers": [
    "deps.edn",
    "project.clj"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "clj-kondo",
    "--lint",
    "src"
  ],
  "gate": [],
  "format": [
    "cljstyle"
  ],
  "install_hint": "brew install clj-kondo cljstyle"
}
```
