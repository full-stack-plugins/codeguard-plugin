## Why

codegraph 深查（2026-09-23）对当前 HEAD 实测出四个长期挂账的小缺口：① `hooks/hooks.json` 引用 `${CLAUDE_PLUGIN_ROOT}` 5 处、Claude 是声明宿主，但仓内**没有** `.claude-plugin/` 清单——Claude 宿主安装面缺件（canvas 仓先例：074a580 补清单）；② CVE 扫描缺 go/gomod 生态（语言注册表有 go，自动选择映射到空，跑不出任何依赖漏洞检查）；③ `scripts/paths.py` 5 处硬编码 `":"`，Windows 上 PATH 拼接/分割必错（4.1 记录在案的未验收面，修兼容是纯正确性）；④ `strict_mode` 死旋钮——`config.py` 只解析零消费（PostToolUse 恒 exit 0 是协议 §1 设计，阻塞语义与之矛盾），README 也自述"保留未接线"，假旋钮误导配置。

## What Changes

- 新增 `.claude-plugin/marketplace.json`（对齐 canvas 仓形态：顶层仓库名 + owner + plugins[0] 条目），并把该清单纳入 `bump-plugin.mjs` 的版本链（否则下次发版必漂移）。
- CVE 新增 **go** 生态：规范映射独立条目（aliases `golang`/`gomod`、languages `go`、markers `go.mod`/`go.sum`），扫描器走 trivy（原生解析 gomod），**报告格式复用 trivy JSON 解析器**、生态身份按规范映射报告——格式是格式，身份是身份；保留 UNKNOWN 进过滤（防假 PASS 同 universal 语义）。
- `paths.py` 全部改为 `os.pathsep`（5 处）。
- 摘除 `strict_mode`：config 解析 + defaults + README 双语句同步删除（保留解析 = 假旋钮）。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `plugin-manifest-contracts`: 新增 Claude 宿主市场清单的存在性与版本链要求。
- `cve-dependency-scan`: 新增 go 生态经规范映射可扫的要求（含别名归一与阈值语义保持）。

## Impact

`scripts/codeguard/{cve,cve_scanners,cve_reports,config}.py`、`scripts/paths.py`、`scripts/bump-plugin.mjs`、`.claude-plugin/marketplace.json`（新）、README 双语、新增 `tests/test_gap_closure_20260923.py`。退出码/JSON schema 不变；`strict_mode` 配置键移除（从无消费点）。5.6 归档与死码清理属在飞 `refactor-codeguard-architecture`，本变更不触碰。
