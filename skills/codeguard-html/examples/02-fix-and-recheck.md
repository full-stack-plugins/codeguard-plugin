# 受控修复与复验

用户：修复 HTML lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `prettier --write` → 审查 diff → 复跑 `bash -c 'find . \( -name '"'"'*.html'"'"' -o -name '"'"'*.htm'"'"' \) -type f -not -path '"'"'*/node_modules/*'"'"' -exec grep -L '"'"'<%'"'"' {} + | xargs -0 -r npx --no-install htmlhint'` → 跑受影响测试。
