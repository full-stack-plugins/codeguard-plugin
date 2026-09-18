# partme-codeguard-plugin 支持的语言

> 覆盖 **55 种编程语言**（注册表 57 条，含 Dockerfile/Ansible 等文件类型条目）。所有语言均可被 `detect_lang` 识别；其中 **53 条**已接入 linter 强制门禁（Stable / Beta），其余列入路线图（Planned，钩子检测到后安全跳过）。

> 本文档由 `scripts/languages.json` 注册表自动生成（`scripts/gen_language_docs.py`）；新增/调整语言请改注册表后重新生成。


## Stable（默认强制，V0.1 起）（53 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 | 安装说明 |
|---|---|---|---|---|
| Java | `.java` | `mvn -q javadoc:jar -DskipTests` | `mvn -q spotless:apply` | — |
| Rust | `.rs` | `cargo clippy --all-targets -- -D warnings` | `cargo fmt` | — |
| TypeScript / JavaScript | `.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` | `npx eslint . --max-warnings 0` | `npx eslint . --fix` | 项目需安装 eslint |
| Python | `.py` | `ruff check .` | `ruff check . --fix` | pip install ruff |
| Go | `.go` | `go vet ./...` | `gofmt -w .` | 内置于 Go 工具链；聚合 lint 可装 golangci-lint |
| C# | `.cs` | `dotnet format --verify-no-changes` | `dotnet format` | .NET SDK 6+ |
| Kotlin | `.kt` `.kts` | `./gradlew detekt` | `./gradlew ktlintFormat` | 项目需配置 detekt / ktlint 插件 |
| Swift | `.swift` | `swiftlint` | `swiftlint --fix` | brew install swiftlint |
| PHP | `.php` | `php -l` | `php-cs-fixer fix` | composer require --dev php-cs-fixer |
| Ruby | `.rb` | `rubocop` | `rubocop -A` | gem install rubocop |
| Scala | `.scala` `.sc` | `scalafmt --check` | `scalafmt` | coursier install scalafmt |
| Shell | `.sh` `.bash` `.zsh` | `shellcheck` | `shfmt -w .` | brew install shellcheck shfmt |
| Dockerfile | （文件名匹配） | `hadolint` | `hadolint` | brew install hadolint |
| YAML | `.yml` `.yaml` | `yamllint .` | `yamllint .` | pip install yamllint |
| Elixir | `.ex` `.exs` | `mix credo --strict` | `mix format` | 项目需配置 credo 依赖 |
| CSS / SCSS / Sass / LESS | `.css` `.scss` `.sass` `.less` | `npx stylelint **/*.css` | `npx stylelint **/*.css --fix` | npm install --save-dev stylelint stylelint-config-standard |
| C | `.c` `.h` | `clang-tidy --quiet` | `clang-format -i` | clang-tidy + clang-format |
| C++ | `.cpp` `.hpp` `.cc` | `clang-tidy --quiet` | `clang-format -i` | clang-tidy + clang-format |
| Objective-C | `.m` `.mm` | `clang-tidy --quiet` | `clang-format -i` | clang-tidy + clang-format |
| Dart / Flutter | `.dart` | `dart analyze` | `dart format .` | Dart SDK 内置 |
| Vue | `.vue` | `npx eslint --ext .vue .` | `npx eslint --ext .vue . --fix` | eslint-plugin-vue |
| Svelte | `.svelte` | `npx eslint .` | `npx eslint . --fix` | eslint-plugin-svelte |
| Astro | `.astro` | `npx eslint .` | `npx eslint . --fix` | eslint-plugin-astro |
| Solidity | `.sol` | `solhint **/*.sol` | `prettier --plugin=prettier-plugin-solidity --write` | npm install -g solhint prettier prettier-plugin-solidity |
| Terraform / OpenTofu | `.tf` `.tfvars` `.tofu` | `tflint` | `terraform fmt` | brew install tflint |
| Nix | `.nix` | `deadnix` | `nixpkgs-fmt` | nix-env -iA nixpkgs.nixpkgs-fmt nixpkgs.deadnix |
| HTML | `.html` `.htm` | `npx htmlhint` | `prettier --write` | npm install -g htmlhint |
| SQL | `.sql` | `sqlfluff lint` | `sqlfluff fix` | pip install sqlfluff |
| GraphQL | `.graphql` `.gql` | `npx eslint --ext .graphql .` | `npx eslint --ext .graphql . --fix` | graphql-eslint |
| Protobuf | `.proto` | `buf lint` | `buf format` | brew install bufbuild/buf/buf |
| Markdown | `.md` `.markdown` | `npx markdownlint-cli2 **/*.md` | `markdownlint-cli2 --fix` | npm install -g markdownlint-cli2 |
| TOML | `.toml` | `taplo lint` | `taplo format` | cargo install taplo-cli --locked |
| Haskell | `.hs` `.lhs` | `hlint .` | `fourmolu -i .` | brew install hlint fourmolu |
| OCaml | `.ml` `.mli` | `ocamlformat --check .` | `ocamlformat -i .` | opam install ocamlformat |
| F# | `.fs` `.fsi` `.fsx` | `dotnet fantomas --check` | `dotnet fantomas` | dotnet tool install -g fantomas |
| Perl | `.pl` `.pm` `.t` | `perlcritic` | `perltidy -b` | cpanm Perl::Critic Perl::Tidy |
| Groovy | `.groovy` | `npm-groovy-lint` | `npm-groovy-lint --fix` | npm install -g npm-groovy-lint |
| Clojure | `.clj` `.cljs` `.cljc` `.edn` | `clj-kondo --lint src` | `cljstyle` | brew install clj-kondo cljstyle |
| PowerShell | `.ps1` `.psm1` | `pwsh -NoProfile -Command Invoke-ScriptAnalyzer -Path . -Severity Error` | `pwsh -NoProfile -Command Invoke-Formatter` | Install-Module PSScriptAnalyzer |
| Zig | `.zig` | `zig fmt --check` | `zig fmt` | 内置于 Zig 工具链 |
| Nim | `.nim` | `nim check src` | `nimpretty -r .` | nimpretty 内置于 Nim |
| Crystal | `.cr` | `ameba` | `crystal tool format` | brew install crystal-ameba |
| Julia | `.jl` | — | `julia -e using JuliaFormatter; format('.')` | julia -e 'using Pkg; Pkg.add("JuliaFormatter")' |
| Elm | `.elm` | `elm-review` | `elm-format --yes` | npm install -g elm-review elm-format |
| Lua | `.lua` | `luacheck .` | `stylua .` | luarocks install luacheck; cargo install stylua |
| Luau | `.luau` | `luau-analyze` | `stylua --syntax luau .` | luau-lsp / luau-analyze |
| Pascal / Delphi | `.pas` `.dpr` `.dpk` `.lpr` | — | `ptop -b .` | pasfmt |
| R | `.r` | `Rscript -e lintr::lint_dir('.')` | `styler :: style_dir` | Rscript -e 'install.packages(c("lintr","styler"))' |
| CFML (ColdFusion) | `.cfc` `.cfm` `.cfs` | `cflint` | — | brew install cflint |
| Visual Basic .NET | `.vb` | `dotnet format` | `dotnet format` | .NET SDK 6+ |
| Erlang | `.erl` `.hrl` | `elvis rock` | `erlfmt` | rebar3 plugins / escript |
| Liquid (Shopify) | `.liquid` | `theme-check .` | — | gem install theme-check |
| CUDA | `.cu` `.cuh` | `clang-tidy --quiet` | `clang-format -i` | CUDA Toolkit + clangd |

## Planned（已识别，linter 在路线图上）（4 种）

| 语言 | 扩展名 | 计划 Linter | 目标版本 |
|---|---|---|---|
| COBOL | `.cbl` `.cob` `.cpy` | 无独立 CLI linter（依赖平台 IDE 诊断） | V0.5 |
| ArkTS (HarmonyOS) | `.ets` | 无独立 CLI linter（依赖平台 IDE 诊断） | V0.5 |
| Metal | `.metal` | 无独立 CLI linter（依赖平台 IDE 诊断） | V0.5 |
| Ansible | — | playbook 检查由 ansible-lint 承接（yaml 通道）；语义级检查待集成 | V0.3 |

## 检测机制

1. **文件级**：`EXT_LANG_MAP` 覆盖上表全部扩展名 → PostToolUse 钩子按文件判断语言。
2. **项目级**：`PROJECT_MARKERS` 识别标记文件 → SessionStart 钩子注入语言清单。
3. **自定义扩展**：项目根 `codeguard.json` 的 `extensions` 可合并/覆盖内置映射，`exclude` 排除文件。
4. **Planned 状态语言**：安全跳过，不报错、不阻塞。

## 新增语言的流程

1. `scripts/languages.json` 注册表加一条语言定义（id/extensions/markers/lint/format/status）。
2. `linters/<lang>/` 放配置模板。
3. `skills/codeguard-<lang>/SKILL.md` 写规范速查（frontmatter `name` == 目录名）。
4. 重跑 `python3 scripts/gen_language_docs.py` 同步本文档。
5. `python3 scripts/detect_lang.py <项目>` 冒烟验证。

