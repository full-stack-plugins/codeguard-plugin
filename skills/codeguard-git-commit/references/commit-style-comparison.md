# Commit 风格对比：Conventional / Gitmoji / Udacity

> codeguard-git-commit 技能的渐进披露资料。团队钦定 Conventional Commits（Angular 正则），其余两种要求识别与兼容。

## 一、三风格总对照

| 维度 | Conventional | Gitmoji | Udacity |
|---|---|---|---|
| 格式 | `type(scope): subject` | `:emoji: subject` 或 emoji + Conventional | 首行 ≤50 + 空行 + 正文（每行 ≤72） |
| 机器可读 | ✅（工具链成熟） | ⚠️ 弱（需 emoji 表映射） | ❌ |
| 语义化版本联动 | ✅（feat/fix 驱动） | ❌ | ❌ |
| 学习成本 | 低 | 最低 | 中 |
| 团队门禁 | commit-msg 正则 ✅ | 剥离 emoji 后走 Conventional | 人工评审 |

## 二、Gitmoji 完整常用表

| emoji | shortcode | 含义 | 对应 conventional type |
|---|---|---|---|
| ✨ | `:sparkles:` | 新功能 | feat |
| 🐛 | `:bug:` | 修 Bug | fix |
| 📝 | `:memo:` | 文档 | docs |
| 🎨 | `:art:` | 结构/格式 | style |
| ⚡ | `:zap:` | 性能 | perf |
| ♻️ | `:recycle:` | 重构 | refactor |
| ✅ | `:white_check_mark:` | 测试 | test |
| 🔧 | `:wrench:` | 配置 | chore |
| 👷 | `:construction_worker:` | CI | ci |
| ⏪ | `:rewind:` | 回滚 | revert |
| 🔥 | `:fire:` | 删代码 | chore |

**codeguard 双写约定**：`✨ feat(美团对接)：新增授权链接生成` —— emoji 给人看，type 给门禁看。

## 三、Conventional Commits 细则

### BREAKING CHANGE 三种写法

```text
feat!(x): 破坏性变更简述              # type 后 !
feat(x): 简述                          # 或 body 末尾：
 
BREAKING CHANGE: 参数 x 改为必填
```

### 与 semver 联动

| 提交类型 | 版本动作 |
|---|---|
| fix | PATCH +1（1.1.1） |
| feat | MINOR +1（1.2.0） |
| BREAKING CHANGE | MAJOR +1（2.0.0） |
| 其余 type | 不触发版本变化 |

## 四、Udacity 风格模板

```text
Add user authentication middleware

Introduce a JWT-based middleware that validates tokens on
protected routes. Chose JWT over session storage because the
API is consumed by both web and mobile clients.

Refs: #142
```

- 首行：祈使句、≤50 字符、结尾不加句号
- 正文：解释 **what 与 why**（不是 how）；每行 ≤72 字符

## 五、commitlint 接入（Node 项目）

```bash
npm install --save-dev @commitlint/cli @commitlint/config-conventional
echo "module.exports = { extends: ['@commitlint/config-conventional'] };" > commitlint.config.js
npx commitlint --from HEAD~1     # 校验最近一次提交
```

husky 接入：`npx husky init && echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg`
