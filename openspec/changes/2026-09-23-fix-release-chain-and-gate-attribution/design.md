## Context

v0.15.0 发版实测：bump-plugin 的两个 plain manifest 没被更新（catalog 0.14.14 vs manifest 0.14.12
漂移 → replace 静默 no-op），且 `node scripts/bump-plugin.mjs` 被 git 意图门禁不可绕过地拦住
（UNVERIFIED）。后者的机制：`_indirect_body` 取到 .mjs 正文后，`split_shell_segments` 按 shell
语法切段，帮助文本模板字符串里的 `git add && git commit && git push` 被认成真实副作用；resolve 阶段因
「非 Shell 正文不可建模」抛 GitIntentError——而 skipGate/内联豁免都在解析成功之后才评估，故不可绕过。

## Goals / Non-Goals

**Goals:**
- 版本漂移时发版工具 fail-loud，写后回读校验，消除半程假成功。
- 非 Shell 正文的 git 归因只认 subprocess/exec 调用形态，消除帮助文本误报；
  真实间接 git 调用保持「UNVERIFIED 阻断」的既有保守语义。

**Non-Goals:**
- 不建模 Node/Python 的动态拼接 subprocess（设计既有边界）。
- 不改 Shell 正文的切段解析与 skipGate 链语义。
- 不改 bump 的版本计算规则（仍以 catalog 为 oldVersion 源）。
- Bash heredoc/命令文本数据段的 git 样例误报不在本次范围（需完整 shell 解析，另立 change）。

## Decisions

**fail-loud 而非 regex 自愈。** 替换失败时按任意版本强行覆盖会把「上游误升/误降」也静默吞掉；
显式抛错并报告 manifest 实际版本与 catalog 版本，把漂移暴露给人，符合 verdict-integrity
「不把缺失证据标为通过」。写后回读校验五文件版本一致，崩溃在 sync 步之前也能被拦住。

**非 Shell 正文按调用形态识别，不按文本切段。** 高精度信号是 `execFileSync("git", …)`、
`subprocess.run(["git", …])`、`os.system("…")` 这类调用点；帮助文本不会以调用形态出现
（bump 帮助文本前是 `console.log(`，不匹配调用词表）。命中调用形态 → 沿用既有阻断
（不可建模 UNVERIFIED），保持「宁可拦住不放行不可证明的 git」的方向安全。
误报面收窄到「帮助文本里恰好写成调用形态的样例」，可接受。

## Risks / Trade-offs

- 调用词表是启发式：`eval(...)`、动态拼接命令等仍漏检——与既有「不承诺分析动态拼接」
  边界一致，不新增风险敞口。
- fail-loud 会让漂移状态的发版直接失败：这是特性而非代价（此前是假成功）。
- bump 自身的发版即 dogfood 验证（工具修好后直跑它自己发版）。

## Verification

- 新增回归测试全绿 + 全量 unittest / run_all 零新增失败 + ruff 干净。
- 直跑 `node scripts/bump-plugin.mjs`（不带 sh -c 包装）通过门禁 = 误报修复的活证据。
- bump 在制造的漂移 fixture 上抛错 = fail-loud 活证据。
