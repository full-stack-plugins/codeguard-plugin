## Purpose

定义 `docs/LANGUAGES.md` 与注册表之间的可复现关系：文档的全部内容都应由注册表与生成器产生，重跑生成器在注册表未变更时不得产生差异，且任一方向的不一致都必须可被检出，而不是静默存在。

## ADDED Requirements

### Requirement: Documentation must be fully reproducible from the registry

`docs/LANGUAGES.md` SHALL 能由注册表与生成器完全复现。生成器 SHALL 覆盖文档的全部内容；若存在有意手工维护的区段，该区段 SHALL 在文档中明确标注，且 SHALL 由生成器原样保留。

#### Scenario: 注册表未变更时重跑生成器

- **WHEN** 注册表自上次生成以来未发生变更
- **THEN** 重跑生成器不产生任何差异

#### Scenario: 手工维护区段被保留

- **WHEN** 文档中存在已声明为手工维护的区段
- **THEN** 重跑生成器后该区段内容保持不变

### Requirement: Documented commands must match the registry field by field

文档中每个语言条目的 `lint` 与 `format` 命令 SHALL 与注册表逐字段一致，包括占位符与参数顺序。

#### Scenario: 表格行与注册表不一致

- **WHEN** 任一语言行的命令文本与注册表对应字段不同
- **THEN** 校验报告该行，并指出两侧的实际取值

### Requirement: Drift must be detectable in both directions

文档与注册表之间的不一致 SHALL 有检查手段可检出，且该检查 SHALL 同时覆盖「文档落后于注册表」与「文档领先于注册表」两种方向。

#### Scenario: 文档落后

- **WHEN** 注册表已更新而文档未重新生成
- **THEN** 漂移检查失败并列出不一致条目

#### Scenario: 文档被手工前移

- **WHEN** 文档被手工修改，其内容为生成器无法产生
- **THEN** 漂移检查同样失败，使该修改必须回落到注册表或生成器

### Requirement: Drift check must run in the existing gate

漂移检查 SHALL 纳入既有的测试入口，与其余回归一起执行，无需额外的独立命令。

#### Scenario: 常规回归被执行

- **WHEN** 运行既有测试入口
- **THEN** 文档与注册表的漂移检查包含在其中，且失败会以非零状态体现
