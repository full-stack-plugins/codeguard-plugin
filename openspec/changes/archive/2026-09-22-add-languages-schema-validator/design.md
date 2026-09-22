## Context

现状（v0.6.3）：
- `scripts/languages.json` 顶层结构 `{version, description, status_levels, languages[]}`；status_levels 三档 stable/beta/planned。
- 单条语言字段：id, name, extensions, markers, status, since, lint, format, install_hint, requiresConfig（部分可选）。
- 下游消费：
  - `scripts/detect_lang.py::_load_registry` + `EXT_LANG_MAP` / `FILE_LANG_MAP` / `PROJECT_MARKERS` / `LANG_COMMANDS` 构建（line 60-122）。
  - `scripts/gen_language_docs.py` → `docs/LANGUAGES.md`。
  - `tests/run_all.py::test_languages` 子集断言 stable/beta ≥50 + by_id/get(key) smoke。
- 已存在错误模式：
  - `tests/test_distribution_safety.py::test_no_rickroll_surface_is_published` 间接证明 languages.json 漏字段会让安全测试挂。
  - 当前 57 个语言全为 stable 或 planned（无 beta），但 status_levels 列出 beta 是历史遗物。

## Decisions

### 校验器独立 CLI（不嵌入 detect_lang）

校验逻辑不放在 `detect_lang.py`——会污染运行时加载路径。独立脚本 `scripts/validate_languages_json.py`，被 CI 直接调、被单元测试直接调。

### 校验规则集（11 条）

每条失败都打印 `ERROR: <id-or-'all'>.<field-or-path>: <message>`，并在脚本末尾汇总「N errors」：

1. **顶层结构**：`version` 存在且为正整数；`languages` 数组非空；`status_levels` 至少包含 stable/beta/planned。
2. **id 唯一性**：所有 languages[i].id 两两不同。
3. **status 合法**：status ∈ status_levels。
4. **extensions 唯一性**：跨语言 extensions 不互相覆盖（`.py` 只能被一个 stable/beta 占用）。
5. **markers 唯一性**：跨语言 markers 不互相覆盖。
6. **lint / format 一致性**：若 status ∈ {stable, beta}，lint 或 format 至少有一个非空；planned 允许全空。
7. **requiresConfig 字段类型**：list of str；glob 模式允许（`*`, `?`, `[`）。
8. **id 命名约定**：kebab-case（小写 + `-`）。
9. **since 字段**：存在；与 status_levels 对应——stable/beta 应有 since，planned 允许为空（但当前均为 V0.1 +）。
11. **extensions 必须以 `.` 开头**。
12. **lint/ format 命令非空列表**：每元素为非空字符串。

### 输出格式

```
INFO: languages.json contains 57 entries (53 stable, 0 beta, 4 planned)
INFO: 53 stable/beta languages (>= 50 ✓)
INFO: 11 schema rules passed
ERROR: all:extensions: marker ' pom.xml' duplicated across java/kotlin/scala (current stable/beta owners differ)
... (N errors)
```

退出码：errors=0 → 0；errors>0 → 1；--help/参数错误 → 2。

### 测试矩阵（unittest）

- `test_clean_registry_passes`：当前 `scripts/languages.json` 通过校验（baseline）。
- `test_duplicate_id_fails`：复制某条 id → 期望 1 条 ERROR。
- `test_invalid_status_fails`：status="draft" → 期望 1 条 ERROR。
- `test_extension_collision_fails`：手造一个 stable/beta 语言 `extensions=["rs"]`（撞 rust）→ 期望 1 条 ERROR。
- `test_marker_collision_fails`：类似。
- `test_planned_with_lint_fails`：status="planned" + lint 非空 → 期望 1 条 ERROR。
- `test_stable_with_no_lint_or_format_fails`：status="stable" 且 lint/format 都为 null/[] → 期望 1 条 ERROR。
- `test_requiresConfig_must_be_list_of_str`：类型错误 → 期望 1 条 ERROR。
- `test_extensions_must_start_with_dot`：".py" 改成 "py" → 期望 1 条 ERROR。
- `test_id_must_be_kebab_case`：id="Ruby_on_Rails" → 期望 1 条 ERROR。

### CI 入口

`skills-check.yml` 增加：
```yaml
- name: languages.json schema check
  run: python3 scripts/validate_languages_json.py
- name: languages.json schema unit tests
  run: python3 -m unittest tests.test_validate_languages_json -v
```

与现有 `python3 -m unittest discover -s tests -p 'test_*.py' -v` 不重复（仍跑总发现测试）。

## Risks / Trade-offs

- **校验器本身需要测试覆盖**——`tests/test_validate_languages_json.py` 是必须项；CI 单独跑一条确保它没有自我指涉。
- **当前注册表可能有隐藏违规**——test_clean_registry_passes 是真实基线；如果发现历史遗留违规，需在 change 里同步修正并标注原因。
- **extensions/markers 冲突判定的语义**：`planned` 语言的扩展名不参与冲突检测（仅 stable/beta 是「已部署」）——避免给未来新增留过严约束。