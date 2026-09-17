---
name: codelint-java
description: |
  Java 专项代码规范：javadoc 必须、checkstyle P3C 风格、Spotless 自动格式化。
  触发：用户说"Java 规范"、"javadoc"、"checkstyle"、"P3C"、"阿里规约"。
---

# Java 代码规范

## 强制项（违反必须修复）

### 1. javadoc（codestyle-check 插件核心约束）

- **public class / interface / enum**：必须 `@author` + 描述
- **public 方法**：必须 `@param`（每个参数）+ `@return`（非 void）
- **public 常量**：必须 `@xxx 含义`
- **构造器**：当 @param 不为空时必须写

示例：
```java
/**
 * 美团门店 token 自动刷新应用服务。
 *
 * <p>双轨制：定时扫描 + 调用前懒检查。</p>
 *
 * @author wandl
 */
public class MeituanTokenRefreshAppService {

    /**
     * 扫描即将过期的门店并逐条刷新。
     *
     * @param threshold 过期阈值（如 30min）
     * @param batchSize 单批最大扫描条数
     * @return 本轮成功补偿条数
     */
    public int refreshExpiringTokens(Duration threshold, int batchSize) {
        // ...
    }
}
```

### 2. 命名

- 类/枚举：UpperCamelCase（`MeituanShopAuth` 而非 `meituan_shop_auth`）
- 方法/变量：lowerCamelCase
- 常量：UPPER_SNAKE_CASE
- 包：全小写

### 3. Import

- 不允许 `import xxx.*;`（通配符）
- 不允许未使用的 import
- import 顺序：java.* / javax.* / 第三方 / 本项目（按字母序）

### 4. 检查命令

```bash
# javadoc 单独检查（codestyle-check 钩子默认调用）
mvn -q javadoc:jar -DskipTests

# checkstyle 阿里 P3C（需项目配置 checkstyle plugin）
mvn -q checkstyle:check

# 自动格式化（可选，配置 spotless 后可用）
mvn -q spotless:apply
```

## 推荐实践（非强制）

- `@Override` 注解必须
- `@Override` 注解**不需要 javadoc**（可抑制）
- 测试类**不需要 javadoc**（已在 checkstyle-suppressions.xml 排除）
- DTO / 枚举 / 简单 POJO 可批量添加 javadoc：使用 IDE 模板
- 类级 javadoc 第一句以句号结尾（被 JavadocStyle 检查）

## 常见错误速查

| 报错 | 修复 |
|---|---|
| `reference not found` | 引用的类不在 javadoc classpath；改 `{@link}` 为 `{@code}` |
| `heading out of sequence` | 类注释默认 H1，不要用 `<h3>`，用 `<p><b>` |
| `no caption for table` | `<table>` 加 `<caption>` |
| `no comment` warning | 公共方法/常量加 javadoc |
| `no @param` warning | 补 `@param` 对每个参数 |
