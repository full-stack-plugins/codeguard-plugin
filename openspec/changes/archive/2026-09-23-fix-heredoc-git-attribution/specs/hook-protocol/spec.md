# hook-protocol（增量）：heredoc 正文按归属语义归因

## ADDED Requirements

### Requirement: Heredoc bodies SHALL be attributed by owner semantics

命令文本中 heredoc 正文的 git 归因 MUST 按归属语义区分：数据程序 + 引号定界符的正文是全字面量
（文档样例/模板字符串），MUST NOT 视为 shell 语法切段出 git 副作用；数据程序 + 无引号的正文会做
命令替换展开，`$(...)` 与反引号跨度的内层文本 MUST 保留扫描（其会被外层真实执行）；Shell 解释器
（bash/sh/zsh）接收的正文是内层 shell 代码，MUST 按既有切段规则建模；python/node 等非 Shell 解释器
接收的正文不是 shell 语法，MUST NOT 按切段归因。遮蔽处理 MUST 先于命令替换展开执行，
否则引号定界正文的字面 `$(...)` 会被误判为可执行替换。

#### Scenario: Sample text in a python heredoc is not guarded

- **WHEN** `python3 - <<'PY'` 的正文含三引号字符串 `'''cd a && git add && git commit && git push'''`（文档样例）
- **THEN** 判定不命中，钩子放行（此前整调用被拦且写入步骤不执行）

#### Scenario: Command substitution in an unquoted data heredoc is guarded

- **WHEN** `cat <<EOF` 的正文含 `$(git push origin b)` 或反引号包裹的 `git commit`
- **THEN** 展开后命中拦截（外层会真实执行，既有实测向量保持）

#### Scenario: Literal substitution text in a quoted data heredoc is not guarded

- **WHEN** `cat <<'EOF'` 的正文含字面 `$(git push origin b)`
- **THEN** 判定不命中（引号定界正文全字面量，不发生替换）

#### Scenario: Shell interpreter heredoc keeps modeled semantics

- **WHEN** `bash <<'SH'` 的正文含 `git commit -m t`
- **THEN** 判定命中且按一层间接建模（行为与既有切段语义一致）
