## Context

在飞大重构（refactor-codeguard-architecture，5.5/5.6）已把执行内核/判定/Java/CVE/状态全部模块化到 `scripts/codeguard/`，四个缺口是它范围之外的挂账项：安装面缺件、生态覆盖、跨平台 PATH、死配置。四项互不相交且与在飞文件仅 config.py 一处相邻（摘两行死配置，属该模块的清理型修改）。

## Goals / Non-Goals

**Goals:**

- Claude 宿主安装面闭环（清单 + 版本链 + 回归锁）。
- go 生态进入规范映射，自动选择与显式选择（含别名）同源，阈值语义与既有生态一致。
- PATH 分隔符跨平台正确；死旋钮不留假象。

**Non-Goals:**

- 不做 govulncheck 原生接入（无严重度输出，阈值语义无处安放；trivy 对 gomod 原生解析已满足扫描与严重度过滤）。
- 不动 5.6 归档、死代码清理（在飞重构的地盘）。
- 不实现 `strict_mode` 阻塞语义（与协议 §1 矛盾，永久移除）。

## Decisions

1. **go 的解析器复用 trivy 格式、身份走规范映射**——`_PARSERS["go"] = _trivy` 是格式复用；`_result("go", …)` 保证"结果中报告的标识来自同一份权威映射"（spec 既有要求）。若让 go 报成 universal，命令行 `--ecosystem go` 的输入标识与输出标识就分叉了。
2. **保留 UNKNOWN 进 severity 过滤**（同 scan_trivy 注释）：先滤掉缺严重度发现会让解析器把它们当不存在——假 PASS。测试锁住该语义。
3. **`.claude-plugin/marketplace.json` 同时进 bump 链**——只补清单不补发版链 = 下一版必漂移；`bumpPlain` 对单点 version 字段即覆盖，两行接入。
4. **README 句级删除而非保留标注**——strict_mode 的"保留"状态只制造配置噪音；文档与解析同批消失，测试双向锁死。
5. **paths.py 用 `os.pathsep` 而非双平台分支**——语义就是"PATH 的分隔符"，抽象层早该在。

## Risks / Trade-offs

- [go 报告格式依赖 trivy] → 与 universal 同一依赖面，无新增失败模式；precheck（go.mod/go.sum）保证非 go 项目走不到扫描。
- [.claude-plugin 清单形状无法在本机装 Claude 验证] → 形态逐字段对齐 canvas 仓先例（074a580），版本链由 bump 与测试双锁；宿主现场安装仍属外部验收（同 5.4 的表述纪律）。
- [strict_mode 从配置中消失] → 从无消费点；用户 yaml 里写了它也只被忽略（与现状一致），README 不再误导。

## Migration Plan

1. 规格先行（两份 ADDED delta），归档前 strict 校验。
2. 实现 + `tests/test_gap_closure_20260923.py` 同批；全套（unittest/run_all/check_architecture/ruff/openspec）绿后按仓规 minor bump 0.16.0。
3. PR/CI/不可变 tag/Release 闭环，市场仓在主检出对齐新 main 后同步。
