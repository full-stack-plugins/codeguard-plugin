# 只读检测与检查

用户：检查这个 PHP 项目，但先不要修改。

执行：确认根目录和配置 → 探测工具 → 运行 `bash -c 'find . -name '"'"'*.php'"'"' -type f -not -path '"'"'*/vendor/*'"'"' -print0 | xargs -0 -n1 php -l'`。

输出必须包含范围、工具版本、退出码和 PASS/FAIL/UNVERIFIED/PLANNED。
