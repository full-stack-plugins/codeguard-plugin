---
name: codeguard-security-api
description: |
  接口安全规范：越权与鉴权注解（Shiro/Spring Security）、数据权限、文件上传三层控制、
  apikey+timestamp+signature 签名机制。触发场景：用户写接口/鉴权/文件上传，或说"接口安全"、"越权"。
---

# 接口安全规范（越权 · 数据权限 · 文件上传 · 签名）

依据：PartMe.AI 开发规范「接口安全规范」。两大类常见漏洞：**越权绕过**、**文件上传漏洞**。

## 一、功能权限检查（防越权）

### 登录控制
- 单设备登录、登录环境检测、登录异常检测

### 接口鉴权注解（按框架选用，AI 写接口必须带）

**Shiro：**
```java
@RequiresAuthentication                    // 已认证
@RequiresUser                              // 已登录（含 rememberMe）
@RequiresGuest                             // 游客
@RequiresPermissions("sys:user:view")      // 单权限
@RequiresPermissions({"a", "b"}, logical = Logical.OR)   // 多权限任一
@RequiresRoles("admin")                    // 角色
```

**Spring Security：**
```java
@PreAuthorize("isAuthenticated()")
@PreAuthorize("hasAuthority('sys:user:view')")
@PreAuthorize("hasAnyAuthority('a','b')")
@PreAuthorize("hasRole('ADMIN')")
@PreAuthorize("hasAnyRole('ADMIN','OPS')")
```

AI 行为：写新增/修改/删除/查询接口时，若项目已用上述框架，**必须**补鉴权注解；缺失即提示。

## 二、数据权限检查（防越权取数）

- 请求参数检查：增删改查接口对数据归属参数做校验，
  如 `@RequiresDataPermissions`（校验学校代码等字段）+ `DataScopeProvider` 本地校验
- 返回数据过滤：按角色/用户设置数据访问范围，查询时动态追加筛选条件

AI 行为：写查询接口时注意 tenantId / shopId / 数据归属字段的过滤；禁止返回全表无过滤数据。

## 三、文件上传检查（三层控制）

| 层 | 控制项 |
|---|---|
| 前端 | 上传前回调校验：格式白名单（xls/doc/pdf/zip 等）+ 大小（如 ≤50MB） |
| 后端 | 基于 JSR303 Bean Validation 扩展注解（如 `@FileNotEmpty`）：非空、扩展名白名单、最大尺寸（如 ≤100MB）、MIME 类型检测 |
| 运维 | Nginx `client_max_body_size` 限制请求体（默认约 2MB，按需调整并 reload） |

风险：不限类型/大小/路径/文件名 → 攻击者传后门拿 WebShell。文件名存储须重命名（UUID），禁止用户可控路径拼接。

## 四、接口签名机制（延伸）

对外暴露的敏感接口采用 **apikey + timestamp + signature**：

1. 客户端：`signature = HMAC(secret, apikey + timestamp + body)`
2. 服务端：校验 apikey 有效 → timestamp 在窗口内（防重放）→ 重算 signature 比对
3. 建议窗口 ±5 分钟 + nonce 缓存防重放

## 五、AI 自查清单（写接口时逐项过）

- [ ] 有鉴权注解（或网关层已统一鉴权）
- [ ] 涉及数据归属的查询有数据权限过滤
- [ ] 文件上传有：白名单 + 大小限制 + 重命名存储
- [ ] 对外接口有签名/防重放
- [ ] 敏感返回字段已脱敏（见数据安全技能）
