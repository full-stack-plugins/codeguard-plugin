---
name: codeguard-java
license: Apache-2.0
description: |
  Apply Java lint gates (javadoc, Checkstyle P3C), diagnose javadoc errors and warnings,
  enforce Java naming/import/style conventions, and fix style violations via Spotless.
  Use when users write or review Java, hit mvn javadoc:jar failures, see checkstyle errors,
  or ask about P3C/Alibaba style rules, javadoc tags, or Java naming conventions.
  Route deep Java syntax/framework/library questions to the java-skills repository;
  route commit format to codeguard-git-commit and CVE findings to codeguard-security-code.
---

# Java 代码规范门禁

> 基于 [Checkstyle](https://checkstyle.sourceforge.io/)、[Alibaba P3C](https://github.com/alibaba/p3c)、[Spotless](https://github.com/diffplug/spotless) 与团队 `mvn javadoc:jar` 门禁实践。

## Capability Boundaries

### ✅ Strengths
1. javadoc 门禁：`mvn javadoc:jar` 三类 error（reference not found / heading sequence / table caption）与全部 warnings 的诊断与修复
2. Checkstyle P3C：命名、import、复杂度、行宽规则与抑制配置
3. Spotless 自动格式化接入
4. doclint 严格模式（JDK 17/21）下的 HTML 规则（`<caption>`、标题层级、跨模块 `{@link}`）

### ⚠️ Prerequisites
1. Maven 与 JDK 17+；javadoc 门禁建议使用与 CI 一致的 JDK（doclint 规则随 JDK 收紧）

### ❌ Out of Scope
1. Java 语法学习、Spring/MyBatis 等框架用法 → [java-skills](https://github.com/full-stack-skills/java-skills)
2. 依赖漏洞（CVE）→ `codeguard-security-code`
3. 提交格式 → `codeguard-git-commit`

## When to Use

- "javadoc 报错了" / "checkstyle 失败" / "P3C 规则"
- AI 写完 `.java` 文件后钩子拦截
- "Java 命名规范" / "import 排序"

## I. javadoc 门禁（核心约束）

```bash
mvn -q javadoc:jar -DskipTests      # 门禁命令（零改动可跑）
```

强制规则：
- public 类/接口/枚举：javadoc + `@author`
- public 方法：每个参数 `@param` + 非 void 加 `@return`
- public 常量：单行 javadoc 说明含义
- `@Override` 方法豁免；`src/test/**` 豁免（suppressions.xml）

错误速查（全部来自真实踩坑，详见 [references/javadoc-error-quickref.md](references/javadoc-error-quickref.md)）：

| javadoc 报错 | 根因 | 修复 |
|---|---|---|
| `reference not found` | `{@link}` 指向的类不在当前模块 classpath（常见于 common 模块引用 api 模块） | 改 `{@code ClassName}` 纯文本 |
| `heading used out of sequence` | 类注释隐式 H1，直接用 `<h3>` 跳级 | `<h3>` 改 `<p><b>...</b></p>` |
| `no caption for table` | `<table>` 缺 `<caption>` | 表格首行加 `<caption>标题</caption>` |
| `no comment` / `no @param` / `no @return` | 公共成员缺 javadoc | 按强制规则补齐 |
| `use of default constructor...` | class 声明上方 javadoc 块不紧邻或重复 | 合并为单份紧贴 class 行 |

## II. Checkstyle P3C

```bash
mvn -q checkstyle:check          # 项目配置 checkstyle 插件后可用
```

配置模板：`linters/checkstyle/p3c-javadoc-enforced.xml`（P3C 风格 + javadoc 强制）、
`linters/checkstyle/checkstyle-suppressions.xml`（测试类/生成代码豁免）。

| 规则族 | 要点 |
|---|---|
| 命名 | 类 UpperCamelCase / 方法 lowerCamelCase / 常量 UPPER_SNAKE_CASE / 包全小写 |
| Import | 禁通配符 `.*`、禁未使用、分组排序 |
| 复杂度 | 方法参数 ≤7；行宽 160 |

## III. Spotless 自动格式化

```bash
mvn -q spotless:apply            # 自动修复格式类问题
mvn -q spotless:check            # CI 检查
```

Spotless 只修格式（缩进/import 排序/行尾），**不修** javadoc 缺失。

## IV. 集成方式

- PostToolUse 钩子：AI 写 `.java` 后自动跑 `mvn javadoc:jar`（默认门禁）
- pre-commit：`.pre-commit-config.yaml` 的 `maven-javadoc` hook
- CI：`mvn verify`（javadoc 在 package 阶段触发）

## Workflow

1. 写完 `.java` → 等 codeguard 钩子结果（或手动 `mvn -q javadoc:jar -DskipTests`）
2. 有 error → 按速查表修复
3. 格式类 warning → `mvn -q spotless:apply`
4. 复跑至零 error
5. 提交前跑一次全模块（多模块取最坏结果）

## Gotchas

1. `mvn compile` 不跑 javadoc——本地绿色不代表 install/deploy 绿色
2. doclint 严格度随 JDK 升级收紧（17 → 21 有新增检查），CI 与本地 JDK 要对齐
3. 跨模块 `{@link}` 是重灾区：common 模块永远解析不到 api 模块的类
4. Javadoc 里的 cron 表达式 `"0 */10 * * * ?"` 会被 doclint 当成注释结束符——写成 `"0 0/10 * * * ?"`
5. 同一 class 上叠加多份 `/** */` 块能编译通过，但 javadoc 只认紧邻的那份

## On-Demand Resources

- [javadoc 错误速查与实战案例](references/javadoc-error-quickref.md)：doclint 全错误分类、修复模板、JDK 版本差异
- [Checkstyle P3C ↔ codeguard 规则映射](references/checkstyle-p3c-mapping.md)：启用规则逐条说明与豁免配置

## Official References

- [Checkstyle](https://checkstyle.sourceforge.io/) · [Alibaba P3C](https://github.com/alibaba/p3c) · [Spotless](https://github.com/diffplug/spotless) · [Javadoc Guide](https://docs.oracle.com/en/java/javase/17/javadoc/javadoc.html)
