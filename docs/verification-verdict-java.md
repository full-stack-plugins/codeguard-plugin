# 判定可信度与 Java 影响分析：本地验收记录

日期：2026-09-22。目标版本：0.12.0；Codex manifest：0.12.0+codex.20260922。
实施基线：插件 main / `601ff64fa0141b1d092bca4632eb7fa61c074f4c`。本轮没有提交、推送、创建 tag/Release 或更新已安装宿主缓存。

## 验证结果

| 命令 / 证据 | 本地结果 | 能证明什么 |
|---|---|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` | 194 tests，OK，无 skip | 单测、真实临时 Git、wrapper 子进程、官方 SDK stdio MCP 契约 |
| `PYTHONDONTWRITEBYTECODE=1 python3 tests/run_all.py` | 141 通过 / 0 失败 / 0 跳过 | 原生工具抽测及 hook stdin/stdout/exit 协议 |
| `ruff check hooks scripts tests` | All checks passed，ruff 0.16.8 | 执行代码静态检查 |
| `python3 scripts/validate_languages_json.py` | 57 条（54 stable / 3 planned），11 schema rules passed | 注册表合法性，不代表 57 语言运行验收 |
| `python3 scripts/vendor/skill_vendor.py check --offline` | 通过 | 68 个受管技能未被篡改 |
| `python3 scripts/vendor/skill_vendor.py check` | 通过，v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c` | 上游 tag、内容与 lock 对齐 |
| `openspec validate converge-verdicts-java-impact --strict` | 通过 | 增量规格结构一致 |
| `openspec archive converge-verdicts-java-impact --yes --json` | 通过；新增 8 / 修改 9 条 requirements | 已同步主规格并保留归档，9 项 tasks 完成 |
| 对本次六组主规格逐一 `openspec validate <name> --type spec --strict` | 六组全部通过 | 合并后的本次行为契约合法 |
| 市场 `node scripts/sync-marketplaces.mjs --plugin=codeguard` | 通过 | 本地市场与插件 0.12.0 元数据一致，不代表远端 tag 已存在 |
| `node --check scripts/bump-plugin.mjs` / `bash -n bin/codeguard` / `git diff --check` | 通过 | 调度脚本语法和差异检查 |

环境：macOS，Python 3.13.5。未安装/升级宿主 CLI、未初始化 CodeGraph、未变更技能源或 skills.lock.json。CI 配置增加固定版本 ruff，远端 CI 未执行。

归档位置：`openspec/changes/archive/2026-09-22-converge-verdicts-java-impact/`。正式行为规格已合并到 `openspec/specs/`；真实项目与宿主验收仍属于后续工作，不因规格归档而自动通过。

## TDD 与规格追溯

本轮先看到失败，再实现：首批可信度 14 用例中 13 失败；Java 首批 12 用例失败。后续补充删除影响、资源影响、修复范围、CVE 报告、配置前置条件等，均先观察到对应失败，再修复后执行完整回归。

| 行为 | 可重跑测试 |
|---|---|
| 第二文件失败不能被首文件成功覆盖 | `test_second_file_failure_is_not_hidden_by_first_pass`、`test_scoped_check_runs_each_placeholder_file` |
| 工具错误不是 PASS，CLI/MCP 不丢失状态 | `test_tool_config_error_is_not_pass_and_survives_mcp`、`test_missing_tool_cli_is_nonzero_without_all_passed`、`test_cli_honors_linter_configuration_prerequisite` |
| index/HEAD 内容与工作树分离且原状态不变 | `test_staged_bad_worktree_clean_checks_index_and_preserves_both`、`test_push_uses_head_not_unstaged_repair` |
| 预测暂存、安全范围与删除影响 | `test_predicted_add_uses_worktree_and_expands_directory`、`test_safety_sees_predicted_add_and_allows_removal`、`test_deleted_file_is_retained_for_impact_but_not_safety` |
| 修复不扩张范围、不跟随符号链接，复检错误仍未验证 | `test_mcp_auto_fix_never_touches_clean_files`、`test_scoped_fix_does_not_follow_symlink_to_clean_file`、`test_post_tool_recheck_error_is_json_unverified_not_failure` |
| Maven/Gradle 图、反向闭包、wrapper 与保守回退 | `tests/test_java_project_impact.py` 的 15 项用例 |
| MCP 真正暴露并调用 Java 规划 | `test_mcp_boot_lists_four_tools`（真实 stdio JSON-RPC） |
| CVE 错误/阈值/JSON 报告分类 | `tests/test_verdict_integrity.py::CveEvidenceTests` |

## 完整性、正确性与一致性审查

- 对照 verdict-integrity、java-project-impact、language-gate-commands、mcp-tool-server、cve-dependency-scan、hook-protocol 六组增量规格检查了入口与断言。
- CLI/MCP/hook 共用状态语义；hook 仍保持原 fail-open 约定，不能把 exit 0 当成通过。
- 删除“未修改文件报错必为历史债”的豁免；没有编造基线结果。
- 双语 README 结构/链接/版本测试通过；老架构与路线图已标记历史，不再用旧延迟/准确率宣传作为验收。
- 本地市场原为 0.11.0，源码为 0.11.1，已用生成脚本准备 0.12.0；修正本仓落后发版脚本的 ref/logo 同步。没有手改生成清单。
- 所有改动保持在当前分支，未创建/切换分支；外部受管技能不变，因没有技能内容变更，本轮不重新跑 TRACE。

## 剩余边界，不得计为通过

1. 没有执行真实 Maven/Gradle 项目的联网构建。wrapper fixture 只证明参数、路由与进程处理，不证明业务项目构建成功。
2. Java 是模块级静态图；不能完整解释任意 Gradle 程序、effective-POM、外部父 POM 注入依赖、符号调用和数据流。复杂项目需要根检查/权威命令和 CI。
3. 临时快照不是执行沙箱；复杂 shell 链、任意 Git refspec、动态 alias、并发写入仍有盲区。符号链接/子模块/冲突/超限快照明确未验证。
4. hook 未验证项仍放行，这是兼容策略；下一阶段需要单独设计可配置 fail-closed，不能宣传“全部守住”。
5. 没有真实漏洞数据库扫描、准确率/召回率基准、Codex/ZCode/Kimi 当前版本现场加载、GitHub CI、tag 或 Release 证据。
6. 额外执行全库 `openspec validate --specs --strict`：7 通过 / 7 失败。失败均为未触及的历史 Purpose 占位：asset-canonicalization、bilingual-docs-consistency、gate-trigger-policy、idiomatic-runner、languages-registry-contract、plugin-manifest-contracts、registry-driven-config。本次相关六组已通过，未扩张修改这些历史规格；不能宣称全库 strict 已清零。

建议下一次验收选择一个真实 Maven reactor 和一个 Gradle 多模块仓，植入接口破坏/删除、配置故障和不可修复问题，核对影响面、拒绝/放行结论与成本，再推进符号级影响分析。
