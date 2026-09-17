---
name: codeguard-git-branch
description: |
  Git 分支规范：Gitflow / Gitflow+（含 test 分支）/ GitLab 分支三类模型，分支命名与合并方向门禁。
  触发场景：AI 帮用户创建/切换/合并分支、规划发版流程、或用户说"分支规范"、"gitflow"、"建分支"。
---

# Git 分支规范

依据：PartMe.AI Git 规范 wiki（GitLab 分支规范 / Git 工作流程 / Gitflow / Gitflow+）。

## 一、先确认项目使用哪种分支模型

| 模型 | 特征 | 适用 |
|---|---|---|
| **Gitflow+（团队在用）** | master / develop / test / release / hotfix | 常规产品迭代（默认按此执行） |
| **Gitflow（标准）** | master / develop / feature / release / hotfix | 无独立测试环境的项目 |
| **GitLab 分支规范** | 主干 + `feature/*` + `*-stable` + `env/*` | GitLab MR 流、多环境部署 |

判断方法：看远端分支（`git branch -r`）存在 `develop` 走 Gitflow 系；存在 `env/*` 走 GitLab 模型。

## 二、分支命名（AI 创建分支必须遵守）

```text
feature/{version}_{function}_{author}_{datetime}
fix/{version}_{function}_bug_{author}_{datetime}
hotfix/{function}_{author}_{datetime}
release/{version}
```

示例（来自团队规范原文）：
- `feature/1.1.0_video_a_20200806`
- `fix/1.1.0_video_upload_bug_alicfeng_20200808`
- `hotfix/video_alicfeng_20200809`

规则：
- AI 代建分支时 **必须** 先从用户或 git log 获取 author 与当天日期（YYYYMMDD），不得编造
- version 取自最近 tag（`git describe --tags --abbrev=0`）或用户指定
- GitLab 模型下：功能分支一律 `feature/*`；发布分支 `*-stable`；环境分支 `env/uat`、`env/production`

## 三、合并方向门禁（AI 执行合并前自检）

### Gitflow+（默认）

| 源 | 允许合并到 |
|---|---|
| master ← | 仅 release、hotfix（合并必打 tag） |
| develop ← | master 初始化、feature 合并 |
| test ← | develop、测试通过的 feature |
| release ← | 测试通过的 feature |
| hotfix ← | 从 master 拉出；修复合回 master |

### GitLab 模型

- 目前规定的方向：**feature/* → 主干分支**；其余方向若仓库有限制配置则遵守之。

## 四、工作流要点（AI 提交/合并时遵守）

1. 高频细粒度提交：大功能拆小模块，完成即提交
2. 提交前必须自测/单测通过
3. 有改动至少一天一提交
4. feature 完成合并回 develop 后**删除功能分支**（谁的分支谁删）
5. hotfix 必须同时合入 master 与 develop，并升补丁版本号打 tag（如 1.1.1）
6. master 每次合并必须设置版本号并打 tag，tag 信息写明更新内容

## 五、AI 行为清单

- [ ] 建分支前：确认分支模型、命名符合上文格式
- [ ] 合并前：确认合并方向在门禁表内
- [ ] 合 master 前：确认已打版本 tag 的计划（问用户版本号）
- [ ] 严禁：直接向 master 提交；从未发布分支反向合并；跳过 develop 直合 test
