# Tasks: 2026-09-23-dot-prefix-default-skip

## 1. 单一谓词

- [x] 1.1 `path_policy.is_dot_prefixed(path, root)`：相对 root 判段，`.`/`..` 段豁免；root 外或无法相对化时返回 False（多检查不漏检查）
- [x] 1.2 路径分隔符统一 `/`（沿用 `is_build_artifact` 的 Windows 兼容写法，不用 `lstrip('./')`）

## 2. 检查面四通道接入

- [x] 2.1 `scope.changed_files` 返回前过滤点前缀路径（delta 门禁面 + push 面同时生效）
- [x] 2.2 `scope._inject_find_excludes` 注入 `-not -path '*/.*'`（幂等，OR 组括号前提不变）
- [x] 2.3 `scope.scope_cmd` ruff 分支 full_excludes 时追加 `--exclude '.*'` 与 `--exclude '**/.*'`
- [x] 2.4 `save_application.should_skip` 点前缀文件静默跳过（root 由 `find_project_root` 兜底推导）

## 3. 发现面

- [x] 3.1 `discovery.detect_languages` 的 include 不计入点前缀文件

## 4. 例外面回归锚定（不许被忽略吞掉）

- [x] 4.1 入库安全：`.env`/`*.pem` 照拦；`.agents/`/`.codex-plugin/` 等点目录照常可入库（固化 `0f284ee`）
- [x] 4.2 配置发现：`requiresConfig` 匹配 `.markdownlint-cli2.jsonc` 等点文件仍判已接入

## 5. 提示词面

- [x] 5.1 `startup_application` 项目记忆文本声明默认忽略规则与两个例外
- [x] 5.2 `AGENTS.md` 硬性禁令补该条
- [x] 5.3 `docs/current-architecture.md` 行为段落补一句

## 6. 测试与发版

- [x] 6.1 `tests/test_dot_prefix_default_skip.py` 锚定 1–5 全部场景（含「项目根本身在点目录下不误伤」陷阱）
- [x] 6.2 全量回归（run_all + unittest discover）通过
- [x] 6.3 按仓规 bump minor、市场仓同步、PR/CI 合并、两仓推送
