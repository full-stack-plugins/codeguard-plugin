# Checkstyle P3C ↔ codeguard 规则映射

> 本文件是 codeguard-java 技能的渐进披露资料：说明 `linters/checkstyle/p3c-javadoc-enforced.xml` 中启用的每条规则、门禁级别与豁免方式。

## javadoc 族（codeguard 核心门禁，全部 error 级）

| Checkstyle 模块 | 门禁点 | 豁免方式 |
|---|---|---|
| `JavadocMethod` | public 方法缺 `@param`/`@return`；`allowMissingParamJavadoc=false` | `allowedAnnotations` 放行 @Override/@Test 等；测试目录走 suppressions |
| `JavadocType` | 类型 javadoc；`allowUnknownTags=false` 拦截坏标签 | — |
| `JavadocVariable` | public 常量需说明 | 局部变量不在 scope 内 |
| `JavadocStyle` | 首句句号、空 javadoc、HTML 完整性 | — |

## 命名族

| 模块 | 正则 | 常见违例 |
|---|---|---|
| PackageName | `^[a-z]+(\.[a-z][a-z0-9]*)*$` | 包名含大写 |
| TypeName | `^[A-Z][a-zA-Z0-9]*$` | 类名 snake_case |
| ConstantName | `^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$` | 常量小写 |
| MethodName / MemberName / LocalVariableName | `^[a-z][a-zA-Z0-9]*$` | 方法名大写开头 |

## Import 族

- `AvoidStarImport`：禁 `import x.*`
- `UnusedImports`：未使用 import（processJavadoc=true 会连 javadoc 里的 @link 一起判）
- `RedundantImport`：同包/同文件冗余导入

## 风格族

- `NeedBraces` / `LeftCurly` / `RightCurly`：大括号强制
- `WhitespaceAround`：运算符两侧空格
- `Indentation`：4 空格
- `LineLength`：160（忽略 package/import/URL 行）
- `ParameterNumber`：≤7

## 豁免的三条正路

1. **suppressions.xml 按路径豁免**（测试类、生成代码）——首选
2. **规则级 allowedAnnotations**（@Override/@Test 等）——已内置
3. **团队评审豁免**——临时 suppressions + 注销日期，禁止无期限

## 禁止事项

- ❌ 调低规则 severity 让失败消失
- ❌ 删除规则模块
- ❌ 对单文件加 `// CHECKSTYLE:OFF`（除非生成代码，且必须配 ON）
