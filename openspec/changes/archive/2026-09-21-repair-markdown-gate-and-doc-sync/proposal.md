## Why

`markdown` 门禁从未工作过：注册表里 markdown 的 `lint` 命令是
`npx --no-install markdownlint-cli2`，而 markdownlint-cli2 v0.23.3 不接受无参数调用，
于是每一次门禁都以「用法错误」退出（exit 2）——它与仓库内容无关，是**结构性红**。
同时这条命令的 `probe` 把一个无效 flag 当成路径处理、`format` 引用未全局安装的二进制，
三者合起来意味着 markdown 的「工具可用性 / 检查 / 自动修复」三个环节都没有真正跑通过。

叠加两层后果：仓内 markdown 配置模板写于 `MD060` 规则出现之前，其禁用清单没有它，
因此一旦命令被修好，全仓会立刻被这条新规则淹没；而 `markdown` / `yaml` 未声明 `requiresConfig`，
使「项目未接入」被当成「已接入」，用工具**默认**规则扫全仓——这也是聚合工作区根目录永久红的原因。

排查过程中还发现一条独立的缺陷：`docs/LANGUAGES.md` 自称「由注册表自动生成」，
但实际**双向漂移**——表格落后于注册表（31 处命令不一致），而「新增语言的流程」一段又领先于生成器
（文档里的 6 步版本包含外部技能仓与 vendor 流程，生成器只会产出旧的 5 步版本）。
后果是**重跑生成器会同时修正与破坏**，在当前状态下并不安全。

## What Changes

- 修正 markdown 的命令三处：`lint` 补 glob、`format` 补包管理器前缀与 glob、`probe` 改用真实可用性查询。
- 给 `markdown` / `yaml` 声明 `requiresConfig`，使「项目未接入」回到「未验证、不阻塞」的既有语义。
- 仓内 markdown 配置模板补上 `MD060` 禁用项，与模板既有的「AI 产出文档不应用代码级规则拦截」定位一致。
- 让生成器覆盖文档的全部内容，然后重跑一次，使 `docs/LANGUAGES.md` 同时正确且可复现。
- 增加漂移检查，使文档与注册表任一方向的不一致都可见。

## Capabilities

### New Capabilities

- `language-gate-commands`: 注册表声明的 lint / format / probe 命令的可执行性要求，以及语言声明配置前置条件的能力。
- `language-registry-doc-sync`: 注册表到 `docs/LANGUAGES.md` 的可复现生成、命令逐字段一致性，以及漂移可检出。

### Modified Capabilities

None. 本仓 `openspec/specs/` 当前为空。

## Impact

- `scripts/languages.json`：markdown 的 `lint` / `format` / `probe`，`markdown` 与 `yaml` 的 `requiresConfig`。
- `linters/markdown/.markdownlint-cli2.jsonc`：新增 `MD060` 禁用项（会随 `codeguard init` 复制到用户项目）。
- `scripts/gen_language_docs.py`：覆盖「新增语言的流程」等区段，使文档可复现。
- `docs/LANGUAGES.md`：重新生成一次；`README.md`、`docs/LANGUAGES.md` 本次已就地修掉的自有 markdown 问题。
- `tests/run_all.py`：`无 requiresConfig 视为已接入` 这条断言的含义需重新表述——它描述的是「未声明时不做限制」，
  而不是「不得声明」；同时新增文档/注册表漂移断言。
- **行为变更**：markdown 门禁从「永远因用法错误而红」变为「真正按配置检查」。已接入 markdown 的仓将首次得到真实结论；
  未接入的仓转为未验证。这一改动会影响所有使用 codeguard 的仓，需在发布说明中明示。
- 上游 `full-stack-skills/codeguard-skills` 需修掉 `skills/**` 下 80 条 markdown 问题并发新 tag，插件重 vendor 后
  才能让本仓 markdown 门禁转绿；本变更不直接修改锁定技能内容。
