---
name: codeguard-cve
license: Apache-2.0
description: 编排 Maven、Node、Python 和 Rust 依赖的 CVE 扫描与门禁；当用户要求扫漏洞、依赖安全检查、发布前审查、解释 HIGH/CRITICAL 发现或设计抑制策略时使用。必须保留工具、阈值、依赖路径与复扫证据。
compatibility: 需要目标生态的锁文件、扫描工具及可用漏洞数据源；默认不升级依赖、不自动接受抑制。
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

## 不适用范围（什么时候不该用）

- 问题是容器基础镜像或操作系统包，而当前 Codeguard 还没有该 scanner 证据。
- 问题是源码密钥泄露、鉴权或数据安全；应转交对应安全技能。
- 没有 lockfile/依赖元数据却要求证明不存在漏洞。

## 数据与安全

依赖名、版本和锁文件可能被扫描工具发送到外部漏洞数据源。执行前需说明网络边界，不上传源码、凭据或私有包内容。报告不得回显 token/NVD key；本技能不会自动创建抑制或升级依赖。

## 证据化 Workflow

### Step 1：确定生态和范围

找到 lockfile、构建文件、workspace 边界和生产/dev/test 依赖分类。

### Step 2：探测扫描器

记录 scanner 版本、漏洞数据库时间和门禁阈值。数据源不可用时状态为 `UNVERIFIED`。

### Step 3：执行只读扫描

优先 `bin/codeguard cve --json <path>` 保存结构化证据，不在首次扫描时带 `--fix`。

### Step 4：确认可利用性与引入路径

核对 CVE/GHSA、受影响版本、已修复版本、直接/传递依赖与项目是否使用受影响功能。

### Step 5：选择处置

优先最小兼容升级，其次替换组件或关闭暴露面。抑制必须有误报依据、责任人和到期日。

### Step 6：回归测试

依赖改动后执行锁文件差异审查、编译、单测、集成测试和关键兼容性检查。

### Step 7：使用原阈值复扫

不能通过调高阈值把发现“修复”掉。报告必须列出已修复、已缓解、已抑制和尚未解决项。

## Rules

1. 无法访问漏洞数据源不等于零漏洞。
2. 不盲目运行 `npm audit fix --force` 或全量 latest 升级。
3. 不只复制 scanner 标题；必须确认依赖路径和可用修复版本。
4. 缓解不等于修复，必须写明残余风险与追踪日期。
5. 报告必须记录扫描日期和数据库新鲜度。

## 输出模板

```text
Codeguard CVE 结果
- 范围/生态：<workspace and lockfiles>
- 扫描器：<name/version/db timestamp>
- 阈值：<severity policy>
- 状态：PASS / FAIL / UNVERIFIED
- 发现：<CVE, dependency path, affected/fixed range>
- 处置：<upgrade/replace/mitigate/suppress with evidence>
- 回归：<build/test evidence>
- 复扫：<command and exit>
```

## Gotchas

1. **锁文件缺失**：基于声明版本的扫描可与真实解析版本不同。
2. **NVD/registry 限流**：首跑下载失败是 UNVERIFIED，不是 PASS。
3. **dev dependency 也可到达生产**：构建链供应链风险不能仅凭“非运行时”忽略。
4. **修复版本可破坏 API**：需根据 semver、changelog 和回归证据判断。
5. **同一漏洞多路径引入**：只升级一条直接依赖可能仍然残留传递路径。
6. **抑制会过期**：已抑制项需要到期日和重验条件。

## 按需加载资源

- 选择 scanner 和阈值时读取 `references/rules/scanner-matrix.md`。
- 设计修复/抑制证据时读取 `references/operations/remediation-playbook.md`。
- 只读取 `examples/` 中与当前生态或失败模式匹配的示例。
