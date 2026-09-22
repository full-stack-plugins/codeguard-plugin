# Tasks: 2026-09-22-gate-full-scan-excludes

## 1. 扫描剔除泛化

- [x] 1.1 `scope.py`：`_RUFF_FULL_EXCLUDES` 重命名为公开 `FULL_SCAN_EXCLUDES`
- [x] 1.2 `scope.py`：新增 `_inject_find_excludes`（`find -print0` 注入 `-not -path`，幂等）
- [x] 1.3 `scope_cmd`：`full_excludes=True` 时对字符串元素应用 find 注入（ruff 分支不变）
- [x] 1.4 `gate_lib`：delta 回退全量路径补 `full_excludes=not uses_delta_files`

## 2. 可诊断性与可回溯性

- [x] 2.1 `gate_lib`：`_dependency_resolution_hint`——java 依赖解析失败给行动指引
- [x] 2.2 `gate_lib`：`record_skip_event` 增加最近 20 条明细（ts/kind/repo），总数兼容
- [x] 2.3 两个 hook 调用点传入 `project_root`

## 3. 注册表契约

- [x] 3.1 `validate_languages_json`：shellcheck gate/lint 必须钉扎 `--severity=`

## 4. 测试与文档

- [x] 4.1 `tests/test_full_scan_excludes.py`：14 用例（注入/幂等/端到端 javadoc.sh/审计/提示/契约）
- [x] 4.2 README（zh+en）：全量门禁自动剔除构建产物目录说明
- [x] 4.3 `run_all.py` 全量 141 通过；ruff 全绿；版本 bump
