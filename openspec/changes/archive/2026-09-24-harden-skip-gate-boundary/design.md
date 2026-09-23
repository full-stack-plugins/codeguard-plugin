## Context

见 proposal.md。会话实测（2026-09-21/24）：AI 在多仓以 `skipGate` 绕过存量 lint 债时，密钥入库检查被连带关闭；另见 `python3` 符号链接（`/usr/local/bin/python3` → Framework 3.13）使 `Path(sys.executable).parent` 指向不含 `ruff` 的目录，`ensure_user_path` 补错目录导致 6 项测试假失败（补 PATH 后 603/603 全过）。

## Goals / Non-Goals

**Goals:**

- 智能体可控的任何豁免都无法关闭密钥/凭据入库扫描。
- 工具链发现在符号链接解释器、多 Python 并存机器上不再误报「未安装」。

**Non-Goals:**

- 不改变 UNVERIFIED / fail-open 语义与退出码契约。
- 不引入命令级 `python3 -m` 改写（探活通过而执行失败会自相矛盾）——PATH 层修复已覆盖同解释器安装的全部工具。
- 不为 `check_paths` 的敏感模式表扩项。

## Decisions

### 1. 逃生门一分为二：lint 豁免 vs 完整豁免

`skipGate` 系（仓库级 / 内联 `-c` / 链式赋值）均为智能体可执行的 git 命令形态，只豁免**语言门禁**；入库安全扫描照常执行。进程环境变量 `CODEGUARD_SKIP_GATE` 无法由智能体注入钩子进程（宿主命令内联赋值不传入），是用户专属开关，保留为覆盖二者的完整逃生门。理由：安全扫描的威胁模型是"智能体误提/被绕过提交密钥"，而非人类用户；人类本来就可以在自己的终端直接提交。

### 2. 工具链修复落在 PATH 层而非 `-m` 回退

原建议是探活回退 `python3 -m <tool>`。根因分析后改为：`ensure_user_path` 补 `resolve().parent` 与 `sysconfig.get_path("scripts")`。理由：`-m` 回退只对 Python 模块工具有效且需同步改写执行命令（`ruff check .` 仍按裸名执行），探活通过而执行 127 会自相矛盾；PATH 修复对同解释器安装的全部工具（含非 Python 的 pipx / console scripts）生效，且零命令改写。`-m` 仅保留为 not_found 时的**诊断手段**（区分"未安装"与"入口缺失"）。

### 3. 安全扫描在豁免路径下复用同一暂存面计算

`git_guard_application` 中暂存面（lanes/extra）计算移出 `if not active: continue` 短路，语言门禁按 `active` 决定是否执行，安全扫描恒执行。快照不可证明时沿用既有 UNVERIFIED 出口，不静默放行。

## Risks / Trade-offs

- [存量 lint 债下以 skipGate 提交合法 fixture（如测试密钥素材）仍会被安全扫描拦] → 用户可用 `CODEGUARD_SKIP_GATE`（完整逃生门）或调整素材命名；报告文案显式指路。
- [行为变更触及 hook-protocol 既有场景措辞] → MODIFIED 增量携带完整更新文本，`openspec validate --strict` 把关。
- [探活重试多一次子进程] → 仅在 not_found 路径发生，成本可忽略。
