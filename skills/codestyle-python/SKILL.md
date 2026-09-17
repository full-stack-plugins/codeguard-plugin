---
name: codestyle-python
description: |
  Python 代码规范：ruff（极速，drop-in 替代 flake8 + isort + pyupgrade + flake8-bugbear）。
  触发：用户说"ruff"、"python 规范"、"flake8"、"lint"。
---

# Python 代码规范

## 推荐工具：ruff（替代 flake8/isort/black）

```bash
pip install ruff

# 检查
ruff check .

# 自动修复
ruff check --fix .

# 格式化
ruff format .
```

**优势**：比 flake8 快 10-100x，单二进制，零依赖。

## 推荐规则集

```toml
# pyproject.toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort（import 排序）
    "B",    # flake8-bugbear（常见 bug）
    "C4",   # flake8-comprehensions（推导式）
    "UP",   # pyupgrade（现代化语法）
    "N",    # pep8-naming
    "SIM",  # flake8-simplify
    "RUF",  # ruff 自身规则
]
ignore = [
    "E501",  # line-too-long（与 line-length 一致即可）
    "B008",  # function call in default argument（pydantic 常用）
]
```

## 强制项

- **类型注解**：公共函数必须有参数和返回类型注解（Python 3.10+ 可用 PEP 604 `|`）
- **docstring**：公共函数 / 类必须有 docstring（Google 风格）
- **命名**：
  - 函数/变量：`snake_case`
  - 类：`UpperCamelCase`
  - 常量：`UPPER_SNAKE_CASE`
  - 私有：前缀 `_`（`_internal_helper`）
- **import 顺序**：stdlib / 第三方 / 本项目（ruff I 规则自动处理）
- **不要使用**：
  - `from foo import *`
  - `except:`（裸捕获，必须指定异常类型）
  - `print()` 在生产代码（用 `logging` 模块）
  - 全局可变状态（除非必要）

## 示例

```python
from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict[str, str]:
    """读取配置文件。

    Args:
        path: 配置文件路径。

    Returns:
        解析后的配置字典。

    Raises:
        FileNotFoundError: 当 path 不存在时。
    """
    if not path.exists():
        logger.error("config not found: %s", path)
        raise FileNotFoundError(f"missing config: {path}")
    return {"key": "value"}
```

## 常见 ruff 规则

| 规则代码 | 含义 | 修复 |
|---|---|---|
| `E501` | line-too-long | 换行或调宽 line-length |
| `F401` | imported but unused | 删除未使用 import |
| `I001` | import 顺序错 | `ruff check --fix` 自动排序 |
| `B006` | mutable default argument | 改 `None` + 函数内初始化 |
| `UP015` | unnecessary `open(... encoding=...)` 显式 encoding | 删除显式 encoding |
