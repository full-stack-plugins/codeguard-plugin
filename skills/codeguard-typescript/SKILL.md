---
name: codeguard-typescript
description: |
  TypeScript / JavaScript 代码规范：ESLint recommended + Prettier 一致格式化。
  触发：用户说"eslint"、"ts 规范"、"prettier"、"lint"。
---

# TypeScript / JavaScript 代码规范

## 强制项（违反必须修复）

### 1. ESLint recommended

```bash
npx eslint . --max-warnings 0
```

必须 0 warning。常用规则：

| 规则 | 行为 |
|---|---|
| `no-unused-vars` | error（参数/变量未使用报错） |
| `prefer-const` | error（let 应改为 const） |
| `eqeqeq` | error（`==` 改 `===`） |
| `no-undef` | error（使用未声明的变量） |
| `no-var` | error（必须用 let/const） |
| `no-console` | warn（除 warn/error/info 外禁止 console） |

### 2. TypeScript strict

`tsconfig.json` 必须开启：
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true
  }
}
```

### 3. 命名

- 类/类型/枚举：`UpperCamelCase`（`UserService`）
- 函数/变量：`lowerCamelCase`
- 常量：`UPPER_SNAKE_CASE`（仅当 `const` 且永不变更时）
- 文件名：kebab-case（`user-service.ts`）或 camelCase（团队约定）

### 4. Import 顺序

```
// 1. Node 内置
import { readFileSync } from 'fs';

// 2. 第三方
import express from 'express';

// 3. 本项目（按字母序）
import { UserService } from './user-service';
```

### 5. 不要使用

- `any`（除非明确注释说明原因）
- `@ts-ignore`（用 `@ts-expect-error` 并说明）
- `as unknown as X` 双重断言
- `eval()`、`new Function()`
- `console.log` 在生产代码（仅 dev/warn/error 可用）

## 自动修复

```bash
npx eslint . --fix          # 自动修复可修复的问题
npx prettier --write .      # 格式化（如果项目同时使用 prettier）
```

## 常见错误速查

| ESLint 报错 | 修复 |
|---|---|
| `no-unused-vars` | 删除未使用变量，或前缀加 `_`（`no-unused-vars` 配置 `varsIgnorePattern: "^_"`） |
| `prefer-const` | `let x = 5;` → `const x = 5;` |
| `eqeqeq` | `a == b` → `a === b` |
| `@typescript-eslint/no-explicit-any` | 替换为具体类型或 `unknown` |
| `import/order` | 调整 import 顺序 |
