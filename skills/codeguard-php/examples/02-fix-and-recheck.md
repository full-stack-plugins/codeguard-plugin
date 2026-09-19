# 受控修复与复验

用户：修复 PHP lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `php-cs-fixer fix` → 审查 diff → 复跑 `bash -c 'find . -name '"'"'*.php'"'"' -type f -not -path '"'"'*/vendor/*'"'"' -print0 | xargs -0 -n1 php -l'` → 跑受影响测试。
