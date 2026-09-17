# javadoc 错误速查与实战案例

> 本文件是 codeguard-java 技能的渐进披露资料：汇总 doclint 全部常见错误、修复模板与 JDK 版本差异。全部案例来自 PartMe.AI 仓库实测。

## 一、error 级（阻断 javadoc 生成）

### 1. reference not found

**报错**：
```text
MeituanCallbackMsgType.java:11: error: reference not found
 * ...由 {@link com.qushiyun.cloud.meituan.api.adapter.message.callback.MeituanCallbackRouteSwitch} 路由...
```

**根因**：`{@link}` 引用的类位于其他 Maven 模块（如 common 引用 api），javadoc 编译当前模块时该类不在 classpath。

**修复**：
```java
// ❌ 跨模块 {@link}
由 {@link com.qushiyun.cloud.meituan.api.adapter.message.callback.MeituanCallbackRouteSwitch} 路由
// ✅ 改 {@code} 纯文本（或文字说明所在模块）
由 api 模块的 {@code MeituanCallbackRouteSwitch} 路由
```

### 2. heading used out of sequence

**报错**：
```text
error: heading used out of sequence: <H3>, compared to implicit preceding heading: <H1>
```

**根因**：类 javadoc 的隐式标题层级从 H1（类名）开始，直接写 `<h3>` 跳过 H2。

**修复**：小节标题用加粗段落替代标题标签：
```java
 * <p><b>已配置回调 msgType</b></p>     // ✅
 * <h3>已配置回调 msgType</h3>          // ❌
```
注意：第一个标题降级后，后续 `<h3>` 反而"合法"（前序已是 H3）——所以会出现只报第一个的假象，**全部都要改**。

### 3. no caption for table

**报错**：
```text
error: no caption for table
 * </table>
```

**修复**：`<table>` 标签后立即补 `<caption>`：
```java
 * <table border="1">
 *   <caption>已配置回调 msgType 一览</caption>
 *   <tr><th>msgType</th>...
```

## 二、warning 级（不阻断但按团队门禁清零）

### no comment / no @param / no @return

| 场景 | 修复模板 |
|---|---|
| 公共方法 | `/** 说明。\n     *\n     * @param msgType 参数含义\n     * @return 返回值含义\n     */` |
| 构造器 | 每个参数 `@param`；带 cause 的补 `@param cause` |
| public 常量 | `/** 常量含义。 */` 单行即可 |
| 默认构造器警告 | 类已有 javadoc 时给类补 `@author`，或给构造器补注释 |

### use of default constructor, which does not provide a comment

两种根因：
1. 类完全没有 javadoc → 补一份
2. **类上方有多份 javadoc 块**（改动遗留）→ javadoc 只认紧邻 class 的那份，合并为一份
   实测案例：`@Data` 注解两侧各一份 javadoc，工具告警 default constructor——删掉远离 class 的那份。

## 三、死代码案例（顺带审计发现）

```java
// ❌ 原实现：前两个分支 return 后，第三个 return 重新查询相同条件，永远只走到 3
return receiptRepository.findFirstConsumedByAppIdAndOrderNo(app.getId(), orderNo).isPresent()
        ? 2
        : (anyReceipt.isPresent() ? 1 : 3);
// ✅ 修复：直接 return QUERY_STATUS_NOT_REGISTERED（该分支语义就是"无记录"）
```

教训：清理注释时如果发现控制流冗余，确认语义后简化，并在 commit 里说明。

## 四、JDK 版本差异

| JDK | doclint 行为 |
|---|---|
| 11 | 基础 HTML 检查 |
| 17 | 新增部分 HTML5 校验；`{@snippet}` 可用 |
| 21 | 更严格的标题/表格序列检查（团队实测案例在 21 上暴露） |

CI 与本地 JDK 必须对齐——本地 17 通过不代表 CI 21 通过，反之亦然。

## 五、批量清理技巧

1. 先修 error（3 类），warnings 单独一轮清
2. 同类 warning 用 IDE 结构化替换或脚本批处理
3. 每轮修复后跑 `mvn -q javadoc:jar -DskipTests` 确认数量下降
4. 团队门禁目标：**0 error**；warning 清零是第二步
