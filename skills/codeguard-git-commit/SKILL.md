---
name: codeguard-git-commit
description: |
  Commit 日志规范：Angular 风格 type(scope): subject，含正则门禁与示例。AI 代写提交信息必须遵守。
  触发场景：AI 帮用户写 commit message、执行 git commit、或用户说"提交规范"、"commit 规范"。
---

# Commit 日志规范

依据：PartMe.AI Git 规范 wiki「Commit 日志规范」。

## 一、格式正则（门禁）

```text
^(feat|fix|docs|style|refactor|test|chore|ci)((.+))?: .{1,100}
```

配套校验脚本：`linters/git/commit-msg`（供 pre-commit / commit-msg hook 使用，见文末）。

## 二、三要素

| 要素 | 说明 |
|---|---|
| **type** | fix 修 Bug / feat 新功能 / test 调试 / style 格式或注释 / docs 文档 / refactor 重构 / chore、ci 等 |
| **scope** | 影响范围：模块、类库、方法（可省略） |
| **subject** | 简短描述，≤60 字；关联 Bug ID 建议注明 |

## 三、示例

```text
fix(首页模块)：修复弹窗 JS Bug
feat(美团对接)：新增门店 OAuth 授权链接生成
docs(readme)：补充三端安装说明
refactor(token)：双轨刷新合并为单一入口
chore(deps)：jackson bom 升级至 2.13.5
```

## 四、AI 代写 commit 的规则

1. 先 `git diff --cached`（或 `git diff`）看**实际改动**，不凭对话记忆编造
2. type 按改动实质选择；一次提交混合多种改动时拆分提交或取主导类型
3. scope 用模块/功能中文名或英文短词，与项目既有 commit 风格一致（可 `git log --oneline -20` 参考团队习惯）
4. subject 说清楚「做了什么」，避免「修改」「优化」等空泛词
5. 提交者与作者邮箱必须使用已验证邮箱（团队 Git 平台要求）
6. **禁止** `git commit -m "update"`、`-m "fix"` 之类无信息提交

## 五、commit-msg 门禁接入

pre-commit 模板已含：

```yaml
- id: conventional-commit-msg
  name: Conventional Commit message (codeguard)
  entry: ./linters/git/commit-msg
  language: system
  stages: [commit-msg]
```

手动启用：`cp linters/git/commit-msg .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg`
