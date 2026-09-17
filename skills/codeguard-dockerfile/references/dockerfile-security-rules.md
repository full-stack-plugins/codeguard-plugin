# Dockerfile 安全规则对照（hadolint DL ↔ trivy DS ↔ 修复模板）

> codeguard-dockerfile 技能的渐进披露资料。按风险主题归类，供逐条修复时查阅。

## 1. 权限类

| 规则 | 主题 | 修复模板 |
|---|---|---|
| DL3002 | 最后一个 USER 不能是 root | 显式 `USER appuser`（UID ≥ 10000 更佳） |
| DS001 | 未声明 USER | 同上 |
| DL3004 | 禁止 sudo | 构建期直接用 root 装依赖，运行期切换非 root |

## 2. 镜像引用类

| 规则 | 主题 | 修复模板 |
|---|---|---|
| DL3006 | 镜像 tag 缺失 | `FROM alpine:3.20` |
| DL3007 | latest 标签 | 固定具体版本号；更强用 `@sha256:digest` |
| DS002 | 同上（trivy 维度） | 同上 |

## 3. 文件与包类

| 规则 | 主题 | 修复模板 |
|---|---|---|
| DL3020 | 用 ADD 复制文件 | 改 `COPY`（ADD 仅用于需要自动解压本地 tar 的场景） |
| DL3015 | apt 未加 --no-install-recommends | 追加参数缩小体积与 CVE 面 |
| DL3008 | apt 未固定包版本 | 团队约定豁免（见 .hadolint.yaml ignored） |
| DL3013 | pip 未固定版本 | 同上豁免 |
| DL3015/3009 组合 | 装完不清理 | `&& rm -rf /var/lib/apt/lists/*` |
| DS0004/DS0005 | 层内残留 secrets / 凭据 | 运行时注入（BuildKit `--secret`、挂载），并重写历史已泄漏镜像 |

## 4. 健康与运维类

| 规则 | 主题 | 修复模板 |
|---|---|---|
| DS026 | HEALTHCHECK 缺失 | `HEALTHCHECK --interval=30s CMD curl -fs http://localhost:8080/healthz \|\| exit 1` |
| DL3016 | EXPOSE 端口与协议 | 声明实际监听端口 |
| DL3025 | `\$VAR` 注入风险 | 转义或改用 ENTRYPOINT exec 形式 |

## 5. 通用最佳实践

| 规则 | 主题 |
|---|---|
| DL3038/DL3047 | apt-get/yum 应连用 update+install，减少层与不一致 |
| DL3059 | 连续 RUN 可合并（减少层数） |
| DL3045 | `WORKDIR` 先于 `COPY`，避免路径歧义 |

## 6. 最小镜像速查

| 基础镜像 | 体积 | 适用 |
|---|---|---|
| `alpine:3.20` | ~7MB | 静态二进制 / Node（注意 musl 兼容） |
| `distroless` | ~20MB | 仅运行时（无 shell，最安全） |
| `debian:bookworm-slim` | ~75MB | 需要 glibc 与包管理器的场景 |

## 7. .dockerignore 基线

```text
.git
.env*
node_modules
dist
build
tests
*.md
Dockerfile*
docker-compose*
```
