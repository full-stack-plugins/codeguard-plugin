## MODIFIED Requirements

### Requirement: Languages may declare a configuration prerequisite

注册表 MUST 允许声明配置前置条件，避免采用不适合项目的默认规则。legacy-v1 缺配置时维持未接入/未验证且旧 Hook 放行语义。Rust 新入口 MUST 使用已批准 rulepack 或已接入的项目配置；如果不能可靠满足前置条件，必需义务为 incomplete，不能通过“未接入”自动免除。

#### Scenario: 已声明前置条件且项目未接入
- **WHEN** legacy-v1 项目缺少声明配置
- **THEN** 按旧协议说明未验证并兼容放行，不签发新认证

#### Scenario: Rust required configuration is missing
- **WHEN** 新入口没有项目配置且无法使用批准规则包建立可靠计划
- **THEN** 返回 configuration_required 和未完成，不报代码违规、不满足交付门禁

#### Scenario: 已声明前置条件且项目已接入
- **WHEN** 原生配置存在且满足批准策略
- **THEN** 按有效配置执行，保留配置来源和覆盖证据

#### Scenario: 未声明前置条件的语言不受影响
- **WHEN** 工具契约不要求额外配置
- **THEN** 正常按已批准规则和工具锁执行，不凭空新增项目配置障碍

### Requirement: Gates in git repositories SHALL default to changed-file scope

本条标题描述 legacy-v1：旧门禁 MUST 保留 delta 默认、gate_scope=repo、FULL_SCAN_EXCLUDES、index/预测暂存/HEAD 的历史输入规则与完整诊断；准确快照不复用旧软缓存。Rust 新门禁 MUST 建立全部适用必需义务，增量仅作为等价执行优化，不能默认豁免未修改文件中的问题。新真实 Git 入口 MUST 使用 execution-kernel 的实际 index/ref 契约。

#### Scenario: A committed legacy issue is untouched by a clean change
- **WHEN** legacy-v1 改动仅文档且项目检查确实不适用
- **THEN** 明示无须执行，不伪称完成项目验证

#### Scenario: A new staged file introduces a problem
- **WHEN** index 内容违规但工作树已修好
- **THEN** 检出 index 违规，不借用工作树通过

#### Scenario: A bad commit made outside the gate must not slip through the push
- **WHEN** 实际待推送内容违规但工作树已修好
- **THEN** 检查待推送内容并保留违规

#### Scenario: Push with no resolvable upstream does not crash
- **WHEN** 旧入口没有可解析上游
- **THEN** 保留 HEAD 全树回退，不因空基线跳过

#### Scenario: A chained commit-and-push takes the wider face
- **WHEN** 宿主可可靠建模同仓 commit→push
- **THEN** 覆盖拟提交内容和已有待推送内容；不可建模时明示未完成

#### Scenario: Rust optimization leaves an obligation unproven
- **WHEN** 增量计划没有执行某必需任务且无等价缓存证明
- **THEN** 不能据 delta 干净签发交付 allow

### Requirement: A toolchain crash SHALL be recorded as unverified, not as a lint failure

检查器退出码 MUST 结合工具契约判定，工具故障 MUST 不认作代码违规。legacy-v1 保留 UNVERIFIED、CLI 1、Hook 可见放行。Rust MUST 将该义务标 incomplete、CLI 3，必需检查不满足交付；混合有效发现仍保留。不能统一把所有工具 exit 2 当配置错误，也不能把所有 exit 1 当违规。

#### Scenario: An npx tool crashes with exit 2
- **WHEN** ESLint 因配置问题以 exit 2 退出
- **THEN** 旧接口为 UNVERIFIED；新接口为 incomplete，均不能称为 lint 违规或通过

## ADDED Requirements

### Requirement: Rust command plans SHALL preserve explicit build levels

Rust build MUST 记录编译、静态检查和测试执行的区别。Java 默认静态构建保留不运行测试的等级；批准策略要求测试时 MUST 执行，智能体不得自行追加 skip。自定义命令 MUST 通过义务覆盖核对，不能只凭 exit 0 替代质量证据。

#### Scenario: Policy requires tests
- **WHEN** 项目批准策略要求构建时运行测试
- **THEN** 新计划包含测试执行，运行参数不能静默排除 test

#### Scenario: Default static build completes
- **WHEN** 默认静态构建成功但未运行测试
- **THEN** 报告 test_execution=false，不声称测试通过
