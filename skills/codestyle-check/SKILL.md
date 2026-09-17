---
name: codestyle-check
description: |
  跨语言代码规范检查。识别项目语言、跑对应 linter（Java javadoc+checkstyle、Rust clippy+fmt、
  TypeScript eslint、Python ruff）、自动修复（spotless:apply / cargo fmt / eslint --fix / ruff --fix）、
  输出报告。
  触发场景：用户说 "/check"、"代码规范"、"linter"、"checkstyle"、"clippy"、"eslint"、
  "javadoc"、"代码风格" 任意关键词；或 AI 准备提交/push 前的最后一步。
---

# 跨语言代码规范检查

## 工作流（严格按顺序）

### 步骤 1：检测项目语言

运行：
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/detect_lang.py" "$(pwd)"
```

输出例如：`["java", "rust"]`。如果返回 `[]`，说明当前目录不是代码项目，安静退出。

### 步骤 2：跑对应 linter

对每种语言执行对应命令：

| 语言 | 命令 | 关注点 |
|---|---|---|
| Java | `mvn -q javadoc:jar -DskipTests` | javadoc 错误会阻塞构建 |
| Java | `mvn -q checkstyle:check`（可选） | 阿里 P3C 风格 |
| Rust | `cargo clippy --all-targets -- -D warnings` | deny warnings |
| Rust | `cargo fmt --check` | 格式 |
| TypeScript | `npx eslint . --max-warnings 0` | 必须 0 warning |
| Python | `ruff check .` | 推荐 ruff（极快） |

可直接用插件脚本：
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_check.py"        # 全跑
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_check.py --lang java  # 只跑 java
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/run_check.py --fix    # 失败时自动修复
```

### 步骤 3：失败时尝试自动修复

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fix.py" --lang <name>
```

| 语言 | 修复工具 |
|---|---|
| Java | `mvn spotless:apply`（需项目配置 spotless） |
| Rust | `cargo fmt` |
| TypeScript | `npx eslint . --fix` |
| Python | `ruff check --fix` |

修复后**必须重跑 lint** 确认通过。

### 步骤 4：报告

按以下表格格式输出：

```
| 语言 | Linter | 通过 | 失败 | 自动修复 |
|---|---|---|---|---|
| Java | javadoc + checkstyle | 0 | 3 | ✅ 2 fixed |
| Rust | clippy + fmt | 5 | 0 | n/a |
| TS | eslint | 12 | 1 | ⏸ pending |
```

## 失败处理 SOP

1. **输出原 linter 错误**（不要二次解读）
2. **定位文件:行号**
3. **如果错误是格式类**（import order / 空格 / 长行）→ 直接跑 fix.py
4. **如果是逻辑类**（unused / missing Javadoc / bug pattern）→ 手动修复，**不要自动改业务代码**
5. **修复后重跑** 完整 lint 套件确认

## 边界

- **不要自动修改 linter 配置**（checkstyle.xml、clippy.toml 等）来让失败消失
- **不要屏蔽 warning**（`@SuppressWarnings`、clippy `allow`）除非用户明确同意
- **不要在测试代码里加 javadoc**（项目里应配置 suppressions.xml 排除）
