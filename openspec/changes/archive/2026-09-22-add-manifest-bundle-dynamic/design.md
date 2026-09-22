## Context

实测基线（HEAD `5591125`）：
- `skills.lock.json` 1 个 source，union `skills` 集合 = 68 个 id
- `plugin-local-skills.json` 当前 `skills` 数组 = 0
- `skills/` 下含 `SKILL.md` 的目录 = 68 个
- 三者相等 → 现状 `68 == len(glob)` 通过

变更目标：让测试在校验 manifest 引用时同时校验三集合一致——任一漂移（lock bump 多/少、plugin-local 新增/移除但仓根漏目录、仓根目录漏登记到 lock）都会被同一断言捕获，错误信号强。

## Decisions

### 期望值从三源交叉推导

```python
lock_union = set().union(*(set(s["skills"]) for s in d["sources"]))
local = set(json.loads(PLUGIN_LOCAL.read_text())["skills"])
on_disk = {p.parent.name for p in ROOT.glob("skills/*/SKILL.md")}
expected = lock_union | local
```

测试断言改为：
- `on_disk == expected`：技能仓根与契约集合相等（防止 vendor 篡改或漏 vendor）。
- 每个 manifest 的 `skills` 字段等于 `{"skills", "./skills/"}` 中之一。

### 测试名去数字

魔法数字 `68` 仅是现状产物；改名为 `test_each_released_manifest_points_to_the_lock_union_plus_local_skills` 体现意图。

### 不引入新测试或新 fixture

变更限制在原测试方法的内部。增加测试会增加失败面（更多用例 = 更容易在 bump 时挂掉），与「去硬编码」的初衷相反。

## Risks / Trade-offs

- **第三方 contributor 看测试时不直观**：但测试名足够描述意图，docstring 注释「三源一致」即可。
- **未来加 manifest 新位置（如 docs/`x.json`）需同步测试**：这是正面的失败信号——任何契约变更都应主动改测试。