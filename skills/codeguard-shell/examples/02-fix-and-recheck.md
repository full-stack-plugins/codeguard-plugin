# 受控修复与复验

用户：修复 Shell lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `shfmt -w .` → 审查 diff → 复跑 `bash -c 'find . \( -name '"'"'*.sh'"'"' -o -name '"'"'*.bash'"'"' -o -name '"'"'*.zsh'"'"' \) -type f -not -path '"'"'*/node_modules/*'"'"' -print0 | xargs -0 shellcheck --severity=warning'` → 跑受影响测试。
