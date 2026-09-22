## 1. Trigger heuristics

- [x] 1.1 Replace substring `in` match with word-boundary match for English trigger words (`\b(commit|push|deploy)\b`) in `hooks/user_prompt_validator.py`; keep Chinese trigger words (`提交|发布|部署`) as substring (no boundary semantics needed).
- [x] 1.2 Add action-intent detection: a message passes only when the trigger word is paired with an action-intent phrase (`请帮我|帮我|请|马上|立刻|现在|下一步|继续|please|now|next|proceed|go ahead|commit this|push this|deploy this`) **or** the trigger word stands at the start of the message (bare imperative).
- [x] 1.3 Add regression tests locking the existing `QUESTION_MARKERS` content (both `？` and `?` already present) — content itself is unchanged.
- [x] 1.4 Add regression tests for sentence-initial bare imperatives (`commit this now`, `提交代码`) that must still trigger.

## 2. Targeted language detection

- [x] 2.1 Add `_detect_languages_in_text(text, language_ids)` helper that returns the intersection of `re.findall(r"\w+", text.lower())` with `languages.json` ids.
- [x] 2.2 When the helper returns a non-empty set, restrict `run_gate()` to that subset.
- [x] 2.3 When the helper returns empty, fall back to existing `detect_languages()` semantics.

## 3. MCP server

- [x] 3.1 Add root `requirements.txt` with `mcp>=1.0,<2` (mcp 2.x changed the decorator API; pin to the tested major) and install it in skills-check.yml before unittest.
- [x] 3.2 Replace `scripts/run_check.py:mcp_main()` with a real `mcp.server.Server` that registers `check_code_style`, `auto_fix`, `list_languages` tools over stdio JSON-RPC.
- [x] 3.3 Ensure `check_code_style` returns a structured `{language, passed, exit_code, stderr_path}` payload and writes full stderr to `out/.codeguard-last.log`.
- [x] 3.4 Ensure `auto_fix` invokes the formatter chain and re-runs `check_code_style` before returning.
- [x] 3.5 Ensure `list_languages` returns `languages.json` ids + names without exposing internal schema.

## 4. Failure log

- [x] 4.1 Add `--log-dir` flag (default `out/`) to `scripts/run_check.py`.
- [x] 4.2 When a language fails, append full stderr to `<log-dir>/.codeguard-last.log` and emit only a summary line plus the absolute log path to stdout.
- [x] 4.3 Honor `--quiet` to suppress the log write and summary line for CI runs.

## 5. Documentation

- [x] 5.1 Append a "MCP server" subsection to `README.md` with one CLI invocation example.
- [x] 5.2 Mirror it in `README.zh-CN.md`.
- [x] 5.3 Confirm `.gitignore` covers `out/` so the on-disk log never enters the index.

## 6. Verification

- [x] 6.1 Add unit tests covering: trigger does NOT fire on `我刚才 pushed 了`, `关于 deployment 策略的讨论`, `Should I commit this?`; trigger fires on `请帮我 commit`, `commit this now`, `请帮我 push`, `提交代码`.
- [x] 6.2 Add a unit test that `_detect_languages_in_text` narrows the gate to a subset (e.g. prompt says `commit this rust change` → only `rust` runs).
- [x] 6.3 Add a unit test that `--mcp` boots, lists tools, and returns a tool result.
- [x] 6.4 Run `python3 -m unittest discover -s tests -p 'test_*.py'` — all green.
- [x] 6.5 Run `python3 scripts/validate_skills.py skills` — unchanged.
- [x] 6.6 Run `openspec validate --all --strict`.

## 7. Release

- [ ] 7.1 `node scripts/bump-plugin.mjs codeguard minor` (0.6.6 → 0.7.0; MCP server is a new feature).
- [ ] 7.2 Sync marketplace manifest + hub catalog.
- [ ] 7.3 Push, confirm CI green, tag v0.7.0, GitHub Release.
- [ ] 7.4 `openspec archive 2026-09-22-fix-gate-trigger-and-mcp`.
