# 只读检测与检查

用户：检查这个 Dockerfile 项目，但先不要修改。

执行：确认根目录和配置 → 探测工具 → 运行 `bash -c 'find . \( -name '"'"'Dockerfile'"'"' -o -name '"'"'Dockerfile.*'"'"' -o -name '"'"'Containerfile'"'"' \) -type f -not -path '"'"'*/node_modules/*'"'"' -print0 | xargs -0 -r hadolint'`。

输出必须包含范围、工具版本、退出码和 PASS/FAIL/UNVERIFIED/PLANNED。
