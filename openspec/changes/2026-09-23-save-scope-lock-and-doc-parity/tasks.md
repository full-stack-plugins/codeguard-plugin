# Tasks: 2026-09-23-save-scope-lock-and-doc-parity

## 1. 豁免值语义与文案

- [x] 1.1 `repository_policy.env_skip_gate()` 单一解析器（只认 1/true/yes）
- [x] 1.2 两个钩子调用点接入（pre_tool_git_guard / user_prompt_validator）
- [x] 1.3 `gate_directive` 文案改为与行为一致（内联赋值不传入钩子 + 准确值词表）

## 2. save 范围锁定测试

- [x] 2.1 scan token 收束单文件
- [x] 2.2 `{file}` 替换形态
- [x] 2.3 裸命令追加形态
- [x] 2.4 越界触碰显式告警（touched_others 集成）

## 3. 文档可执行断言测试

- [x] 3.1 绕过值词表（文案 ↔ 解析器）
- [x] 3.2 生态标识与别名（bin 用法 ↔ canonical_ecosystem）
- [x] 3.3 点前缀语义（AGENTS.md ↔ is_dot_prefixed）
- [x] 3.4 markdown probe 形态（文档 ↔ languages.json）
- [x] 3.5 CVE 退出码契约（README/bin ↔ EXIT_*）

## 4. 发版

- [x] 4.1 全量回归 + ruff 干净 + openspec strict
- [x] 4.2 dogfood 发 v0.15.4 + PR/CI/合并 + 两仓推送
