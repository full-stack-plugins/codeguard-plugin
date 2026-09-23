"""用户配置旧导入面的兼容导出；实现仅在 codeguard.config。

Deprecated：此模块是旧导入面的兼容外观，新代码必须从 `codeguard.config` 导入；
计划在下一个 major 版本移除。
"""
from codeguard.config import (
    ConfigurationError,
    get_overrides,
    load_project_overrides,
    load_user_config,
)

__all__ = ["ConfigurationError", "get_overrides", "load_project_overrides", "load_user_config"]
