# 受控修复与复验

用户：修复 Nix lint，但不要改变业务逻辑。

执行：先保存失败证据 → 仅对格式类问题运行 `nixpkgs-fmt '{file}'` → 审查 diff → 复跑 `bash -c 'find . -name '"'"'*.nix'"'"' -type f -print0 | xargs -0 -r deadnix'` → 跑受影响测试。
