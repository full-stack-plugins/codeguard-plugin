# 只读检测与检查

用户：检查这个 C++ 项目，但先不要修改。

执行：确认根目录和配置 → 探测工具 → 运行 `bash -c 'find . \( -name '"'"'*.cpp'"'"' -o -name '"'"'*.hpp'"'"' -o -name '"'"'*.cc'"'"' \) -type f -print0 | xargs -0 -r clang-tidy --quiet'`。

输出必须包含范围、工具版本、退出码和 PASS/FAIL/UNVERIFIED/PLANNED。
