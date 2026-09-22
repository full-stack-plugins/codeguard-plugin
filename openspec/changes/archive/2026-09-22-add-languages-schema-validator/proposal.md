## Why

`scripts/languages.json` 是 codeguard 的语言注册表（57 条），由 `detect_lang.py`、`hooks/__protocol__.md` 指向的 `gen_language_docs.py`、`tests/run_all.py::test_languages` 三处下游同时消费。MEDIUM #5 评审指出：每条语言字段是手工维护的（id / name / extensions / markers / status / since / lint / format / install_hint / requiresConfig），任一字段漏写、状态值非法、id 重复、extensions 互相冲突，错误信号极弱——`tests/run_all.py::test_languages` 仅断言「stable/beta ≥50」，捕获不到字段完整性或一致性。需要一个集中校验脚本，作为 PR-time 的硬门禁。

## What Changes

- 新增 `scripts/validate_languages_json.py`：纯函数校验器，零网络、零依赖；接受 `--path`（默认 `scripts/languages.json`）；退出码 0=通过 / 1=失败 / 2=参数错误；输出逐行 `level: id.field: message` 文本格式。
- 新增 `tests/test_validate_languages_json.py`：unittest，覆盖正例（当前 json）与反例（id 重复、status 非法、extensions 冲突、required 字段缺失、requiresConfig 指向不存在的注册项）。
- CI（`skills-check.yml`）增加一行 `python3 scripts/validate_languages_json.py` 与 `python3 -m unittest tests.test_validate_languages_json` 的执行（如同现有 `run_all.py`）。
- 不修改 `languages.json` 内容；不修改下游消费方（detect_lang / gen_language_docs / run_all.py）。

## Capabilities

### New Capabilities

- `languages-registry-contract`: Defines the schema and consistency rules for `scripts/languages.json`.

### Modified Capabilities

None.

## Impact

新增 1 个校验脚本（~80 行）+ 1 个测试文件（~80 行）；CI 工作流加 2 行。总行数净增 < 200。