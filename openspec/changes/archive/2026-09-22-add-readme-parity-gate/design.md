## Context

实测漂移证据（v0.6.6）：

1. **标题层级序列不等**（围栏外解析）：
   - 英文：`H2 Governance skills (Git & Security)` → `H3 External skill source`
   - 中文：`H2 外部技能来源`（缺包裹 H2）
   - 其余 20 个标题层级与顺序完全一致（H1×1 / H2×12 / H3×9 vs 修复前中文 H3×8）。
2. **版本串停在 0.5.4**：`| Current version | 0.5.4 |`（双语），实际已发 0.6.6+。
3. **vendor 快照串过期**：双语 4 处写 `v0.1.0`，`skills.lock.json.ref = v0.1.2`。
4. **docs 文件名含全角逗号** `5、`：两份 README 共 6 处链接 + 文档 H1 引用。

漂移根因：无门禁。曾考虑「英文 SSOT + 自动翻译生成中文」——被否：仓内无翻译管线，伪自动生成会把漂移换成假同步。选择**结构门禁 + 单 commit 镜像规则**：机器守结构（标题/链接/版本三类硬一致），人守译文。

## Decisions

### 门禁只守「结构可机检」三类

`tests/test_readme_parity.py` 断言（全部跳过 ``` 围栏，避免把 bash 注释 `#` 当标题）：

1. 标题层级序列相等（`[1,2,3,2,...]`）——不要求文字相同（语言不同），只要求结构镜像。
2. 本地链接目标集合相等（`](path)` 去掉 http/mailto/锚点）——docs 改名两边必须同时改。
3. `x.y.z` 版本串集合相等——`Current version`、vendor 快照等串任一边漏改即失败。

不守的：译文正确性（机器判不了）、图片 alt 文案、表格行数。

### mirror-edit 规则写进文件与 spec

两份 README 顶部各加一行 parity 注（互指 + 指向门禁测试）；spec `bilingual-docs-consistency` 加 Requirement：任一 README 修改必须同 commit 镜像另一份，结构差异由门禁拦截、译文差异由 review 拦截。

### 不做 SSOT 自动翻译

原因如上；若未来引入翻译管线，可在本 spec 下 MODIFIED Requirement 升级为「单源生成」。

### docs 改名目标与既有约定对齐

`docs/` 既有 `partme-codeguard-plugin-Architecture.zh_CN.md`——新名 `technical-roadmap.zh_CN.md` 同风格（蛇形 + `.zh_CN.md` 后缀）。文档 H1 去掉序号前缀 `5、`。共 7 处引用更新（README en×3 / zh×3 / 文档 H1×1）。

### 兼容性「已验证」行不升级

`✅ V0.5.4 verified` 是历史验证记录；在未对 0.6.7 重做宿主安装验证前改写它 = 虚假声明。`Current version` 行是事实字段（当前发布版本），跟着 release 走，本次预写 `0.6.7`（与本 change 的发版一致）。

## Risks / Trade-offs

- **门禁只挡结构漂移**：译文漏改仍靠 review——两份 README 顶部的 parity 注 + spec Requirement 是软约束。
- **`Current version` 行预写**：feat PR 合并到 release PR 之间存在短暂 README=0.6.7 / manifest=0.6.6 窗口；门禁不比对 manifest（只比对两份 README 互等），窗口内 CI 仍绿。release PR 合并后收敛。
- **docs 改名断外部深链**：该文件是中文技术方案，外部引用概率低；GitHub 对改名文件不自动重定向（wiki/issue 内的旧链接会 404）。接受此风险换取文件名可移植性。