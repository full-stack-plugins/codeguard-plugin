---
name: codeguard-cve
license: Apache-2.0
description: |
  codeguard cve 命令：多生态 CVE 依赖漏洞扫描编排（Maven dependency-check / npm audit /
  pip-audit / cargo audit），失败阈值可调，npm 支持自动修复。Use when users say
  "扫漏洞", "CVE", "依赖安全检查", or before release. Route Dockerfile misconfig to
  codeguard-dockerfile; suppression policy to codeguard-security-code.
---

# codeguard cve

## Capability Boundaries

### ✅ Strengths
1. 自动检测生态，编排对应扫描工具
2. 阈值门禁（`--severity MEDIUM/HIGH/CRITICAL`）
3. `--fix` 自动修复（npm audit fix）；其余生态输出修复指引
4. 三态退出码：0=通过 / 1=无法验证（工具缺失）/ 2=发现漏洞

### ⚠️ Prerequisites
1. Maven：mvn + 网络（首跑下载 NVD 库，建议申请 NVD_API_KEY）
2. Node：npm + package-lock.json
3. Python：pip-audit（`pip install pip-audit`）
4. Rust：cargo-audit（`cargo install cargo-audit`）

### ❌ Out of Scope
1. 镜像内 OS 包 CVE → trivy image（可后续接入）
2. Dockerfile misconfig → codeguard-dockerfile
3. 豁免策略制定 → codeguard-security-code

## 命令

```bash
bin/codeguard cve                          # 全生态扫描
bin/codeguard cve --ecosystem node         # 只扫 node
bin/codeguard cve --fix                    # 扫描 + 自动修复 + 复扫
bin/codeguard cve --severity MEDIUM        # 门禁阈值调到中危（发版前）
bin/codeguard cve --json path/             # 结构化输出
```

## 三态语义（门禁必须遵守）

| 退出码 | 含义 | 门禁动作 |
|---|---|---|
| 0 | 全部通过 | 允许提交 |
| 1 | 无法验证（工具缺失/超时） | **不视为通过**——先装工具 |
| 2 | 发现漏洞 | 必须修复（升级/替换/登记缓解），禁止只报告不处理 |

## Workflow

1. 扫描：`bin/codeguard cve`
2. 有发现 → 读报告定位受影响包与引入路径（`mvn dependency:tree` / `npm ls`）
3. 修复：优先升级版本；无法升级给出缓解措施（WAF/关闭暴露面）并登记注销日期
4. 复扫至零 HIGH/CRITICAL
5. 提交前再跑一次确认
