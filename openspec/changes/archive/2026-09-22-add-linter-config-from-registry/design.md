## Context

`env_check.py` 当前的实现：

```python
LINTER_CONFIG_FILES = [
    ("java", [".pre-commit-config.yaml", "checkstyle.xml", "pmd.xml"]),
    ("rust", [".pre-commit-config.yaml", "clippy.toml", ".clippy.toml"]),
    ("typescript", [".pre-commit-config.yaml", "eslint.config.js", ".eslintrc.json", ".eslintrc.js"]),
    ("python", [".pre-commit-config.yaml", "ruff.toml", ".ruff.toml", "pyproject.toml"]),
]
```

下游 `detect_linter_config(project_root)` 走这个硬编码 dict 给 4 种语言加白名单，对其他 50+ stable/beta 语言完全不报告「已配置的 linter」。

更糟的是 `requiresConfig` 已经在 `scripts/languages.json` 里存在，**概念重叠**——`requiresConfig` 是 gate 命令需要的「项目级 linter 配置」标记，用于 gate 命令运行前判定「项目是否真的接入了这个 linter」。`linter_config_files` 是 SessionStart 钩子用来「向 AI 报告：项目里已经存在这些 linter 配置文件」。

为避免混淆，**本 change 不合并 requiresConfig**——只是 env_check 改读 registry 的 `linter_config_files` 新字段。requiresConfig 保持原样。

## Decisions

### languages.json 加字段（向后兼容）

每条语言加 `"linter_config_files": []`（默认空）。**已迁移条目**（java/rust/typescript/python）从现有 `LINTER_CONFIG_FILES` 复制对应数组；**未迁移条目**保持 `[]` 不报错——但 env_check 会跳过。

迁移后 4 个条目：

```json
{
  "id": "java", ..., "linter_config_files": [".pre-commit-config.yaml", "checkstyle.xml", "pmd.xml"]
},
{
  "id": "rust", ..., "linter_config_files": [".pre-commit-config.yaml", "clippy.toml", ".clippy.toml"]
},
{
  "id": "typescript", ..., "linter_config_files": [".pre-commit-config.yaml", "eslint.config.js", ".eslintrc.json", ".eslintrc.js"]
},
{
  "id": "python", ..., "linter_config_files": [".pre-commit-config.yaml", "ruff.toml", ".ruff.toml", "pyproject.toml"]
}
```

### env_check 从 registry 派生

替换 `LINTER_CONFIG_FILES` 常量与 `detect_linter_config` body：

```python
def detect_linter_config(project_root: Path) -> dict:
    """返回 {language: [存在的 linter 配置文件]}，由 languages.json 驱动。"""
    from detect_lang import REGISTRY  # 延迟 import：env_check 是钩子入口，避免循环
    found = {}
    for lang_id, lang_def in REGISTRY.items():
        files = lang_def.get("linter_config_files") or []
        present = [f for f in files if (project_root / f).exists()]
        if present:
            found[lang_id] = present
    return found
```

注意：env_check 已经 `from detect_lang import ...`，但 `REGISTRY` 没在导入名单——加 `REGISTRY` 到 import。

### 校验器新增规则

`scripts/validate_languages_json.py` 加一条规则到 `_check_*` 列表：

```python
def _check_linter_config_files(reg: dict) -> list[str]:
    errs = []
    for lang in reg.get("languages", []):
        if not isinstance(lang, dict):
            continue
        lid = lang.get("id", "<?>")
        cf = lang.get("linter_config_files")
        if cf is None:
            continue
        if not isinstance(cf, list) or not all(isinstance(s, str) for s in cf):
            errs.append(f"{lid}:linter_config_files: must be list of strings")
    return errs
```

`check()` 链追加：`errs += _check_linter_config_files(registry)`。

### 测试新增

`tests/test_validate_languages_json.py` 加 2 条：
- `test_linter_config_files_must_be_list_of_str`
- `test_linter_config_files_can_be_empty`

## Risks / Trade-offs

- **未迁移的 50+ 语言**继续在 SessionStart 钩子中不报告 linter 配置——这是历史行为，本次 change 不引入新副作用**也未修复既有缺陷**。未来哪个 change 主动补各语言 `linter_config_files` 即可。
- **类型契约变更**：languages.json 加了可选字段——下游消费方必须忽略未知字段（`detect_lang` 现状已如此）。