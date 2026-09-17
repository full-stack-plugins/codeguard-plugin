---
name: codeguard-dockerfile
license: Apache-2.0
description: |
  Dockerfile 安全风险检查与规范门禁：hadolint 安全规则（root 运行、latest 标签、ADD 风险、
  sudo、包管理器缓存）+ trivy config misconfig 规则（digest 未固定、secrets 进镜像层、
  HEALTHCHECK 缺失）+ 安全基线（非 root 用户、多阶段构建、最小镜像）。
  Use when users write or review Dockerfiles, hit hadolint failures, ask about container
  security hardening, or before building/publishing images. Route dependency CVEs inside
  images to codeguard-security-code and base-image selection to trivy/scout reports.
---

# Dockerfile 安全风险检查

> 基于 [hadolint](https://github.com/hadolint/hadolint)（DL 规则）、[trivy config](https://trivy.dev/latest/docs/scanner/misconfig/)（misconfig 规则）与团队容器安全基线。

## Capability Boundaries

### ✅ Strengths
1. hadolint 双层门禁：lint 风格 + 安全规则（root/latest/ADD/sudo/端口/缓存）
2. trivy config misconfig：DS 系规则（root 运行、digest 未固定、secrets 进层、HEALTHCHECK）
3. 统一编排入口 `bin/codeguard dockerfile`（自动发现项目内全部 Dockerfile）
4. 修复指引随报告输出（每条 FAIL 附 Resolution）

### ⚠️ Prerequisites
1. `brew install hadolint`；trivy 可选（装了增加 misconfig 维度）

### ❌ Out of Scope
1. 镜像内依赖的 CVE（基础镜像/OS 包）→ `codeguard-security-code`（trivy fs/image CVE 维度）
2. 运行时安全（seccomp/AppArmor）→ 运维基线
3. Kubernetes YAML 加固 → 后续版本

## When to Use

- "Dockerfile 安全" / "镜像加固" / "hadolint" / "容器安全检查"
- AI 写/改 Dockerfile 后（PostToolUse 钩子按扩展名识别）
- 构建镜像前

## I. 安全风险清单（检查器覆盖 + 修复模板）

### 1. 以 root 运行（最高优先级）

```dockerfile
# ❌
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y curl
CMD ["app"]

# ✅ 专用非 root 用户
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser
USER appuser
CMD ["app"]
```

### 2. latest 标签 / 未固定版本（DL3007、可升级为 digest 固定）

```dockerfile
# ❌
FROM node:latest
# ✅ 固定具体版本（更强：@sha256: digest）
FROM node:20.18.0-alpine3.20
```

### 3. ADD 的隐式风险（DL3020）

`ADD` 会自动解压远程 tar 并支持 URL——**复制本地文件一律用 `COPY`**：

```dockerfile
# ❌ ADD app.tar.gz /app/       # 自动解压 + 可拉远程 URL（攻击面）
# ✅ COPY app.tar.gz /app/
```

### 4. sudo（DL3004）

容器内禁止 `sudo`（镜像构建期本就是 root，运行期应切换 USER）。

### 5. 包管理器缓存与 --no-install-recommends（DL3005/3008/3015）

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
```

### 6. secrets 进镜像层

- ❌ `ENV API_KEY=sk-xxx`、`COPY .env`、`ARG PASSWORD`（层缓存可被 `docker history` 还原）
- ✅ 运行时注入（环境变量 / secret 挂载 / BuildKit `--secret`）

### 7. HEALTHCHECK 缺失

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fs http://localhost:8080/healthz || exit 1
```

### 8. EXPOSE 与端口

只暴露应用实际监听端口；EXPOSE 是文档声明，真正的暴露由运行时 `-p` 决定。

## II. 多阶段构建（减小攻击面）

```dockerfile
FROM node:20.18.0-alpine3.20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20.18.0-alpine3.20
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
USER node
HEALTHCHECK CMD wget -qO- http://localhost:3000/healthz || exit 1
CMD ["node", "dist/main.js"]
```

要点：最终阶段不含构建工具/源码/dev 依赖；`.dockerignore` 排除 `.git`、`node_modules`、`*.env`。

## III. trivy config misconfig 规则（DS 系速查）

| 规则 | 含义 |
|---|---|
| DS001 | 未声明 USER（默认 root） |
| DS002 | 镜像 tag 为 latest 或空 |
| DS005 | ADD 而非 COPY |
| DS026 | HEALTHCHECK 缺失 |
| AVD-DS-0002 | 敏感数据进 ADD/COPY 层 |

## Workflow

1. `bin/codeguard dockerfile` 扫描全部 Dockerfile
2. hadolint 发现按「安全规则 → 风格规则」顺序修复
3. trivy FAIL 逐条按 Resolution 修复
4. 修复后复扫至零发现
5. 提交前由 pre-commit `hadolint` hook 再拦一次

## Gotchas

1. hadolint 的 DL3008/3013（apt/pip 版本锁定）团队约定不启用——基础镜像更新会破坏构建；其余 DL 规则不豁免
2. `docker history` 可还原任何镜像层内容——构建期注入的 secrets 一样泄漏，必须运行时注入
3. `ALWAYS` 类 apt 安装建议加 `--no-install-recommends`，镜像体积与 CVE 面同时缩小
4. 多阶段构建的最终阶段也要声明 USER——只在前一阶段切用户无效
5. `.dockerignore` 缺失会让 `.git`、`.env` 被 COPY 进上下文——与 Dockerfile 同等重要

## On-Demand Resources

- [Dockerfile 安全规则对照（hadolint DL ↔ trivy DS ↔ 修复模板）](references/dockerfile-security-rules.md)
- [.hadolint.yaml 模板](../../linters/dockerfile/.hadolint.yaml) · [多阶段构建完整示例](../../README.md#quick-start)

## Official References

- [hadolint](https://github.com/hadolint/hadolint) · [trivy misconfig](https://trivy.dev/latest/docs/scanner/misconfig/) · [Docker 安全官方指南](https://docs.docker.com/develop/security-best-practices/)
