# 受控修复与复验

用户：修复 Dart / Flutter lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `dart format .` → 审查 diff → 复跑 `dart analyze` → 跑受影响测试。
