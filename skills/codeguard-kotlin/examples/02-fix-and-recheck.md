# 受控修复与复验

用户：修复 Kotlin lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `./gradlew ktlintFormat` → 审查 diff → 复跑 `./gradlew detekt` → 跑受影响测试。
