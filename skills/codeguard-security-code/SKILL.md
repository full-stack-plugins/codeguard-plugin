---
name: codeguard-security-code
description: |
  代码安全规范：代码泄露 / 配置泄露 / 依赖漏洞（CVE）三大检查项，含前后端扫描工具命令。
  触发场景：用户说"代码安全"、"配置泄露"、"CVE"、"漏洞扫描"、"依赖检查"、"安全检查"。
---

# 代码安全规范（泄露 · 配置 · CVE）

依据：PartMe.AI 开发安全规范「代码安全规范」。核心原则：**源码与配置不得暴露到公共网络**。

## 一、代码泄露检查

| 检查项 | 要求 |
|---|---|
| Git 访问方式 | 必须使用 SSH 或 HTTPS + 凭据；禁止 http 明文协议拉取推送 |
| 公网发布管控 | 源码不得公开在公网（含公开仓库、网盘、博客贴码） |
| AI 工具使用 | 注意 AI 工具的代码泄露风险；敏感项目不将核心代码发给不受控外部服务 |

风险：代码含业务逻辑接口、加解密方式、鉴权方式及未修复漏洞，公网暴露即攻击面。

## 二、配置泄露检查

| 检查项 | 要求 |
|---|---|
| 仓库不含重要配置 | 数据库密码、Api Key、存储密钥不进代码仓库，用环境变量替代 |
| 前端 | 使用 `.env.local` 本地变量文件（gitignore）；重要信息由后端接口返回 |
| 后端 | 配置放配置中心（如 Nacos）；数据库、ApiKey 等加密存储 |

AI 行为：**禁止**把密钥/密码写死进代码或提交；发现已泄露的密钥立即提示轮换，而非仅删除（git 历史仍在）。

## 三、安全漏洞（CVE）检查

要求：前后端定期做依赖组件漏洞扫描，**无中等风险以上漏洞**。

### 后端

```bash
# Maven 项目：OWASP dependency-check
mvn org.owasp:dependency-check-maven:check -DfailBuildOnCVSS=7

# 或 trivy（多语言通用，扫锁文件与镜像）
trivy fs --scanners vuln --severity HIGH,CRITICAL .

# JetBrains IDE 插件：MurphySec Code Scan（团队推荐）
```

### 前端

```bash
npm audit --audit-level=high        # 或 pnpm audit / yarn audit
npm audit fix                        # 自动修复可修复项
# VS Code 安全检查插件定期检查依赖组件
```

### AI 行为

- 升级依赖前先确认 CVE 受影响版本范围，避免为修 CVE 引入不兼容变更
- 发现 CRITICAL/HIGH 漏洞：提示升级路径；无法升级时给出缓解措施（如 WAF 规则、关闭暴露面）
- 扫描报告要求：无中等风险以上漏洞才算通过

## 四、检查清单（AI 会话结束时自查）

- [ ] 本次改动没有新增任何硬编码密钥/密码/内网地址
- [ ] 新增依赖没有引入 HIGH/CRITICAL CVE（用上述工具确认）
- [ ] .env / 配置文件没有加入 git（确认 .gitignore 覆盖）
- [ ] 没有把内网仓库代码推到公网仓库
