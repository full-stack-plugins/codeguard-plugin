# 七种分支模型总对照

> codeguard-git-branch 技能的渐进披露资料：一表看全 7 种主流模型的分支构成、流向与适用场景。详细逐模型说明见 SKILL.md 主体。

## 总对照表

| 维度 | Gitflow | Gitflow+（团队） | GitLab 分支规范（团队变体） | GitHub Flow | GitLab Flow | Trunk-Based | OneFlow | Release Flow |
|---|---|---|---|---|---|---|---|---|
| 长期分支 | master, develop | master, develop, test | 主干（默认分支）+ env/* | main | main + 环境/发布分支 | trunk/main | main | main + release/v* |
| 临时分支 | feature, release, hotfix | feature, fix, hotfix | feature/*,*-stable | feature（短命） | feature（短命） | <2 天短命分支（或直推） | feature, release(可选), hotfix | feature（短命） |
| 发布方式 | release → master → tag | test 回归 → release → master → tag | *-stable 分支 → PROD | 合并 main 即部署 | 环境晋升 / release 分支 | 每次提交可发布（feature flag） | main 打 tag | release/v* 维护 |
| 热修复 | master→hotfix→master+develop | master→hotfix→master（+develop） | feature 修复走 MR | main 直修 | cherry-pick 下游 | trunk 直修（flag 关闭） | main→hotfix→main | main 修 + cherry-pick 回 release |
| 合并方向门禁 | 严格 | 严格 | feature/*→主干 | feature→main | 上游→下游 | 全部→trunk | feature→main | 开发在 main，release 只收 cherry-pick |
| 适用 | 版本制产品 | 多环境团队迭代 | GitLab 多环境 | 小团队 SaaS | 需要环境晋升 | CI/CD 成熟高频发布 | Gitflow 现代化替代 | 多版本并行维护 |

## 模型识别速查（git branch -r 特征）

```text
有 develop + release/* + hotfix/*        → Gitflow（有 test → Gitflow+）
有 env/* 或 *-stable                     → GitLab 分支规范
有 main + production/staging             → GitLab Flow（环境式）
有 main + release/v*                     → Release Flow 或 GitLab Flow（发布式）
只有 main + 短命 feature/*               → GitHub Flow 或 TBD
  └─ 分支寿命 <2 天 + feature flag       → TBD
  └─ PR 评审驱动                          → GitHub Flow
```

## 合并策略速查

| 策略 | 命令 | 历史形态 | codeguard 建议 |
|---|---|---|---|
| Merge commit | `git merge --no-ff` | 保留分支拓扑 | Gitflow 系 master/release 合并默认 |
| Squash | `git merge --squash` | 压成单提交 | GitHub Flow / TBD 的 main 合并 |
| Rebase + ff | `git rebase && git merge --ff-only` | 线性 | OneFlow / TBD；禁对已推送共享分支 rebase |

## 迁移注意事项

1. 模型切换（如 Gitflow → TBD）是团队流程变更：先约定 feature flag 方案与测试覆盖
2. 旧分支（develop/release/*）冻结后保留一个发布周期再删
3. 保护分支规则（codeup/GitHub）必须与新模式同步更新
