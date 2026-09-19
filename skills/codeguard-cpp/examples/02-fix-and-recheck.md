# 受控修复与复验

用户：修复 C++ lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `clang-format -i '{file}'` → 审查 diff → 复跑 `bash -c 'find . \( -name '"'"'*.cpp'"'"' -o -name '"'"'*.hpp'"'"' -o -name '"'"'*.cc'"'"' \) -type f -print0 | xargs -0 -r clang-tidy --quiet'` → 跑受影响测试。
