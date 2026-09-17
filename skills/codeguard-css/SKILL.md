---
name: codeguard-css
license: Apache-2.0
description: |
  CSS / SCSS / Sass / LESS 规范：stylelint recommended + 自动修复。
  Use when users write or review .css/.scss/.less files, hit stylelint errors, or ask
  about CSS conventions. Route framework-specific styling (Tailwind/Modules) to their docs.
---

# CSS / SCSS 代码规范门禁

> 基于 [stylelint](https://stylelint.io/) + `stylelint-config-standard`。配置模板：`linters/css/stylelint.config.js`。

## Capability Boundaries

### ✅ Strengths
1. stylelint recommended 全规则（缩进/色值/属性顺序/空行）
2. `--fix` 自动修复（大部分规则 MachineApplicable）
3. 覆盖 CSS / SCSS / Sass / LESS

### ⚠️ Prerequisites
1. Node.js；项目 devDeps 安装 `stylelint stylelint-config-standard`

### ❌ Out of Scope
1. 样式视觉效果评审 → 设计侧
2. Tailwind class 顺序 → tailwindcss-intellisense / prettier-plugin-tailwindcss

## When to Use

- "css 规范" / "stylelint" / "样式检查"

## I. 强制项

```bash
npx stylelint "**/*.css"          # 门禁（codelint 钩子默认）
npx stylelint "**/*.css" --fix    # 自动修复
```

配置基线（见 `linters/css/stylelint.config.js`）：
- 缩进 2 空格、行宽 120
- `no-unused-vars` / `no-duplicate-properties` / `block-no-empty`
- `selector-class-pattern` 默认关闭（交给团队 BEM/模块化约定）

## II. 高频规则速查

| 规则 | 修复 |
|---|---|
| `color-hex-length` | `#ffffff` → `#fff` |
| `declaration-block-no-duplicate-properties` | 合并重复属性 |
| `function-comma-space-after` | `fn(a,b)` → `fn(a, b)` |
| `length-zero-no-unit` | `0px` → `0` |
| `shorthand-property-no-redundant-values` | `margin: 1px 1px` → `margin: 1px` |

## Workflow

1. `npx stylelint "**/*.css"` 扫描
2. `--fix` 自动修复
3. 复扫至零输出

## Gotchas

1. `stylelint-config-standard` 对 SCSS 需额外 `stylelint-config-standard-scss`
2. `no-descending-specificity` 对组件化样式常误报 —— 按需关闭并注明原因
3. 与 Prettier 同时使用时用 `stylelint-config-prettier` 避免格式冲突
