## 1. 本仓自有 markdown 问题（已完成，无需上游）

- [x] 1.1 `README.md` 表格与后续标题之间补空行（MD058）。
- [x] 1.2 `README.md` 去掉标题重复后缀 `(Git & Security) (Git & Security)`。
- [x] 1.3 `docs/LANGUAGES.md` 把两条说明合并为同一引用块（MD028）——就地修，不重新生成，以免丢失手工维护内容。
- [x] 1.4 修 `scripts/gen_language_docs.py` 中的同一根因，使未来重新生成不再复发 MD028。

## 2. markdown 命令修复

- [x] 2.1 `scripts/languages.json` 的 markdown `lint` 补显式 glob。
- [x] 2.2 `scripts/languages.json` 的 markdown `format` 补包管理器前缀与 glob（与 eslint/stylelint 条目写法一致）。
- [x] 2.3 `scripts/languages.json` 的 markdown `probe` 改用工具真实支持的可用性查询方式。
- [x] 2.4 `linters/markdown/.markdownlint-cli2.jsonc` 增加 `MD060` 禁用项，延续模板既有的「AI 产出文档不应用代码级规则拦截」定位。
- [x] 2.5 确认仓根 `.markdownlint-cli2.jsonc` 与模板保持一致（本仓已按 `codeguard init` 的方式拷入）。
- [x] 2.6 验证修好后命令返回真实 lint 结论而非用法错误。

## 3. 配置前置条件（requiresConfig）

- [x] 3.1 `scripts/languages.json` 为 markdown 声明 `requiresConfig`。
- [x] 3.2 `scripts/languages.json` 为 yaml 声明 `requiresConfig`。
- [x] 3.3 重新表述 `tests/run_all.py` 中「无 requiresConfig 视为已接入」这条断言——它记录的是「未声明时不做限制」，不是「不得声明」。
- [x] 3.4 新增用例：未接入 → 未验证且不阻塞；已接入 → 正常检查（工具缺失时断言「未验证」分支，CI 无 markdownlint 亦稳定）。
- [x] 3.5 新增用例：未声明前置条件的语言行为不变（防回归）。

## 4. 生成器可复现

- [x] 4.1 把「新增语言的流程」的 6 步版本（含外部技能仓与 vendor 流程）搬进 `gen_language_docs.py`。
- [x] 4.2 重跑生成器，逐条确认 31 处表格修正的方向正确（注册表为较新一侧）。
- [x] 4.3 确认注册表未变更时重跑生成器无差异。

## 5. 漂移检查

- [x] 5.1 `tests/run_all.py` 增加文档与注册表的逐字段比对（按语言行的 `lint` / `format`）。
- [x] 5.2 覆盖双向：文档落后于注册表、以及文档被手工前移（生成器无法产生的内容）。
- [x] 5.3 确认检查在既有测试入口内执行，无需额外命令。

## 6. 文档与会话提示

- [x] 6.1 `README.md` / `README.zh-CN.md` 说明 markdown 门禁的行为变更：此前恒为用法错误，此后返回真实结论。
- [x] 6.2 说明 `requiresConfig` 语义：未配置的仓转为「未验证跳过」，不再被默认规则全仓报错。
- [x] 6.3 明确记录：本仓 markdown 门禁转绿依赖上游修复，本次变更后仍不会绿。

## 7. 上游收口（跨仓，本变更不修改锁定内容）

- [x] 7.1 在 `full-stack-skills/codeguard-skills` 修 `skills/**` 下 80 条 markdown：66 `MD029/ol-prefix`、13 `MD056/table-column-count`、1 `MD037`。
- [ ] 7.2 发布不可变 tag。
- [ ] 7.3 插件侧更新 `skills.lock.json` 的 ref 并重跑 vendor。
- [ ] 7.4 确认本仓 markdown 门禁转绿（此时 `npx --no-install markdownlint-cli2 "**/*.md"` 应为 0 问题）。

## 8. 发布

- [ ] 8.1 运行 `python3 scripts/vendor/skill_vendor.py check --offline` 与在线 `check`。
- [ ] 8.2 按 AGENTS.md 执行 `node scripts/bump-plugin.mjs codeguard minor`（含行为变更）。
- [ ] 8.3 同步市场仓 `full-stack-plugins` 的 catalog 版本并重新生成三平台清单。
- [ ] 8.4 提交并推送插件仓与市场仓。
