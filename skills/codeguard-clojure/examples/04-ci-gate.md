# CI 门禁对齐

用户：本地已经通过，为什么 CI 仍失败？

对比本地与 CI 的工具版本、工作目录、配置、环境变量、扫描范围和实际命令；使用 CI 的 `clj-kondo --lint src` 形状复现，并分别报告 lint、test、build 证据。
