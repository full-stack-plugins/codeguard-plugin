# 受控修复与复验

用户：修复 Visual Basic .NET lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `dotnet format` → 审查 diff → 复跑 `dotnet format --verify-no-changes` → 跑受影响测试。
