# partme-codeguard-plugin 支持的语言

> 覆盖 **55 种编程语言**（注册表 57 条，含 Dockerfile/Ansible 等文件类型条目）。所有语言均可被 `detect_lang` 识别；其中 **26 条**已接入 linter 强制门禁（Stable / Beta），其余列入路线图（Planned，钩子检测到后安全跳过）。

> 本文档由 `scripts/languages.json` 注册表自动生成（`scripts/gen_language_docs.py`）；新增/调整语言请改注册表后重新生成。


## Stable（默认强制，V0.1 起）（4 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 | 安装说明 |
|---|---|---|---|---|
| Java | `.java` | `mvn -q javadoc:jar -DskipTests` | `mvn -q spotless:apply` | — |
| Rust | `.rs` | `cargo clippy --all-targets -- -D warnings` | `cargo fmt` | — |
| TypeScript / JavaScript | `.ts` `.tsx` `.js` `.jsx` `.mjs` `.cjs` | `npx eslint . --max-warnings 0` | `npx eslint . --fix` | 项目需安装 eslint |
| Python | `.py` | `ruff check .` | `ruff check . --fix` | pip install ruff |

## Beta（V0.2 起）（22 种）

| 语言 | 扩展名 | Lint 命令 | Format 命令 | 安装说明 |
|---|---|---|---|---|
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
| Dart / Flutter | `.dart` | `dart analyze` | `dart format .` | Dart SDK 内置 |
| Solidity | `.sol` | `solhint **/*.sol` | `prettier --write` | npm install -g solhint prettier prettier-plugin-solidity |
| Terraform / OpenTofu | `.tf` `.tfvars` `.tofu` | `tflint` | `terraform fmt` | brew install tflint |
| Nix | `.nix` | `deadnix` | `nixpkgs-fmt` | nix-env -iA nixpkgs.nixpkgs-fmt nixpkgs.deadnix |
| HTML | `.html` `.htm` | `npx htmlhint` | `prettier --write` | npm install -g htmlhint |
| SQL | `.sql` | `sqlfluff lint` | `sqlfluff fix` | pip install sqlfluff |
| Protobuf | `.proto` | `buf lint` | `buf format` | brew install bufbuild/buf/buf |
| Markdown | `.md` `.markdown` | `npx markdownlint-cli2 **/*.md` | `markdownlint-cli2 --fix` | npm install -g markdownlint-cli2 |
| TOML | `.toml` | `taplo lint` | `taplo format` | cargo install taplo-cli --locked |
| Ansible | （文件名匹配） | `ansible-lint` | `ansible-lint --fix` | pip install ansible-lint |

## Planned（已识别，linter 在路线图上）（31 种）

| 语言 | 扩展名 | 计划 Linter | 目标版本 |
|---|---|---|---|
| C | `.c` `.h` | clang-tidy + clang-format | V0.4 |
| C++ | `.cpp` `.hpp` `.cc` | clang-tidy + clang-format | V0.4 |
| Objective-C | `.m` `.mm` | clang-tidy + clang-format | V0.4 |
| Vue | `.vue` | eslint-plugin-vue | V0.4 |
| Svelte | `.svelte` | eslint-plugin-svelte | V0.4 |
| Astro | `.astro` | eslint-plugin-astro | V0.4 |
| GraphQL | `.graphql` `.gql` | graphql-eslint | V0.4 |
| Haskell | `.hs` `.lhs` | brew install hlint fourmolu | V0.5 |
| OCaml | `.ml` `.mli` | opam install ocamlformat | V0.5 |
| F# | `.fs` `.fsi` `.fsx` | dotnet tool install -g fantomas | V0.5 |
| Perl | `.pl` `.pm` `.t` | cpanm Perl::Critic Perl::Tidy | V0.5 |
| Groovy | `.groovy` | npm install -g npm-groovy-lint | V0.5 |
| Clojure | `.clj` `.cljs` `.cljc` `.edn` | brew install clj-kondo cljstyle | V0.5 |
| PowerShell | `.ps1` `.psm1` | Install-Module PSScriptAnalyzer | V0.5 |
| Zig | `.zig` | 内置于 Zig 工具链 | V0.5 |
| Nim | `.nim` | nimpretty 内置于 Nim | V0.5 |
| Crystal | `.cr` | brew install crystal-ameba | V0.5 |
| Julia | `.jl` | julia -e 'using Pkg; Pkg.add("JuliaFormatter")' | V0.5 |
| Elm | `.elm` | npm install -g elm-review elm-format | V0.5 |
| Lua | `.lua` | luarocks install luacheck; cargo install stylua | V0.5 |
| Luau | `.luau` | luau-lint | V0.5 |
| Pascal / Delphi | `.pas` `.dpr` `.dpk` `.lpr` | pasfmt | V0.5 |
| R | `.r` | Rscript -e 'install.packages("lintr")' | V0.5 |
| CFML (ColdFusion) | `.cfc` `.cfm` `.cfs` | brew install cflint | V0.5 |
| COBOL | `.cbl` `.cob` `.cpy` | IBM COBOL Checker | V0.5 |
| Visual Basic .NET | `.vb` | .NET SDK 6+ | V0.4 |
| Erlang | `.erl` `.hrl` | rebar3 plugins 或 brew install elvis | V0.5 |
| ArkTS (HarmonyOS) | `.ets` | DevEco Studio ArkTS Linter | V0.5 |
| Metal | `.metal` | Xcode Metal compiler 诊断 | V0.5 |
| Liquid (Shopify) | `.liquid` | gem install theme-check | V0.5 |
| CUDA | `.cu` `.cuh` | CUDA Toolkit + clangd | V0.5 |

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

