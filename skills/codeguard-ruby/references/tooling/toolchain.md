# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "ruby",
  "name": "Ruby",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".rb"
  ],
  "file_names": [],
  "markers": [
    "Gemfile"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "rubocop"
  ],
  "gate": [],
  "format": [
    "rubocop",
    "-A"
  ],
  "install_hint": "gem install rubocop"
}
```
