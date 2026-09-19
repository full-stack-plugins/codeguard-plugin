# 只读检测与检查

用户：检查这个 SQL 项目，但先不要修改。

执行：确认根目录和配置 → 探测工具 → 运行 `bash -c 'find . -name '"'"'*.sql'"'"' -type f -not -path '"'"'*/node_modules/*'"'"' -print0 | xargs -0 -r sqlfluff lint'`。

输出必须包含范围、工具版本、退出码和 PASS/FAIL/UNVERIFIED/PLANNED。
