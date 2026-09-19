# 受控修复与复验

用户：修复 PowerShell lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `pwsh -NoProfile -Command Invoke-Formatter` → 审查 diff → 复跑 `pwsh -NoProfile -Command 'Invoke-ScriptAnalyzer -Path . -Severity Error'` → 跑受影响测试。
