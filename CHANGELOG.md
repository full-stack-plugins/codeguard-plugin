# Changelog

按版本段落提炼的主题摘要（生成于 2026-09-23，来源：git 历史 212 个提交与各 release 提交）。逐提交细节以 `git log` 与 GitHub Releases 为准；本文件按主题归纳，不逐条罗列。

## v0.16.1 — 测试可移植性收口与汇流

- 测试可移植性与迁移债三批收口（P0 skipIf 守卫、requirements-dev、CI 矩阵 3.11/3.12/3.13；P1 shim 弃用通告、SCRIPT_ROLES 角色登记、双轨分工说明；P2 bump 歧义报错、init exit 0、README 计数锁定），615/615 单测与 run_all 144/144 全过。
- bump-plugin 写后回读支持 `.claude-plugin` 嵌套版本路径（`plugins[0].version`）。
- 汇流收口：test-portability 批次与起草中的统一 Rust CLI 变更骨架一并入 main。
- skipGate 豁免范围收窄：代理可控豁免（仓库配置/内联 `-c`/链式）只覆盖语言门禁，
  入库内容安全扫描（密钥/凭据类）恒执行；唯一完整逃生门为进程环境变量
  `CODEGUARD_SKIP_GATE`（1/true/yes，仅用户可设）。软硬门禁与四份文档同批同步。
- 工具链 PATH 根因修复：符号链接解释器机器上 `ensure_user_path` 补 resolve 目录与
  sysconfig scripts 目录；探活 not_found 时以 `python3 -m <tool>` 试判「未安装」vs
  「入口缺失」；run_gate 入口先补 PATH 再采集缓存身份（check_identity 计入 PATH，
  事后改写会使 ck≠after、软缓存永不落盘）。

## v0.16.0 — Claude 安装面与 Go CVE 生态

- Claude 安装面补件（新增 `.claude-plugin/marketplace.json`）；CVE 新增 go 生态；
  pathsep 修复；`strict_mode` 摘除。

## v0.15.x — Git 归因收敛与诊断安全

- **v0.15.4** 测试卫生与可见性：`tests/run_all.py`（809 行）拆分为
  `_harness.py`（共享夹具）+ `_subsets.py`（8 个回归子集），入口签名与
  逐字节输出保持不变（golden diff 验证）；CI 单测改由 coverage 包装并
  追加 advisory 覆盖率报告（非门禁）。
- **v0.15.3** heredoc 正文按归属语义归因（数据段 git 样例误报清零）。
- **v0.15.2** 发版链 fail-loud（bump 漂移即抛错）；非 Shell 间接 git 归因收紧；`hook-protocol` 归因 delta 并入主规格。
- **v0.15.1** 诊断日志改为私有原子落盘；准确 Git 快照的 index 与 HEAD 身份复核。
- **v0.15.0** 点前缀目录与文件默认忽略（代码 + 提示词双层硬约束）。

## v0.14.x — Git 操作判定与 MCP 诊断（15 个补丁系列）

- 显式 / 多仓 / 间接 / 带前缀 Git 操作的仓库与暂存判定逐步收敛（0.14.3–0.14.6）。
- 逐命令执行证据与 MCP 脱敏（0.14.7）；诊断日志与 CLI 判定收敛（0.14.8）。
- 门禁故障隔离与 MCP 诊断收敛（0.14.9）；Git 提交链暂存时间归属（0.14.10）。
- Git 快照批量对象身份与内容哈希校验（0.14.11）；MCP 自动修复文件身份边界（0.14.12）。
- MCP 逐项修复可信度判定收敛（0.14.13）；外部检查进程有界输出护栏（0.14.14）。
- Git 快照资源边界与覆盖层一致性（0.14.15）；提交安全检查默认忽略点前缀目录。

## v0.13.x — 执行内核收敛

- **v0.13.0** 执行内核（execution kernel）重构：五类 Hook 应用层收敛统一判定内核。

## v0.12.x — 会话实测优化与 Java 影响分析

- 规则聚合计数、`java_project` executable 键、scope 边界加固（会话实测批）。
- 默认检查等级不含测试执行（`-DskipTests` / `-x test`）；ruff 版本基线钉扎。
- 工具链不兼容归 UNVERIFIED 而非误红；JDK 兼容版本解析；mvnw 感知接入门禁。
- 版本横幅不再前置——stderr 首行必须是门禁综述（契约测试锁定）。

## v0.8–v0.11 — 门禁硬化与构建产物认知

- v0.8.x：门禁硬化 14 项实弹审计修复；推送面补齐；判定归一化 + 安全检查范围收窄；守卫绕过闭环。
- v0.10.x：门禁全量扫描剔除构建产物（`find` 型 gate 注入 `-not -path`）；GNU `xargs` 空输入误红修复。
- v0.11.x：构建产物认知补全——单一事实源 + 四通道生效；manifest 收敛。
- v0.12.0：判定可信度收敛 + Java 项目影响分析（mvn/gradle 变更面）。

## v0.7.x — MCP 接入与双语门禁

- **v0.7.0** 门禁触发词词边界匹配（`pushed`/`deployment` 不误触发）+ 定向语言子集 + MCP 官方 SDK 三工具 + 失败日志落盘。
- **v0.7.1** `pre_tool` import 规范化与版本行对齐收编。

## v0.6.x — 注册表契约与结构门禁

- **v0.6.1** `detect_lang` 三职责拆分（`paths.py` / `user_config.py`），hooks↔scripts 跨社区边清零；manifest bundle 测试动态化。
- **v0.6.2** `run_per_language` 共享 per-language 编排（`run_check` / `fix` 去重）。
- **v0.6.3** `hooks/__protocol__.md` 宿主契约 cheat-sheet（exit 码 / JSON / fail-open 单源化）。
- **v0.6.4** `languages.json` 11 条 schema 校验器（自捕 `ansible` 误标 planned 的真实 bug）。
- **v0.6.5** env_check 的 linter 配置盘点改由注册表驱动。
- **v0.6.6** 零引用营销资产清理 + `assets/README.md`。
- **v0.6.7** 双语 README 结构对齐门禁（标题层级/链接/版本串三断言）+ 技术方案文档改名去全角逗号。
- **v0.6.8** `linter_config_files` 推全局（4 → 39/54 stable-beta）+ 覆盖守护测试。

## v0.5.x 及更早 — 三宿主插件成型

- v0.5.x：ZCode / Codex / Kimi 三端 manifest 收敛、发版与市场仓同步链成型。
- v0.3–v0.4：早期技能 vendor 与分发安全边界（`safe-skill-distribution`）。
- v0.1.x：初版三端插件。
