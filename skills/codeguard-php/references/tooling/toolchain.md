# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "php",
  "name": "PHP",
  "status": "stable",
  "since": "V0.2",
  "extensions": [
    ".php"
  ],
  "file_names": [],
  "markers": [
    "composer.json"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "php",
    "-l",
    "{file}"
  ],
  "gate": [
    "bash",
    "-c",
    "find . -name '*.php' -type f -not -path '*/vendor/*' -print0 | xargs -0 -n1 php -l"
  ],
  "format": [
    "php-cs-fixer",
    "fix"
  ],
  "install_hint": "composer require --dev php-cs-fixer"
}
```
