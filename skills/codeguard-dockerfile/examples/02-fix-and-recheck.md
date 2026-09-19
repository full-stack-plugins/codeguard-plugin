# 受控修复与复验

用户：修复 Dockerfile lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `hadolint` → 审查 diff → 复跑 `bash -c 'find . \( -name '"'"'Dockerfile'"'"' -o -name '"'"'Dockerfile.*'"'"' -o -name '"'"'Containerfile'"'"' \) -type f -not -path '"'"'*/node_modules/*'"'"' -print0 | xargs -0 -r hadolint'` → 跑受影响测试。
