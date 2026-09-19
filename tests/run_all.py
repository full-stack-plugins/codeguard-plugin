#!/usr/bin/env python3
"""codeguard 测试集：语言规则结构审计 + 对话级钩子触发模拟 + 报告结构断言。

三个子集（可单独跑，缺省全跑）：
  python3 tests/run_all.py          # 全量
  python3 tests/run_all.py langs    # 语言注册表结构审计（纯结构，不依赖工具安装）
  python3 tests/run_all.py hooks    # 钩子级模拟（构造临时 git 仓，按宿主协议 stdin JSON 触发）
  python3 tests/run_all.py unit     # 纯函数单测（glob/requiresConfig、{file} 兜底、多 cd 边界、综述≠细节）

钩子模拟的原理 = 完全复刻宿主行为：把 ZCode/Claude 会发给钩子的 JSON payload
通过 stdin 喂给真实钩子脚本，断言退出码与输出协议（exit 0 JSON / exit 2 stderr）。
runtime 用例按工具可用性自动 SKIP（shellcheck 已装则真跑，未装则结构通过）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
HOOKS = PLUGIN / "hooks"
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(HOOKS))

PASS, FAIL, SKIP = [], [], []


def ok(name, cond, note=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'✅' if cond else '❌'} {name}" + (f"  — {note}" if note and not cond else ""))


def skip(name, why):
    SKIP.append(name)
    print(f"  ⏭️  {name}  — {why}")


def run_hook(script: str, payload: dict | None, cwd: Path, env_extra: dict | None = None):
    """按宿主协议触发钩子：stdin JSON → (exit, stdout, stderr)"""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload) if payload is not None else "",
        capture_output=True, text=True, cwd=cwd, timeout=120, env=env,
    )


def git(repo: Path, *args: str):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def make_repo() -> Path:
    """临时 git 仓（含一个必被 shellcheck 抓到的坏脚本）"""
    repo = Path(tempfile.mkdtemp(prefix="cg-test-"))
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "deploy.sh").write_text(
        '#!/bin/bash\nif [ $foo = bar ]; then echo hi; fi\n'
    )
    git(repo, "add", "-A")
    return repo


# ══════════════════════════ 子集 1：语言规则结构审计 ══════════════════════════

def test_languages():
    print("\n[1] 语言规则结构审计（全部 stable/beta）")
    langs = json.load(open(PLUGIN / "scripts" / "languages.json"))["languages"]
    stable = [l for l in langs if l.get("status") in ("stable", "beta")]
    ok(f"stable/beta 数量 = {len(stable)}（≥50）", len(stable) >= 50)

    no_target, file_no_gate, npx_no_flag, npx_no_probe, bad_cfg = [], [], [], [], []
    for l in stable:
        lint = l.get("lint") or []
        cs = " ".join(lint)
        if not lint:
            # format-only 语言（julia/pascal）：无独立 linter，合法
            if not l.get("format"):
                no_target.append(l["id"])
            continue
        # 目标参数：{file} 占位 / 明确路径 / 项目级命令词（裸跑默认检查当前目录）
        project_level = (
            lint[0] in {
                "mvn", "cargo", "gradlew", "swiftlint", "dart", "tflint", "ameba",
                "rubocop", "dotnet", "buf", "mix", "crystal", "elm-review", "elvis",
            }
            or (len(lint) > 1 and lint[1] in {"fmt", "rock", "analyze"} and lint[0] in {"zig", "scalafmt"})
            or "markdownlint-cli2" in cs
            or any(t in cs for t in (".", "*", "{file}", "src"))
        )
        if not project_level:
            no_target.append(f"{l['id']}:{cs}")
        if "{file}" in cs and not l.get("gate"):
            file_no_gate.append(l["id"])
        if lint[0] == "npx":
            if "--no-install" not in cs:
                npx_no_flag.append(l["id"])
            if not l.get("probe"):
                npx_no_probe.append(l["id"])
        cfg = l.get("requiresConfig")
        if cfg is not None and (not isinstance(cfg, list) or not all(isinstance(x, str) and x for x in cfg)):
            bad_cfg.append(l["id"])
    ok("所有语言 lint 都有检查目标", not no_target, str(no_target))
    ok("{file} 单文件模式语言都有项目级 gate", not file_no_gate, str(file_no_gate))
    ok("npx 系全部 --no-install", not npx_no_flag, str(npx_no_flag))
    ok("npx 系全部有显式 probe", not npx_no_probe, str(npx_no_probe))
    ok("requiresConfig 结构合法", not bad_cfg, str(bad_cfg))

    # 关键语言的修正是否落地
    by_id = {l["id"]: l for l in stable}
    for lid, field, needle in [
        ("nix", "lint", "{file}"), ("groovy", "lint", "{file}"), ("cfml", "lint", "{file}"),
        ("html", "lint", "{file}"), ("markdown", "lint", "--no-install"),
        ("vbnet", "lint", "--verify-no-changes"),
        ("dockerfile", "gate", "hadolint"), ("sql", "gate", "sqlfluff"),
        ("c", "gate", "clang-tidy"), ("html", "gate", "htmlhint"),
    ]:
        ok(f"{lid}.{field} 含 {needle!r}", needle in json.dumps(by_id.get(lid, {}).get(field)))
    ok("rust 无 Cargo.toml 视为未接入", "Cargo.toml" in json.dumps(by_id.get("rust", {}).get("requiresConfig")))
    ok("java 无 pom/build 视为未接入", "pom.xml" in json.dumps(by_id.get("java", {}).get("requiresConfig")))
    ok("vbnet requiresConfig 用 glob (*.sln)", "*.sln" in json.dumps(by_id.get("vbnet", {})))
    ok("erlang requiresConfig(elvis.config)", "elvis.config" in json.dumps(by_id.get("erlang", {})))

    # detect_lang 透传：gate/probe/requiresConfig 必须进 LANG_COMMANDS
    from detect_lang import LANG_COMMANDS
    ok("LANG_COMMANDS 透传 gate（shell）", bool(LANG_COMMANDS.get("shell", {}).get("gate")))
    ok("LANG_COMMANDS 透传 probe（html）", bool(LANG_COMMANDS.get("html", {}).get("probe")))
    ok("LANG_COMMANDS 透传 requiresConfig（typescript）", bool(LANG_COMMANDS.get("typescript", {}).get("requiresConfig")))

    # runtime 抽查：已装工具的语言真跑一条坏样例
    if shutil.which("shellcheck"):
        repo = make_repo()
        r = run_hook("pre_tool_git_guard.py",
                     {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, repo)
        ok("shell 门禁真跑：坏脚本 → exit 2", r.returncode == 2, f"exit={r.returncode}")
        ok("shell 门禁 stderr 首行=综述", r.stderr.strip().splitlines()[0].startswith("codeguard ❌ 提交门禁未通过："))
        shutil.rmtree(repo)
    else:
        skip("shell 门禁真跑", "shellcheck 未安装")


# ══════════════════════════ 子集 2：对话级钩子触发 ══════════════════════════

def test_hooks():
    print("\n[2] 对话级钩子触发（stdin JSON 复刻宿主协议）")

    # ── SessionStart：env_check 在项目里盘点 ──
    repo = make_repo()
    r = run_hook("env_check.py", None, repo)
    out = r.stdout
    ok("SessionStart 盘点输出项目记忆", r.returncode == 0 and "# codeguard 项目记忆" in out)
    ok("SessionStart 列出检测到的语言", "检测到语言" in out)

    # ── PostToolUse：坏 shell 文件 → 结构化告警（exit 0 + additionalContext） ──
    r = run_hook("post_tool_lint.py",
                 {"tool_name": "Write", "tool_input": {"file_path": str(repo / "scripts" / "deploy.sh")}}, repo)
    ok("PostToolUse 坏文件 exit 0（不阻断）", r.returncode == 0)
    try:
        ctx = json.loads([l for l in r.stdout.splitlines() if l.startswith("{")][-1])
        add = ctx["hookSpecificOutput"]["additionalContext"]
        first = add.splitlines()[0]
        body = add[len(first):]
        ok("PostToolUse 注入 additionalContext", "codeguard" in first)
        ok("告警首行=综述（含语言与文件）", "shell" in first and "deploy.sh" in first)
        ok("综述≠细节（首行未在正文重复出现）", first.strip() not in body)
        ok("细节含具体问题编号", "SC" in body or "问题" in body)
        ok("细节含怎么修指引", "怎么修" in body or "自动修复" in body)
        ok("systemMessage 为短标题", 0 < len(ctx.get("systemMessage", "")) <= 60)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        ok("PostToolUse 输出为合法 JSON 协议", False, repr(e))

    # ── PostToolUse：好文件 → 通过确认 ──
    good = repo / "scripts" / "good.sh"
    good.write_text('#!/bin/bash\nx="ok"\necho "$x"\n')
    r = run_hook("post_tool_lint.py",
                 {"tool_name": "Write", "tool_input": {"file_path": str(good)}}, repo)
    ok("PostToolUse 好文件 exit 0", r.returncode == 0)
    ok("好文件注入通过确认", "✅" in r.stdout and "passed" in r.stdout)

    # ── UserPromptSubmit：提交意图（脏仓）→ 软引导注入（exit 0，prompt 不被弹回） ──
    r = run_hook("user_prompt_validator.py", {"user_prompt": "提交代码"}, repo)
    ok("提交意图 exit 0（软引导）", r.returncode == 0)
    try:
        ctx = json.loads([l for l in r.stdout.splitlines() if l.startswith("{")][-1])
        add = ctx["hookSpecificOutput"]["additionalContext"]
        first = add.splitlines()[0]
        ok("UPS 注入首行=综述", first.startswith("codeguard ❌ 提交门禁未通过："))
        ok("UPS 细节含怎么修与绕过说明", "怎么修" in add and "skipGate" in add)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        ok("UPS 输出为合法 JSON 协议", False, repr(e))

    # ── UserPromptSubmit：疑问句豁免（功能性询问不触发门禁） ──
    for q in ("怎么提交代码？", "git 提交和推送能不能排除 .venv 么", "commit 是什么意思"):
        r = run_hook("user_prompt_validator.py", {"user_prompt": q}, repo)
        ok(f"疑问句豁免: {q[:14]}…", r.returncode == 0 and r.stdout.strip() == "",
           f"exit={r.returncode} out={r.stdout[:60]!r}")

    # ── PreToolUse：git commit 脏仓 → 硬拦（exit 2 + stderr 综述/细节） ──
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, repo)
    ok("PreToolUse 脏仓 exit 2", r.returncode == 2)
    lines = r.stderr.strip().splitlines()
    ok("stderr 首行=综述", lines[0].startswith("codeguard ❌ 提交门禁未通过："))
    ok("综述后跟细节（标题≠详情）", len(lines) > 3 and "具体问题" in r.stderr)
    ok("综述行未在细节中重复", lines.count(lines[0]) == 1)

    # ── PreToolUse：干净仓 → 完全静默 ──
    clean = Path(tempfile.mkdtemp(prefix="cg-clean-"))
    git(clean, "init", "-q"); git(clean, "config", "user.email", "t@t"); git(clean, "config", "user.name", "t")
    (clean / "README.md").write_text("ok\n"); git(clean, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, clean)
    ok("干净仓 exit 0 且零输出（通过即静默）", r.returncode == 0 and r.stdout == "" and r.stderr == "",
       f"exit={r.returncode} out={r.stdout[:40]!r}")
    r = run_hook("user_prompt_validator.py", {"user_prompt": "提交代码"}, clean)
    ok("干净仓提交意图注入通过确认", r.returncode == 0 and "✅" in r.stdout)

    # ── PreToolUse：安全文件（.env/.venv 入库）→ 🛑 拦截 ──
    (repo / ".env").write_text("SECRET=1")
    (repo / ".venv" / "lib").mkdir(parents=True)
    (repo / ".venv" / "lib" / "x.py").write_text("x=1")
    git(repo, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, repo)
    ok("安全违规 exit 2", r.returncode == 2)
    ok("安全报告含 .env 与 .venv", ".env" in r.stderr and ".venv" in r.stderr)
    ok("安全报告给出 rm --cached 修法", "rm --cached" in r.stderr)

    # ── PreToolUse：多 cd 命令链 → 逐 git 段解析边界 ──
    ws = PLUGIN.parent
    cmd = (f"cd {ws} && python3 fix.py && cd {repo} && git commit -m t && cd {clean} && git push")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": cmd}}, repo)
    ok("多 cd 链不连坐 workspace（只查目标仓）", "partme" not in r.stderr and ws.name not in r.stderr.split("─")[0])

    # ── Stop：会话统计 ──
    r = run_hook("stop_summary.py", None, repo)
    ok("Stop 汇总 exit 0", r.returncode == 0)

    shutil.rmtree(repo); shutil.rmtree(clean)


# ══════════════════════════ 子集 3：纯函数单测 ══════════════════════════

def test_unit():
    print("\n[3] 纯函数单测")
    from detect_lang import project_uses_linter, probe_toolchain
    import gate_lib
    import pre_tool_git_guard as guard

    # requiresConfig glob 支持
    tmp = Path(tempfile.mkdtemp())
    ok("glob 未命中=未接入", not project_uses_linter({"requiresConfig": ["*.sln"]}, tmp))
    (tmp / "App.sln").write_text("")
    ok("glob 命中=已接入", project_uses_linter({"requiresConfig": ["*.sln"]}, tmp))
    ok("精确名匹配仍有效", project_uses_linter({"requiresConfig": ["App.sln"]}, tmp))
    ok("无 requiresConfig 视为已接入", project_uses_linter({}, tmp))

    # probe：不存在的工具
    ok("probe 报工具不在 PATH", probe_toolchain({"lint": ["no-such-tool-xyz"]})[0] is False)
    if shutil.which("shellcheck"):
        ok("probe shellcheck 通过", probe_toolchain({"lint": ["shellcheck"]})[0] is True)

    # run_gate：{file} 无 gate 的语言必须归 skipped（防字面量当文件名）
    gate_lib.detect_languages = lambda root: ["sql"]
    gate_lib.LANG_COMMANDS["sql"] = {"lint": ["sqlfluff", "lint", "{file}"], "install_hint": "pip install sqlfluff"}
    gate_lib.project_uses_linter = lambda c, r: True
    gate_lib.probe_toolchain = lambda c, timeout=10: (True, "")
    failures, skipped = gate_lib.run_gate(Path(tmp), {})
    ok("{file} 无 gate → skipped 不拦提交", not failures and any("gate" in s for s in skipped),
       f"failures={failures}")

    # 综述/细节分离：综述≠细节
    report = gate_lib.format_failure_report([("shell", "SC2086: double quote\nSC2154: unassigned", "shfmt -w .", "brew install")])
    first, rest = report.splitlines()[0], "\n".join(report.splitlines()[1:])
    ok("综述为一行短语", 0 < len(first) <= 80 and "\n" not in first)
    ok("综述行不在细节中重复", first not in rest)
    ok("细节含问题与修法", "SC2086" in rest and "怎么修" in rest)
    srep = gate_lib.format_safety_report([(".env", "敏感配置", "git rm --cached .env")])
    sfirst = srep.splitlines()[0]
    ok("安全报告同构：首行综述不重复", sfirst not in "\n".join(srep.splitlines()[1:]))

    # 多 cd 边界解析
    roots = guard.resolve_project_roots(f"cd /tmp && x && cd {PLUGIN} && git commit -m t && cd /tmp && git push")
    ok("边界=git 段前最近的 cd", PLUGIN in roots and Path("/tmp") not in roots)
    ok("无 git 段返回空", guard.resolve_project_roots("ls -la && echo done") == [])
    ok("is_guarded 词法匹配不误伤 echo", not guard.is_guarded('echo "git push 是危险命令"'))
    ok("is_guarded 命中真实 git push", guard.is_guarded("cd r && git push origin main"))
    shutil.rmtree(tmp)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"codeguard 测试集  plugin={PLUGIN.name}")
    if which in ("all", "langs"): test_languages()
    if which in ("all", "hooks"): test_hooks()
    if which in ("all", "unit"): test_unit()
    print(f"\n═══ 结果: {len(PASS)} 通过 / {len(FAIL)} 失败 / {len(SKIP)} 跳过 ═══")
    if FAIL:
        print("失败项:", *FAIL, sep="\n  - ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
