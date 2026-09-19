# 受控修复与复验

用户：修复 SQL lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `sqlfluff fix` → 审查 diff → 复跑 `bash -c 'find . -name '"'"'*.sql'"'"' -type f -not -path '"'"'*/node_modules/*'"'"' -print0 | xargs -0 -r sqlfluff lint'` → 跑受影响测试。
