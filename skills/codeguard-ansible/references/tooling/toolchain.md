# 工具链快照

该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。

```json
{
  "id": "ansible",
  "name": "Ansible",
  "status": "planned",
  "since": "V0.3",
  "extensions": [],
  "file_names": [],
  "markers": [
    "ansible.cfg",
    "playbook.yml"
  ],
  "requiresConfig": [],
  "probe": [],
  "lint": [
    "ansible-lint"
  ],
  "gate": [],
  "format": [
    "ansible-lint",
    "--fix"
  ],
  "install_hint": "playbook 检查由 ansible-lint 承接（yaml 通道）；语义级检查待集成"
}
```
