---
name: codeguard-php
description: |
  PHP 代码规范：php -l 语法门禁 + PHP-CS-Fixer PSR-12 自动修复 + PHPStan 静态分析。
  触发：用户说"PHP 规范"、"PSR-12"、"php-cs-fixer"、"phpstan"。
---

# PHP 代码规范

## 强制项（违反必须修复）

### 1. lint 命令

```bash
php -l <file>                                   # codeguard 钩子默认调用（语法门禁，零依赖）
vendor/bin/php-cs-fixer fix --dry-run           # 风格检查
vendor/bin/php-cs-fixer fix                     # 自动修复
vendor/bin/phpstan analyse                      # 静态分析（推荐另配）
```

### 2. PSR-12 基线

- 严格 `<?php` 开头标签；文件末尾不加 `?>`
- 缩进 4 空格；行宽软限 120
- 命名空间与目录一致：`App\Services\UserService` → `src/Services/UserService.php`
- 一個文件一個類

### 3. 命名

- 类：`UpperCamelCase`；方法/变量：`camelCase`
- 常量：`UPPER_SNAKE_CASE`（类常量）
- 接口不加 `Interface` 后缀（PSR conventions 建议按语义命名）

### 4. 类型声明（现代 PHP 必须）

```php
public function findUser(int $id): ?User
{
    ...
}
```

- 所有公共方法写参数类型 + 返回类型
- `declare(strict_types=1);` 放每个文件首行

### 5. 禁止使用

- `extract()`、`eval()`、`die()`（用 `exit`）
- 关闭错误 `@` 抑制符
- 裸 `echo` 混 HTML（模板引擎分离）

## 常见错误速查

| 工具/规则 | 修复 |
|---|---|
| `php -l` 语法错误 | 按行号修复；常见为缺分号/括号 |
| CS-Fixer `ordered_imports` | import 按字母序 |
| CS-Fixer `no_unused_imports` | 删除未使用 use |
| PHPStan Level 错误 | 从 level 0 起逐级修复类型缺口 |
