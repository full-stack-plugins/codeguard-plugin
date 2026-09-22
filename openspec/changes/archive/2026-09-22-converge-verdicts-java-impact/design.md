# 实施设计

## Context

动机见 proposal.md。保留 Python stdlib、现有三端 hook 契约和外部技能所有权，不引入新框架。现有 main 干净，在当前分支实施，不自动创建分支。

## Goals / Non-Goals

- 目标：结论可信、检查对象准确、Java 模块级影响分析可解释。
- 非目标：完整符号级调用图、业务语义自动修复、自动安装 scanner、所有语言沙箱、宿主配置迁移。

## Decisions

1. 增加共享 verdict 模块：状态、原始退出码、原因分离。兼容 passed 字段但只允许 PASS=true；每工具独立处理特殊退出码，未知异常保守 UNVERIFIED。原有 tuples gate API 保留，未验证通过 skipped 通道明确输出。
2. Git 硬门禁在临时目录物化 index/HEAD，并按 staging intent 覆盖将被暂存的路径。用户工作树/index 不写入；不借用真实 .git。无法物化、外部符号链接/子模块或缺少快照运行依赖时明确未验证。软提醒仍可检查工作树。精确快照路径不复用工作树缓存，避免缓存污染。
3. 安全检查使用未排除构建产物的预测路径集合，并排除已删除路径。检查目录名不是秘密内容扫描，文档必须明确边界。
4. 删除无基线的“未修改文件就是历史问题”降级。新增 Java 模块图将反向依赖方纳入计划。代价是部分历史项目会暴露真实存量失败；不能为减少噪声制造通过。
5. Java 使用 POM XML 和保守的 Gradle 声明读取，绝不执行构建脚本来获得图。Maven 解析模块、父坐标、properties 与内部依赖；无法解析/profile/动态结构回退全仓。Gradle 不能确认静态图时根 check。优先 wrapper；Maven 使用 verify，Gradle 使用 check，不默认跳过测试。
6. java-plan 独立 CLI + MCP；门禁和仓库检查复用同一计划。计划包含 changes/affected/modules/dependencies/commands/reasons/gaps，声明模块级而非符号级覆盖。项目级检查在保存时只提醒，不自动跑整仓 formatter。
7. CVE 以 JSON 或工具明确证据归类，网络错误不得当漏洞；不进行真实联网扫描测试。保留旧字段方便消费者迁移。

## Risks / Trade-offs

- 快照不包含 ignored 依赖 → 缺少依赖时 UNVERIFIED，不能退回扫描错误内容。
- 动态构建不能静态完全解析 → 全量保守计划和明确 gaps，而非虚构精确影响面。
- Maven verify/Gradle check 可能执行项目已有插件或联网 → 规划只读，执行延续显式检查/提交门禁授权，文档标明不是沙箱。
- 不同宿主 payload 仍需独立真实端验收；本轮以子进程协议和 stdio MCP 测试为证据。

## Migration Plan

先发布本地可验证的 minor 变更；CLI 未验证退出 1，消费者不得只按非 2 判 PASS。MCP 增加工具和状态字段。文档同步，不移动既有 tag，不直接改受管 skills；远端发布与宿主升级另需确认。
