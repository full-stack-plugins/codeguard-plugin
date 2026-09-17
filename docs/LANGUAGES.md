# partme-codelint 支持的语言

> 与 [codegraph supported-languages](https://github.com/colbymchenry/codegraph#supported-languages) 的 32 种语言完全对齐。
> 状态说明：**Stable** = 默认启用，随会话钩子自动 lint；**Beta** = V0.2 起启用，linter 需按安装说明准备；**Planned** = 已识别扩展名，linter 集成在路线图上（钩子检测到后安全跳过）。

## Stable（V0.1 起，4 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 |
|---|---|---|---|
| Java | `.java` | `mvn -q javadoc:jar -DskipTests` | `mvn -q spotless:apply` |
| Rust | `.rs` | `cargo clippy --all-targets -- -D warnings` | `cargo fmt` |
| TypeScript / JavaScript | `.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` | `npx eslint . --max-warnings 0` | `npx eslint . --fix` |
| Python | `.py` | `ruff check .` | `ruff check . --fix` |

## Beta（V0.2 起，7 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 | 安装说明 |
|---|---|---|---|---|
| Go | `.go` | `go vet ./...` | `gofmt -w .` | 内置于 Go 工具链；聚合 lint 可装 golangci-lint |
| C# | `.cs` | `dotnet format --verify-no-changes` | `dotnet format` | .NET SDK 6+ |
| Kotlin | `.kt` `.kts` | `./gradlew detekt` | `./gradlew ktlintFormat` | 项目需配置 detekt / ktlint 插件 |
| Swift | `.swift` | `swiftlint` | `swiftlint --fix` | `brew install swiftlint` |
| PHP | `.php` | `php -l` | `php-cs-fixer fix` | `composer require --dev php-cs-fixer` |
| Ruby | `.rb` | `rubocop` | `rubocop -A` | `gem install rubocop` |
| Scala | `.scala` `.sc` | `scalafmt --check` | `scalafmt` | `coursier install scalafmt` |

## Planned（扩展名已识别，linter 集成在路线图上，21 种）

| 语言 | 扩展名 | 计划 Linter | 目标版本 |
|---|---|---|---|
| C | `.c` `.h` | clang-tidy + clang-format | V0.4 |
| C++ | `.cpp` `.hpp` `.cc` | clang-tidy + clang-format | V0.4 |
| Objective-C | `.m` `.mm` | clang-tidy + clang-format | V0.4 |
| Dart / Flutter | `.dart` | `dart analyze` + `dart format` | V0.4 |
| Vue | `.vue` | eslint-plugin-vue | V0.4 |
| Svelte | `.svelte` | eslint-plugin-svelte | V0.4 |
| Astro | `.astro` | eslint-plugin-astro | V0.4 |
| Solidity | `.sol` | solhint | V0.4 |
| Terraform / OpenTofu | `.tf` `.tfvars` `.tofu` | tflint + terraform fmt | V0.4 |
| Nix | `.nix` | nixpkgs-fmt + deadnix | V0.4 |
| Lua | `.lua` | luacheck + stylua | V0.5 |
| Luau | `.luau` | luau-lint + stylua | V0.5 |
| Ruby（CFML 之外的企业线） | — | — | — |
| ColdFusion (CFML) | `.cfc` `.cfm` `.cfs` | CFLint | V0.5 |
| COBOL | `.cbl` `.cob` `.cpy` | cobol-check | V0.5 |
| Visual Basic .NET | `.vb` | dotnet format | V0.4（随 C# 通道） |
| Erlang | `.erl` `.hrl` | dialyzer + elvis | V0.5 |
| Pascal / Delphi | `.pas` `.dpr` `.dpk` `.lpr` | pasfmt | V0.5 |
| R | `.R` `.r` | lintr | V0.5 |
| ArkTS (HarmonyOS) | `.ets` | ArkTS Linter | V0.5 |
| Metal | `.metal` | metal-lint | V0.5 |
| Liquid (Shopify) | `.liquid` | theme-check | V0.5 |
| CUDA | `.cu` `.cuh` | clang-tidy (CUDA) | V0.5 |

> 说明：Planned 列表共 21 个条目（含与 Stable/Beta 共用工具链的条目）。Planned 状态语言的文件会被 `detect_lang` 识别为代码文件，但钩子不会对它跑 linter（`LANG_COMMANDS` 无条目时安全跳过），不会阻塞 AI。

## 检测机制

1. **文件级**：`scripts/detect_lang.py` 的 `EXT_LANG_MAP` 覆盖上表全部扩展名 → PostToolUse 钩子按文件判断语言。
2. **项目级**：`PROJECT_MARKERS` 识别 `pom.xml` / `go.mod` / `Cargo.toml` / `package.json` / `pyproject.toml` / `composer.json` / `Gemfile` / `build.sbt` / `Package.swift` 等标记文件 → SessionStart 钩子据此注入项目语言清单。
3. **未列入命令表的语言**：安全跳过，不报错、不阻塞。

## 新增语言的流程

1. `scripts/detect_lang.py`：`EXT_LANG_MAP` 加扩展名、`LANG_COMMANDS` 加 lint/format 命令。
2. `linters/<lang>/` 放配置模板。
3. `skills/codelint-<lang>/SKILL.md` 写规范速查（frontmatter `name` 必须等于目录名）。
4. `docs/LANGUAGES.md` 状态列更新为 Stable/Beta。
5. 跑 `python3 scripts/detect_lang.py <项目>` 冒烟验证。
