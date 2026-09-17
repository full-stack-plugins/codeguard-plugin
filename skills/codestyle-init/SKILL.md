---
name: codestyle-init
description: |
  一键把 codestyle-check 接入当前仓库。检测项目语言、拷贝 linter 配置文件、写 .pre-commit-config.yaml、
  增量更新 AGENTS.md、生成 GitHub Actions CI 工作流。
  触发场景：用户说 "/init"、"接入规范检查"、"给项目加 pre-commit"、"加 CI 检查"。
---

# 初始化项目接入 codestyle-check

## 工作流

### 步骤 1：检测项目语言

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/detect_lang.py" .
```

### 步骤 2：拷贝对应 linter 配置文件

| 检测到语言 | 拷贝到项目根 |
|---|---|
| Java | `linters/checkstyle/p3c-javadoc-enforced.xml` → `checkstyle.xml` |
| Java | `linters/checkstyle/checkstyle-suppressions.xml` → `checkstyle-suppressions.xml` |
| Rust | `linters/clippy/strict.toml` → `clippy.toml` |
| TypeScript | `linters/eslint/recommended.cjs` → `eslint.config.js` |
| Python | 追加 `linters/ruff/pyproject-snippet.toml` 的 `[tool.ruff]` 块到 `pyproject.toml` |

### 步骤 3：写 .pre-commit-config.yaml

如果项目根**没有** `.pre-commit-config.yaml`，从 `linters/pre-commit/.pre-commit-config.template.yaml` 拷贝并按本项目语言**裁剪**（删掉不适用的语言块）。

如果**已有** `.pre-commit-config.yaml`，询问用户：「检测到已有 pre-commit 配置，是否合并 codestyle-check 项？」

### 步骤 4：增量更新 AGENTS.md

如果没有 `AGENTS.md`，创建并写入：

```markdown
# AGENTS.md

## 代码规范（由 codestyle-check 插件管理）

- 项目使用 [codestyle-check](https://github.com/partme-ai/codestyle-check-plugin)
- 检测到的语言：<从步骤 1 输出>
- Linter：checkstyle (Java) / clippy (Rust) / eslint (TS) / ruff (Python)
- **AI 写代码会被 PostToolUse 钩子强制 lint**；失败会阻塞继续
- **用户要求「提交/push」时** UserPromptSubmit 钩子会再次确认全部通过
```

如果已有 `AGENTS.md`，**追加**上述章节，不要覆盖已有内容。

### 步骤 5：写 GitHub Actions CI（可选）

如果项目根**没有** `.github/workflows/`，询问用户：「是否生成 GitHub Actions 工作流？」

如果是，写 `.github/workflows/lint.yml`：

```yaml
name: lint
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4   # Java 项目需要
        with: { distribution: temurin, java-version: 17 }
      - uses: actions/setup-python@v5  # Python 项目需要
        with: { python-version: '3.10' }
      - uses: actions/setup-node@v4    # TS 项目需要
        with: { node-version: '20' }
      - uses: arduino/setup-protoc@v1  # 仅 Rust 需要（如适用）
      - run: pip install pre-commit
      - run: pre-commit run --all-files
```

### 步骤 6：询问用户

输出安装指令（不自动执行）：
```bash
pip install pre-commit
pre-commit install
```

并提醒：「pre-commit 已配置好。现在每次 git commit 时会自动跑 linter。」

## 边界

- 不要删除或覆盖项目已有 `.pre-commit-config.yaml` / `checkstyle.xml` / `eslint.config.js`
- 不要覆盖已有 `AGENTS.md` 内容（只追加章节）
- 不要自动执行 `pre-commit install`（让用户决定）
