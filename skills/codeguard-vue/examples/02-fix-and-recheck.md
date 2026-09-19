# 受控修复与复验

用户：修复 Vue lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `npx eslint --ext .vue . --fix` → 审查 diff → 复跑 `npx --no-install eslint --ext .vue .` → 跑受影响测试。
