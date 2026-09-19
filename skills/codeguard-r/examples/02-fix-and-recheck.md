# 受控修复与复验

用户：修复 R lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `styler :: style_dir` → 审查 diff → 复跑 `Rscript -e 'lintr::lint_dir('"'"'.'"'"')'` → 跑受影响测试。
