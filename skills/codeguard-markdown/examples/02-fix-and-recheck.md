# 受控修复与复验

用户：修复 Markdown lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `markdownlint-cli2 --fix` → 审查 diff → 复跑 `npx --no-install markdownlint-cli2` → 跑受影响测试。
