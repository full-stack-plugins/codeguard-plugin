# Codeguard Rust CLI 语言迁移与验收设计

状态：待执行。语言清单取自 `03ebb24` 的 [scripts/languages.json](../../scripts/languages.json)，共 57 项：54 stable、3 planned。表中工具是旧注册声明或迁移调查入口，**不是已核验的新适配器能力**。不存在的 Rust 实现不计完成；只有 formatter 的旧 stable 也必须补足真实只读检查。

## 1. 每种语言的能力账本

每一 language/module 都生成 `lint/comments/cve/security/build` 五个槽位，分别记录 `implemented / gap / not_applicable`，并附 adapter、规则、工具版本、适用性证据及验收记录。

- `implemented` 只表示具备通过验收的实现；一次运行仍可能 incomplete。
- `gap` 表示有义务但没有可靠能力，交付不能通过。
- `not_applicable` 必须有结构性理由，例如完整依赖发现证明没有第三方组件，或配置文件语言没有独立编译步骤。缺工具、缺规则、扫描失败不能作为理由。
- 外部 ecosystem 扫描可满足多个相关语言的 CVE 义务，但需要可追溯映射。纯 Markdown 的 build 可能不适用，其链接站点构建、文档规则仍按项目声明产生义务。
- 宣传能力矩阵由同一注册数据生成；明确语言/类别/平台覆盖，不能只有“支持 57 种语言”的单一数字。

## 2. 全量迁移清单

波次仅是执行顺序：A 先跑通端到端，B/C 补齐现有 stable，P 保留原 planned 路线图。全量迁移必须完成 A/B/C；P 不强制虚构实现，但如果目标项目要求 P 对应能力，仍不能通过。

| language ID | 旧状态 | 旧 lint 声明/调查入口 | 波次 | 必须验证的差异 |
|---|---|---|---|---|
| java | stable | Maven verify | A | P3C、注释、安全、CVE 各自取证；Maven/Gradle/JDK 矩阵 |
| rust | stable | cargo clippy | A | workspace/features/targets、rustdoc、依赖审计 |
| typescript | stable | ESLint | A | JS/TS 别名、parser、tsconfig、type-aware 上下文 |
| python | stable | Ruff | A | 目标 Python、docstring 规则、依赖图 |
| go | stable | go vet | B | 多模块、build tags、依赖与文档规则 |
| csharp | stable | dotnet format --verify-no-changes | B | analyzer、solution、目标 framework、XML 文档 |
| kotlin | stable | Gradle detekt | B | Kotlin/JVM 版本、Gradle 项目与 KDoc |
| swift | stable | SwiftLint | B | Swift/Xcode 工具链、平台与文档规则 |
| php | stable | php -l | B | 语法检查不能代表完整编码规范；配置与 PHPDoc |
| ruby | stable | RuboCop | B | Ruby 版本、cop 配置、依赖与注释 |
| scala | stable | scalafmt --check | B | 格式之外的诊断义务及 Scaladoc |
| shell | stable | ShellCheck | A | sh/bash/zsh 方言分别建模；不得静默抛弃 zsh |
| dockerfile | stable | Hadolint | A | Dockerfile 变体、配置安全与镜像依赖范围 |
| yaml | stable | yamllint | B | 原生配置与 YAML 方言、模板文件 |
| elixir | stable | Credo | B | Mix project、依赖、模块文档 |
| css | stable | Stylelint | B | CSS 方言及插件，不能将任意预处理器当 CSS |
| c | stable | clang-tidy | B | compile_commands、目标平台、头文件上下文 |
| cpp | stable | clang-tidy | B | 编译数据库、模板、标准版本、头文件 |
| objc | stable | clang-tidy | B | Objective-C/Objective-C++ 与 SDK |
| dart | stable | dart analyze | B | SDK、analysis_options、pub 依赖 |
| vue | stable | ESLint | B | SFC parser、template/script/style 覆盖 |
| svelte | stable | ESLint | B | Svelte parser/plugin 与编译上下文 |
| astro | stable | ESLint | B | Astro parser/plugin、模板与内嵌语言 |
| solidity | stable | Solhint | B | pragma/compiler、静态安全和依赖 |
| terraform | stable | TFLint | B | provider/module 版本、IaC 安全与锁 |
| nix | stable | deadnix | B | dead-code 不代表完整安全；Nix 表达式和锁 |
| html | stable | HTMLHint | B | 模板方言显式适用，不能正则过滤后假装全覆盖 |
| sql | stable | SQLFluff | B | dialect、templater、项目配置 |
| graphql | stable | ESLint | B | schema/operation/plugin，上下文关联 |
| protobuf | stable | buf lint | B | module/workspace 与依赖 |
| markdown | stable | markdownlint-cli2 | B | 项目规则、代码块、MDX 等方言 |
| toml | stable | Taplo | B | TOML/schema 规则与项目归属 |
| haskell | stable | HLint | C | GHC extensions、项目依赖、文档规则 |
| ocaml | stable | ocamlformat --check | C | 原命令可执行性、Dune/opam、格式之外义务 |
| fsharp | stable | dotnet fantomas --check | C | F# 项目/工具锁与编译诊断 |
| perl | stable | Perl::Critic | C | Perl 版本、profile、POD |
| groovy | stable | npm-groovy-lint | C | Groovy/Gradle 方言与只读执行模式 |
| clojure | stable | clj-kondo | C | namespace/classpath、配置与文档元数据 |
| powershell | stable | PSScriptAnalyzer | C | PowerShell 版本、对象报告与 comment help |
| zig | stable | zig fmt --check | C | 格式与编译义务分离、Zig 版本 |
| nim | stable | nim check | C | 命令真实输入、项目入口与依赖 |
| crystal | stable | Ameba | C | Crystal 版本、shards、文档规则 |
| julia | stable | lint 为空；旧表有 format 能力 | C | 找到并验证只读检查器，不以 formatter 宣称 lint 完成 |
| elm | stable | elm-review | C | review 项目配置、依赖与锁定规则 |
| lua | stable | Luacheck | C | Lua 版本/globals、文档约定 |
| luau | stable | luau-analyze | C | Luau 类型环境，不能复用 Lua 语义 |
| pascal | stable | lint 为空；旧表有 format 能力 | C | 编译器/方言与只读检查能力补齐 |
| r | stable | lintr | C | R 版本、包项目、对象报告与文档 |
| cfml | stable | CFLint | C | CFML 引擎、模板和报告版本 |
| cobol | planned | 无 | P | 显式 capability gap，保留迁移记录 |
| vbnet | stable | dotnet format --verify-no-changes | C | VB analyzer、solution、XML 注释 |
| erlang | stable | Elvis | C | OTP/rebar、规则与文档 |
| arkts | planned | 无 | P | SDK/编译器可用性未知，不能标成功 |
| metal | planned | 无 | P | Apple SDK 能力未知，不能标成功 |
| liquid | stable | theme-check | C | 主题结构、Liquid/HTML 边界 |
| cuda | stable | clang-tidy | C | CUDA toolkit、host/device、编译数据库 |
| ansible | stable | ansible-lint | C | collections、playbook、依赖及安全规则 |

旧表只有 lint 声明并不代表其它类别不需要做；每行必须附完整五槽位记录后才可以验收。`java`/`kotlin`/`scala` 等可共享 Maven/Gradle 依赖图，不能重复扫描造成重复 CVE，也不能漏掉另一构建根。

## 3. 必备场景库

每个新 stable adapter 至少含以下 fixture 类型；工具模拟只测执行边界，最终必须用真实二进制完成正反例。

| 编号 | 场景 | 验收 |
|---|---|---|
| F01 | 正确源码，正确配置与版本 | 完整、零阻断违规；实际目标非空 |
| F02 | 一条确定违规与对应最小修复 | 检出规则和正确位置；复检不再有该 finding |
| F03 | 缺命令/运行时、版本不兼容、坏配置 | incomplete，违规数不因工具故障虚增 |
| F04 | 原生非零但没有有效报告 | incomplete，不靠通用 rc 推断违规 |
| F05 | 有效违规后超时/崩溃/输出截断 | 保留 finding，同时 incomplete |
| F06 | exit 0 但空/畸形/陈旧/矛盾报告 | incomplete，不能假 PASS |
| F07 | 模块/方言/生成代码/配置继承 | 按批准规则准确覆盖；不能自行扩大或缩小 |
| F08 | 字符编码、特殊路径、空格、换行、非 UTF-8 | 身份可逆；无注入、无静默丢目标 |
| F09 | 内容或原生配置同大小同 mtime 替换 | 缓存失效；检查绑定实际输入 |
| F10 | 规则/工具/漏洞库更换 | 重新计算，不复用旧通过 |
| F11 | 50/51 文件、顺序变化、并发度变化 | findings 和 gate 等价；只有耗时变化 |
| F12 | 历史问题在未修改文件 | existing 分类，仍按相同规则阻断 |
| F13 | Agent 尝试 skipGate/env/suppression/提高阈值 | 不能获得新交付 allow，留下策略差异 |
| F14 | formatter 成功但无变化/失败后部分变化 | 分开执行成功、内容变化与已修复 |
| F15 | 原始诊断含凭据，日志目录/文件 symlink | 公共报告脱敏，目标不被意外覆盖 |
| F16 | index 与工作树不同、多 ref/non-HEAD push | 检查真实内容；不改 index |
| F17 | 所有发现为零但有一个必需类别缺能力 | exit 3，不能签发交付通过 |
| F18 | 点前缀源码/配置/.env | 普通面不扫描不逐文件报告；配置发现及入库安全例外保留 |
| F19 | Java verify 没绑定 P3C/Javadoc | 不得据 verify 成功声称全部质量义务完成 |
| F20 | 库过期/离线、模糊包匹配、未知严重度 | CVE 不伪造安全通过，也不伪称确定高危 |
| F21 | stdout/stderr 洪流、fork 子孙进程、取消 | 有界结束、清理、部分证据、无孤儿进程 |
| F22 | 同一请求 CLI/MCP/Hook/CI 输出转换 | 语义一致，协议退出码按各自表映射 |
| F23 | 多工具重复发现或同规则多次出现 | 归并可追溯，次数不丢失，不跨文件抵扣 |
| F24 | 项目脚本禁用 analyzer 或自定义命令仅 echo | 覆盖不足，不能被命令 exit 0 欺骗 |

## 4. 误报与漏报的评测方法

采用两层语料：确定性合成正反例用于边界与回归；脱敏的真实项目样本用于规则适用性、方言、依赖与报告准确性。样本按语言、类别、工具版本和项目规模分层，保留独立 holdout，不能只挑工具最容易通过的项目。

每条裁定记录由人工或经过确认的 oracle 给出：应有 finding、规则依据、位置/依赖定位、应有执行状态、覆盖义务。争议样本单独统计，不靠模型投票充当真值。样本来源、版本、内容摘要、工具锁、裁定理由随报告归档。

| 指标 | 定义 | 防止指标失真 |
|---|---|---|
| Precision | TP / (TP + FP) | 附 finding 样本量；无发现时记不可估计，不能报 100% |
| False discovery rate | FP / (TP + FP) | 不与传统 FPR 混称 |
| Recall | TP / (TP + FN) | 使用已知真问题语料，保留漏报原因 |
| 工具故障误判率 | 被错误标成代码违规的故障样本 / 全部故障样本 | 单列，不与代码 FP 混在一起 |
| 完整率 | 完成且覆盖匹配的必需义务 / 全部适用必需义务 | 删除义务、增加排除会进入差异审计 |
| 假通过数 | incomplete、坏证据或已知阻断违规却 allow 的样本数 | 必须为零；未知不能算通过 |
| 稳定性 | 相同输入/工具/规则/库身份重跑结果一致比例 | 按规则定位不稳定来源 |
| 性能 | 同环境冷/热启动、p50/p95、峰值内存、缓存命中 | 对比覆盖/规则/工具完全一致 |

建议发布门槛（目标，不是已达成指标）：确定性必备场景零假通过、零工具故障误判；新增 adapter 必须检出其全部预置真问题；关键安全/CVE 回归零漏报；每个有足够裁定样本的 adapter/category 的 precision 95% Wilson 下界至少 0.98。没有足够样本的能力不得借全局平均值升级为充分验证；预览版本标明证据不足。

统计门槛调整属于人工可审查的验收标准变化，智能体不得为了完成任务调低。每个分层至少列出 n、TP、FP、FN、区间、规则数和项目数；CI 跑固定离线集，周期性真实工具/漏洞库运行单独跟踪，避免网络波动污染确定性回归。

性能先建立基线，再由维护者冻结绝对预算；本次不编造毫秒级承诺。验收首先要求优化前后发现集合、完整性、覆盖身份等价，才比较启动、扫描和缓存性能。

## 5. 发布与迁移验收矩阵

| 层次 | 证据 | 不可替代它的证据 |
|---|---|---|
| Rust 源码 | fmt/clippy/test、依赖方向、schema/fixture 测试 | 文件存在或编译成功 |
| 工具适配 | 固定工具链真实正反例、故障与修复复检 | mock 输出解析通过 |
| 全语言覆盖 | 54 stable 五槽位验收 + 3 planned 明示 | Java/Python/Rust/TS 演示 |
| Git/CI | 实际 index、多 ref push、受保护策略测试 | Shell 字符串静态识别 |
| 制品 | target triple、摘要/签名、安装及离线 doctor | Release 页面存在 |
| 插件接入 | Codex/ZCode/Kimi 每种事件真实调用新二进制 | manifest 语法正确 |
| 市场与安装 | source/lock/vendor/market/installed version/digest 对齐 | 本地单元测试通过 |
| 产品结果 | 固定语料 precision/recall/完整率与历史差异裁定 | “误报已经很低”的主观描述 |

验收记录建议包含 `requirement_id / task_id / fixture_or_project / tool_lock / source_digest / expected / actual / artifact_refs / reviewer / date`。任务只有对应证据可定位且通过时才勾选。

## 6. 规范到任务追踪

| 规格能力 | 任务阶段 | 主要场景 |
|---|---|---|
| unified-cli-contract | S01、S02、S11 | F17、F22、CLI 错参/空输入 |
| native-tool-adapters | S05、S06、S07、S08 | F01–F08、F19、F20、F23、F24 |
| rulepack-governance | S04、S05、S12 | F07、F10、F12、F13、F18 |
| verdict-integrity | S02、S12 | F03–F06、F12、F17 |
| execution-kernel | S03、S10、S12 | F08–F11、F14–F16、F21 |
| language-gate-commands | S05–S08、S12 | F03、F07、F11、F19 |
| hook-protocol | S11、S12 | F13、F16、F22 |
| binary-distribution | S11、S13 | 摘要不匹配、无网络、版本回滚、三宿主实机 |
| remediation-workflow | S09、S10、S11、S12 | 重复发现归并、跨类别同步、attempt 预算、复检关闭/重开、租约冲突 |
| scan-scope-policy | S04、S09、S12 | 自有产物不递归扫描、用户源码仍检查、入库安全不豁免 |

## 7. 完成边界

当前仅完成设计文件；上述表格无一构成适配器已实现证明。实施顺序与核对框统一位于 [OpenSpec tasks](../../openspec/changes/introduce-rust-codeguard-cli/tasks.md)。旧实现对照仅用于解释差异，不作为新系统必须复制错误的依据。
