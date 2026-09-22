## Context

- `hooks/env_check.py::detect_linter_config`（M8 后）：`for lang_id, lang_def in REGISTRY.items(): files = lang_def.get("linter_config_files") or []` → 存在性过滤 → `{lang: [files]}`。**填错无害**（不存在的文件名永远不命中），这是本 change 敢于「保守估计 + 宽清单」的依据。
- 现状覆盖：java / rust / typescript / python 四条（M8 迁移自旧硬编码常量）。
- 关键区分（M8 design 遗留）：`requiresConfig` **不等于** linter 配置——java 的 `requiresConfig` 是 `pom.xml` 等项目文件（gate 判定「项目是否接入」用），**不是** linter 配置文件；直接把 requiresConfig 拷进 linter_config_files 会造成误报（SessionStart 会说「linter 配置：pom.xml」）。只有 requiresConfig 本身就是 linter 配置的条目（yaml 的 `.yamllint*`、markdown 的 `.markdownlint*`、scala 的 `.scalafmt.conf`、erlang 的 `elvis.config*`、protobuf 的 `buf.yaml`、vue/svelte/astro 的 eslint 系）可直接复制。

## Decisions

### 保守清单（只填确定存在的标准配置名）

按语言分组（~30 条）：

- go: `.golangci.yml`, `.golangci.yaml`
- shell: `.shellcheckrc`
- dockerfile: `.hadolint.yaml`, `.hadolint.yml`
- yaml: `.yamllint`, `.yamllint.yaml`, `.yamllint.yml`（requiresConfig 即 linter 配置，直接复制）
- markdown: `.markdownlint-cli2.*` / `.markdownlint.*` 九件套（同上复制）
- vue / svelte / astro: eslint 系（requiresConfig 直接复制）
- ruby: `.rubocop.yml`, `.rubocop.yaml`
- php: `phpstan.neon`, `phpstan.neon.dist`, `psalm.xml`
- swift: `.swiftlint.yml`, `.swiftlint.yaml`
- kotlin: `detekt.yml`, `detekt.yaml`
- dart: `analysis_options.yaml`
- elixir: `.credo.exs`
- c / cpp / objc / cuda: `.clang-tidy`, `.clang-format`
- css: `.stylelintrc`, `.stylelintrc.json`, `.stylelintrc.yml`, `stylelint.config.js`
- html: `.htmlhintrc`
- terraform: `.tflint.hcl`, `tflint.hcl`
- sql: `.sqlfluff`
- haskell: `.hlint.yaml`, `.hlint.yml`
- ocaml: `.ocamlformat`
- perl: `.perlcriticrc`
- clojure: `.clj-kondo/config.edn`
- powershell: `PSScriptAnalyzerSettings.psd1`
- crystal: `.ameba.yml`
- lua: `.luacheckrc`
- r: `.lintr`
- ansible: `.ansible-lint`
- solidity: `.solhint.json`, `.solhintrc`
- scala: `.scalafmt.conf`（requiresConfig 复制）
- erlang: `elvis.config`, `elvis.config.js`（requiresConfig 复制）
- protobuf: `buf.yaml`, `buf.gen.yaml`, `buf.work.yaml`（requiresConfig 复制）

**明确不填**（低置信或无标准配置名）：graphql、toml、zig、nim、julia、pascal、liquid、luau、nix、groovy、cfml、fsharp、vbnet、csharp、elm、objc→已填 clang、cfml 等——留空数组是诚实状态。

### 守护测试

`test_linter_config_files_coverage`：stable/beta 中非空 `linter_config_files` 数量 ≥ 25（当前应 ~34）。防止未来语言注册表重构静默清空填充。

### 不动 requiresConfig 语义

两条字段语义分离是 M8 的设计决定，本 change 遵守：requiresConfig 服务 gate 判定，linter_config_files 服务 SessionStart 盘点。

## Risks / Trade-offs

- 个别配置名猜错 → 该文件不存在 → 盘点不报 → 无副作用。
- 个别语言存在更流行的配置名（如 graphql 的 `.graphqlrc`）→ 未填 → 盘点少报一项 → 未来按需补，本 change 不冒进。