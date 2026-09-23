## 1. Specification

- [x] 1.1 两份 ADDED delta（manifest 版本链 / go 生态规范映射）
- [x] 1.2 `openspec validate --strict` 通过

## 2. Implementation

- [x] 2.1 `.claude-plugin/marketplace.json`（canvas 仓形态）+ `bump-plugin.mjs` 版本链接入
- [x] 2.2 go 生态：`scan_go`（trivy、UNKNOWN 保序）+ `_PARSERS["go"]` 格式复用 + ECOSYSTEM_SCANNERS 条目（别名/语言/标志）
- [x] 2.3 `paths.py` 5 处 `os.pathsep`；`config.py` 摘除 `strict_mode`；README 双语句同步

## 3. Verification

- [x] 3.1 `tests/test_gap_closure_20260923.py`：清单形态/版本链/bump 覆盖锁、go 映射/别名/前置条件/trivy 格式解析 parity、pathsep 源级锁、strict_mode 双向消失锁
- [x] 3.2 全套终验（unittest / run_all / check_architecture / ruff / openspec --all）
