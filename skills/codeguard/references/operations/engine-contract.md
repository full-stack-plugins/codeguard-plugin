# 引擎契约：判定由谁签发

> 目标是消除“看起来没问题”与“真的检查过”之间的空隙。任何 PASS 都必须能指回一次真实执行。

## 存在两个引擎

| 引擎 | 位置 | 判定强度 |
| --- | --- | --- |
| Legacy Python CLI | 插件仓 `bin/codeguard` → `scripts/run_check.py` | 可签发 PASS / FAIL |
| Rust `codeguard` 组件 | 独立组件仓，二进制 `codeguard` | **当前不可签发质量结论** |

Rust 组件是新的统一内核，方向上最终取代 Legacy。**但在它自己解除未完成状态之前，Legacy 才是唯一能产出质量判定的引擎。**

不要因为“Rust 更新”就把技能全部改写成 Rust 命令——那会让所有检查恒为未完成，比旧契约错误更糟。

## 先探测，再选命令

```bash
codeguard --version --format json 2>/dev/null && echo ENGINE=rust
```

- 命令成功且 `format_version` 属于 Rust 组件协议 → `ENGINE=rust`
- 探测失败，或只存在插件仓的 `bin/codeguard` → `ENGINE=legacy`

探测本身失败就是 `UNVERIFIED`。不要因为“猜它是哪个”就继续。

## 两套命令面

### Legacy Python CLI

```bash
codeguard detect [path]
codeguard check [--lang LANG[,LANG...]] [--timeout N] [path]
codeguard fix [--lang LANG] [--dry-run] [path]
codeguard cve [--ecosystem maven|node|python|rust|go|universal] [--severity S] [--fix] [--json] [path]
codeguard dockerfile [--json] [path]
codeguard java-plan [args]
```

退出码：`0` 通过 / `1` 无法验证 / `2` 存在违规 / `3` 参数错误。

### Rust 组件（能力未完成）

```bash
codeguard --version | capabilities | detect | init | doctor | plan | config | tools
codeguard check <all|java> [path] [--timeout DURATION] [--format human|json|sarif]
codeguard lint <python|typescript|go|java> [path]
codeguard comments rust [path]
codeguard build rust [path]
codeguard cve <rust|python|typescript> [path]
codeguard rules list|whitelist <...>
codeguard work sync | status | next
codeguard task show|claim|heartbeat|release|attempt|verify ID
codeguard gate pre-commit [path]
```

Rust 组件当前对所有质量路径固定返回退出码 `3`（检查未完成），能力矩阵中全部条目为 `gap`。**因此：**

- 可以用 `detect` / `capabilities` / `plan` / `doctor` 做只读观察。
- **不能**用它的 `check` / `lint` / `cve` 结果声称任何质量通过。
- 它的输出只能表述为“局部原生观察”或“未完成”。

## 已发生的不兼容

从 Legacy 迁到 Rust 时，以下调用**已经失效**。在两个引擎下都不要写：

| 旧调用 | 状态 | 说明 |
| --- | --- | --- |
| `codeguard check --lang java` | 无效 | Rust `check` 只接受位置参数 `all\|java` |
| `codeguard fix` | **Rust 侧不存在** | 只在 Legacy 可用 |
| `codeguard cve --ecosystem node` | 无效 | Rust 改用位置参数 `cve typescript` |
| `codeguard cve --severity HIGH` | 无效 | Rust 侧无严重度阈值参数 |
| `codeguard cve --fix` | 无效 | Rust 侧无自动修复 |
| `codeguard cve --json` | 无效 | Rust 改用 `--format json` |
| `codeguard dockerfile` | **Rust 侧不存在** | 只在 Legacy 可用 |

`--timeout` 两边都有，但格式不同：Legacy 是裸秒数（`--timeout 60`），Rust 是 duration（`--timeout 30m`）。

## 汇报纪律

1. 报告里写明用的是哪个引擎，不要把 Legacy 结果说成 Rust 结果，反之亦然。
2. 引擎探测失败、工具缺失、配置错误 → `UNVERIFIED`，并说明缺什么。
3. 单个检查通过不等于整体通过；列出未执行的检查项。
4. 不要为了“让命令跑通”而改写事实。Rust 组件返回 3 是诚实结果，不是需要绕过的障碍。
