# partme-codeguard-plugin 支持的语言

> 覆盖 **55 种编程语言/文件类型**。所有语言均可被 `detect_lang` 识别；其中 **16 种**已接入 linter 强制门禁（Stable / Beta），其余 39 种已列入路线图（Planned，钩子检测到后安全跳过）。
>
> 状态说明：**Stable** = 默认启用、久经生产验证；**Beta** = V0.2 起启用，需按安装说明准备工具；**Planned** = linter 集成在路线图上。

## Stable（默认强制，4 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 |
|---|---|---|---|
| Java | `.java` | `mvn -q javadoc:jar -DskipTests` | `mvn -q spotless:apply` |
| Rust | `.rs` | `cargo clippy --all-targets -- -D warnings` | `cargo fmt` |
| TypeScript / JavaScript | `.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` | `npx eslint . --max-warnings 0` | `npx eslint . --fix` |
| Python | `.py` | `ruff check .` | `ruff check . --fix` |

## Beta（V0.2 起，12 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 | 安装说明 |
|---|---|---|---|---|
| Go | `.go` | `go vet ./...` | `gofmt -w .` | 内置于 Go 工具链；聚合 lint 可装 golangci-lint |
| C# | `.cs` | `dotnet format --verify-no-changes` | `dotnet format` | .NET SDK 6+ |
| Kotlin | `.kt` `.kts` | `./gradlew detekt` | `./gradlew ktlintFormat` | 项目需配置 detekt / ktlint 插件 |
| Swift | `.swift` | `swiftlint` | `swiftlint --fix` | `brew install swiftlint` |
| PHP | `.php` | `php -l` | `php-cs-fixer fix` | `composer require --dev php-cs-fixer` |
| Ruby | `.rb` | `rubocop` | `rubocop -A` | `gem install rubocop` |
| Scala | `.scala` `.sc` | `scalafmt --check` | `scalafmt` | `coursier install scalafmt` |
| Shell | `.sh` `.bash` `.zsh` | `shellcheck` | `shfmt -w .` | `brew install shellcheck shfmt` |
| Dockerfile | `Dockerfile` | `hadolint` | —（仅检查） | `brew install hadolint` |
| YAML | `.yml` `.yaml` | `yamllint .` | `yamllint .` | `pip install yamllint` |
| Elixir | `.ex` `.exs` | `mix credo --strict` | `mix format` | 项目需配置 credo 依赖 |
| CSS / SCSS / Sass / LESS | `.css` `.scss` `.sass` `.less` | `npx stylelint **/*.css` | `npx stylelint --fix` | 项目需配置 stylelint |

## Planned（已识别，linter 在路线图上，39 种）

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
| HTML | `.html` `.htm` | htmlhint + prettier | V0.4 |
| SQL | `.sql` | sqlfluff | V0.4 |
| GraphQL | `.graphql` `.gql` | graphql-eslint | V0.4 |
| Protobuf | `.proto` | buf lint | V0.4 |
| Markdown | `.md` `.markdown` | markdownlint-cli2 | V0.4 |
| TOML | `.toml` | taplo | V0.4 |
| Haskell | `.hs` `.lhs` | hlint + fourmolu | V0.5 |
| OCaml | `.ml` `.mli` | ocamlformat | V0.5 |
| F# | `.fs` `.fsi` `.fsx` | fantomas | V0.5 |
| Perl | `.pl` `.pm` `.t` | perlcritic + perltidy | V0.5 |
| Groovy | `.groovy` | CodeNarc（npm-groovy-lint） | V0.5 |
| Clojure | `.clj` `.cljs` `.cljc` `.edn` | clj-kondo + cljstyle | V0.5 |
| PowerShell | `.ps1` `.psm1` | PSScriptAnalyzer | V0.5 |
| Zig | `.zig` | zig fmt + zlint | V0.5 |
| Nim | `.nim` | nimpretty | V0.5 |
| Crystal | `.cr` | ameba | V0.5 |
| Julia | `.jl` | JuliaFormatter | V0.5 |
| Elm | `.elm` | elm-format + elm-review | V0.5 |
| Lua | `.lua` | luacheck + stylua | V0.5 |
| Luau | `.luau` | luau-lint | V0.5 |
| Pascal / Delphi | `.pas` `.dpr` `.dpk` `.lpr` | pasfmt | V0.5 |
| R | `.R` `.r` | lintr | V0.5 |
| CFML (ColdFusion) | `.cfc` `.cfm` `.cfs` | CFLint | V0.5 |
| COBOL | `.cbl` `.cob` `.cpy` | cobol-check | V0.5 |
| Visual Basic .NET | `.vb` | dotnet format | V0.4（随 C# 通道） |
| Erlang | `.erl` `.hrl` | dialyzer + elvis | V0.5 |
| ArkTS (HarmonyOS) | `.ets` | ArkTS Linter | V0.5 |
| Metal | `.metal` | metal-lint | V0.5 |
| Liquid (Shopify) | `.liquid` | theme-check | V0.5 |
| CUDA | `.cu` `.cuh` | clang-tidy (CUDA) | V0.5 |
| Ansible（Playbook YAML） | playbook 内 | ansible-lint | V0.5 |

## 检测机制

1. **文件级**：`scripts/detect_lang.py` 的 `EXT_LANG_MAP` 覆盖上表全部扩展名 → PostToolUse 钩子按文件判断语言。
2. **项目级**：`PROJECT_MARKERS` 识别 `pom.xml` / `go.mod` / `Cargo.toml` / `package.json` / `pyproject.toml` / `composer.json` / `Gemfile` / `build.sbt` / `Package.swift` / `mix.exs` / `shard.yml` / `Project.toml` / `elm.json` / `stack.yaml` 等标记文件 → SessionStart 钩子据此注入项目语言清单。
3. **未接入 linter 的语言**：安全跳过，不报错、不阻塞。

## 新增语言的流程

1. `scripts/detect_lang.py`：`EXT_LANG_MAP` 加扩展名、`LANG_COMMANDS` 加 lint/format 命令。
2. `linters/<lang>/` 放配置模板。
3. `skills/codeguard-<lang>/SKILL.md` 写规范速查（frontmatter `name` 必须等于目录名）。
4. `docs/LANGUAGES.md` 状态列更新为 Stable/Beta。
5. 跑 `python3 scripts/detect_lang.py <项目>` 冒烟验证。
