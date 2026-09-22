# Tasks: 2026-09-23-java-gate-default-level

## 1. 默认等级（门禁 ≠ 测试执行）

- [x] 1.1 `java_project.analyze`：Maven argv 追加 `-DskipTests`（测试代码仍编译）
- [x] 1.2 `java_project.analyze`：Gradle argv 追加 `-x test`
- [x] 1.3 `languages.json` java.lint 同步 + `gen_language_docs` 重新生成

## 2. 文档（P2-6 等级语义 / P2-7 ruff 基线）

- [x] 2.1 README：默认等级语义 + `java.commands` 升级完整 verify 路径
- [x] 2.2 README：ruff 版本基线说明（CI 钉扎 ruff==0.16.8）

## 3. 测试与验证

- [x] 3.1 `test_java_project_impact.py` 断言更新（maven/gradle 默认等级）
- [x] 3.2 unittest discover + run_all + ruff + validate_languages_json 全绿
