---
name: codeguard-git-commit
description: |
  Commit 日志规范：整合主流风格——Conventional Commits（Angular）、Gitmoji、Udacity，
  含正则门禁、commitlint 工具与示例。AI 代写提交信息必须遵守。
  触发场景：AI 帮用户写 commit message、执行 git commit、或用户说"提交规范"、"commit 规范"。
---

# Commit 日志规范（三种主流风格整合）

依据：PartMe.AI Commit 日志规范（Angular 正则）+ 业界主流实践。

## 一、先识别项目现有风格

`git log --oneline -20` 看团队习惯：多数提交形如 `feat(x): y` 用 **Conventional**；带 `✨`/`🐛` emoji 用 **Gitmoji**；首行 50 字左右空行后正文用 **Udacity**。识别不出按 Conventional（团队 wiki 钦定）执行。

## 二、Conventional Commits（团队钦定，事实标准）

### 格式正则（门禁）

```text
^(feat|fix|docs|style|refactor|test|chore|ci)((.+))?: .{1,100}
```

配套校验脚本：`linters/git/commit-msg`（兼容半角/全角冒号、冒号后空格可选、Gitmoji 前缀剥离）。

### 三要素

| 要素 | 说明 |
|---|---|
| **type** | fix / feat / test / style / docs / refactor / chore / ci（+ 业界常用 perf、revert） |
| **scope** | 影响范围：模块、类库、方法（可省略） |
| **subject** | 简短描述 ≤60 字；关联 Bug ID 建议注明 |

### 完整 type 对照（Conventional Commits 1.0.0）

| type | 含义 | 版本语义 |
|---|---|---|
| `feat` | 新功能 | MINOR +1 |
| `fix` | Bug 修复 | PATCH +1 |
| `perf` | 性能优化 | PATCH +1 |
| `refactor` | 重构（不改行为） | — |
| `style` | 格式/注释（不改逻辑） | — |
| `test` | 测试 | — |
| `docs` | 文档 | — |
| `build` | 构建系统/依赖 | — |
| `ci` | CI 配置 | — |
| `chore` | 杂务 | — |
| `revert` | 回滚 | — |

（`feat`/`fix` 后加 `!` 或 body 含 `BREAKING CHANGE:` 表示破坏性变更 → MAJOR +1）

### 示例

```text
fix(首页模块)：修复弹窗 JS Bug
feat(美团对接)：新增门店 OAuth 授权链接生成
refactor(token)!: 双轨刷新合并为单一入口（升级需重配 cron）
docs(readme)：补充三端安装说明
```

## 三、Gitmoji（emoji 前缀风格）

形如 `:emoji: subject` 或直接 unicode emoji。常用对照：

| emoji | 含义 | 对应 conventional |
|---|---|---|
| ✨ `:sparkles:` | 新功能 | feat |
| 🐛 `:bug:` | 修 Bug | fix |
| 📝 `:memo:` | 文档 | docs |
| 🎨 `:art:` | 格式/结构 | style/refactor |
| ⚡ `:zap:` | 性能 | perf |
| ♻️ `:recycle:` | 重构 | refactor |
| ✅ `:white_check_mark:` | 测试 | test |
| 🔧 `:wrench:` | 配置/杂务 | chore |
| 👷 `:construction_worker:` | CI | ci |
| 🔥 `:fire:` | 删代码/文件 | — |

**codeguard 规则**：Gitmoji 可作前缀（脚本会自动剥离后按 Conventional 校验），如
`✨ feat(美团对接)：新增授权链接生成`——emoji + type 双写，机器可读 + 人类直观。

## 四、Udacity 风格（长描述型）

```text
首行：变更摘要（≤50 字符，祈使句）

正文：解释 what 与 why（而非 how），每行 ≤72 字符。
      可分段说明动机、方案对比、副作用。
```

适合：复杂重构、架构变更等需要向未来读者解释决策的提交。团队日常迭代不强制。

## 五、工具化

- 门禁脚本：`linters/git/commit-msg`（pre-commit 模板已预置 `stages: [commit-msg]`）
- commitlint（Node 项目）：
  ```bash
  npm install --save-dev @commitlint/cli @commitlint/config-conventional
  echo "module.exports = { extends: ['@commitlint/config-conventional'] };" > commitlint.config.js
  ```
- 手动启用 hook：`cp linters/git/commit-msg .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg`

## 六、AI 代写 commit 的规则

1. 先 `git diff --cached` 看**实际改动**，不凭对话记忆编造
2. type 按改动实质选择；混合改动拆分提交或取主导类型
3. scope 与项目既有 commit 风格一致（`git log --oneline -20` 参考）
4. subject 说清「做了什么」，禁止 `update` / `fix` 等空泛词
5. 提交者与作者邮箱必须使用已验证邮箱
6. 不确定时问用户，**不得**用 `--no-verify` 绕过门禁
