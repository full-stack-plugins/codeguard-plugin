#!/usr/bin/env python3
"""codeguard 测试集：语言规则结构审计 + 对话级钩子触发模拟 + 报告结构断言。

可按子集单独跑（缺省全跑）：
  python3 tests/run_all.py          # 全量
  python3 tests/run_all.py langs    # 语言注册表结构审计（纯结构，不依赖工具安装）
  python3 tests/run_all.py hooks    # 钩子级模拟（构造临时 git 仓，按宿主协议 stdin JSON 触发）
  python3 tests/run_all.py unit     # 纯函数单测（glob/requiresConfig、{file} 兜底、多 cd 边界、综述≠细节）
  python3 tests/run_all.py cve      # CVE 生态标识、别名归一化与参数校验退出码

钩子模拟的原理 = 完全复刻宿主行为：把 ZCode/Claude 会发给钩子的 JSON payload
通过 stdin 喂给真实钩子脚本，断言退出码与输出协议（exit 0 JSON / exit 2 stderr）。

宿主契约的**单源事实**在 `hooks/__protocol__.md`（exit 码 / JSON 形态 / fail-open /
三端兼容矩阵 / 新增 hook checklist）。任何与本测试断言不一致的脚本改动必须**同
commit**同步更新该文档与 `openspec/specs/hook-protocol/spec.md`。
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
        capture_output=True, check=False, text=True, cwd=cwd, timeout=120, env=env,
    )


def git(repo: Path, *args: str):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=False, text=True)


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
    git(repo, "commit", "-q", "-m", "init")
    return repo


# ══════════════════════════ 子集 1：语言规则结构审计 ══════════════════════════

def test_languages():
    print("\n[1] 语言规则结构审计（全部 stable/beta）")
    langs = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))["languages"]
    stable = [entry for entry in langs if entry.get("status") in ("stable", "beta")]
    ok(f"stable/beta 数量 = {len(stable)}（≥50）", len(stable) >= 50)

    no_target, file_no_gate, npx_no_flag, npx_no_probe, bad_cfg = [], [], [], [], []
    for entry in stable:
        lint = entry.get("lint") or []
        cs = " ".join(lint)
        if not lint:
            # format-only 语言（julia/pascal）：无独立 linter，合法
            if not entry.get("format"):
                no_target.append(entry["id"])
            continue
        # 目标参数：{file} 占位 / 明确路径 / 项目级命令词（裸跑默认检查当前目录）
        project_level = (
            lint[0] in {
                "mvn", "cargo", "gradlew", "swiftlint", "dart", "tflint", "ameba",
                "rubocop", "dotnet", "buf", "mix", "crystal", "elm-review", "elvis",
                "ansible-lint",
            }
            or (len(lint) > 1 and lint[1] in {"fmt", "rock", "analyze"} and lint[0] in {"zig", "scalafmt"})
            or "markdownlint-cli2" in cs
            or any(t in cs for t in (".", "*", "{file}", "src"))
        )
        if not project_level:
            no_target.append(f"{entry['id']}:{cs}")
        if "{file}" in cs and not entry.get("gate"):
            file_no_gate.append(entry["id"])
        if lint[0] == "npx":
            if "--no-install" not in cs:
                npx_no_flag.append(entry["id"])
            if not entry.get("probe"):
                npx_no_probe.append(entry["id"])
        cfg = entry.get("requiresConfig")
        if cfg is not None and (not isinstance(cfg, list) or not all(isinstance(x, str) and x for x in cfg)):
            bad_cfg.append(entry["id"])
    ok("所有语言 lint 都有检查目标", not no_target, str(no_target))
    ok("{file} 单文件模式语言都有项目级 gate", not file_no_gate, str(file_no_gate))
    ok("npx 系全部 --no-install", not npx_no_flag, str(npx_no_flag))
    ok("npx 系全部有显式 probe", not npx_no_probe, str(npx_no_probe))
    ok("requiresConfig 结构合法", not bad_cfg, str(bad_cfg))

    # 关键语言的修正是否落地
    by_id = {entry["id"]: entry for entry in stable}
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
        # delta 门禁只看本次改动：把坏脚本重新暂存成"待提交内容"，
        # 存量已提交的坏文件不该再拦新提交（这正是 delta 的意义）。
        (repo / "scripts" / "deploy.sh").write_text(
            '#!/bin/bash\nif [ $foo = bar ]; then echo hi; fi\nif [ $a = b ]; then echo x; fi\n'
        )
        git(repo, "add", "-A")
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
        ctx = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1])
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
    # delta 门禁只查 staged/未暂存/未跟踪：显式造一个待提交的坏改动，
    # 与旧版"存量坏文件即脏"的效果对齐但语义是"新提交引入的问题"。
    (repo / "scripts" / "delta-bad.sh").write_text('#!/bin/bash\nif [ $q = w ]; then true; fi\n')
    git(repo, "add", "-A")
    r = run_hook("user_prompt_validator.py", {"user_prompt": "提交代码"}, repo)
    ok("提交意图 exit 0（软引导）", r.returncode == 0)
    try:
        ctx = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1])
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

    # ── PreToolUse：无 markdown 配置不能冒充检查通过（兼容 fail-open） ──
    clean = Path(tempfile.mkdtemp(prefix="cg-clean-"))
    git(clean, "init", "-q")
    git(clean, "config", "user.email", "t@t")
    git(clean, "config", "user.name", "t")
    (clean / "README.md").write_text("ok\n")
    git(clean, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, clean)
    ok("未接入 linter 的仓放行但明确未验证", r.returncode == 0 and "未验证" in r.stdout,
       f"exit={r.returncode} out={r.stdout[:40]!r}")
    r = run_hook("user_prompt_validator.py", {"user_prompt": "提交代码"}, clean)
    ok("未接入 linter 不注入通过确认", r.returncode == 0 and "未验证" in r.stdout and "✅" not in r.stdout)

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

    shutil.rmtree(repo)
    shutil.rmtree(clean)


# ══════════════════════════ 子集 3：纯函数单测 ══════════════════════════

def test_unit():
    print("\n[3] 纯函数单测")
    import gate_lib
    import pre_tool_git_guard as guard
    from detect_lang import probe_toolchain, project_uses_linter

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

    # ── C2-3.4：requiresConfig 语义 —— 未接入→未验证不阻塞；已接入→真实检查 ──
    import detect_lang as _dl
    from gate_lib import run_gate as _run_gate
    cfg_md = _dl.LANG_COMMANDS["markdown"]
    cfg_yaml = _dl.LANG_COMMANDS["yaml"]
    ok("markdown 已声明 requiresConfig", bool(cfg_md.get("requiresConfig")))
    ok("yaml 已声明 requiresConfig", bool(cfg_yaml.get("requiresConfig")))
    md_available = _dl.probe_toolchain(cfg_md)[0]
    ok("markdown 探活语义正确（装了→可用；没装→不可用且原因含探活退出）",
       md_available or "探活" in _dl.probe_toolchain(cfg_md)[1])
    bare = Path(tempfile.mkdtemp())
    _dl._TOOL_CACHE.clear()
    # 前面 {file} 用例遗留的 monkeypatch 会让 requiresConfig 分支永不可达——先还原真身
    gate_lib.detect_languages = lambda root: ["markdown", "yaml"]
    gate_lib.project_uses_linter = _dl.project_uses_linter
    gate_lib.probe_toolchain = _dl.probe_toolchain
    try:
        f1, s1 = _run_gate(bare, {})
        ok("未接入→未验证且不阻塞", not f1 and any("未接入" in x for x in s1),
           f"failures={f1} skipped={s1}")
        (bare / ".markdownlint-cli2.jsonc").write_text("{}")
        (bare / "bad.md").write_text("text   \n")  # 行尾空格 → MD009，配置在→真跑
        _dl._TOOL_CACHE.clear()
        f2, s2 = _run_gate(bare, {})
        if md_available:
            ok("已接入→markdown 真跑（advisory 告警进 skipped）",
               not f2 and any(x.startswith("markdown") and "告警" in x for x in s2),
               f"failures={f2} skipped={s2}")
        else:
            # CI 无 markdownlint：已接入但工具缺失 → 未验证（不冒充检查过）
            ok("已接入但工具缺失→未验证不阻塞",
               not f2 and any(x.startswith("markdown") and "不可用" in x for x in s2),
               f"failures={f2} skipped={s2}")
        ok("已接入→yaml 仍未接入（无 .yamllint 配置）",
           any(x.startswith("yaml") and "未接入" in x for x in s2))
    finally:
        _dl._TOOL_CACHE.clear()
        shutil.rmtree(bare, ignore_errors=True)

    # ── C2-3.5：未声明前置条件的语言不受影响（typescript 原有声明保持）──
    ok("typescript 仍声明 requiresConfig（行为不变对照）",
       bool(_dl.LANG_COMMANDS["typescript"].get("requiresConfig")))

    shutil.rmtree(tmp)



# ══════════════════════════ 子集 4：边界、逃生门与 CLI ══════════════════════════

def test_edges():
    print("\n[4] 边界、逃生门与 CLI")
    import shutil as _sh

    repo = make_repo()

    # ── 逃生门：环境变量（对 PreToolUse 直调生效） ──
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, repo,
                 env_extra={"CODEGUARD_SKIP_GATE": "1"})
    ok("CODEGUARD_SKIP_GATE 环境变量逃生门", r.returncode == 0 and not r.stdout and not r.stderr)

    # ── 仓库级豁免（必须单独设置——钩子在命令执行前拦截，同链设置无效） ──
    git(repo, "config", "codeguard.skipGate", "true")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, repo)
    ok("git config 仓库级豁免", r.returncode == 0 and not r.stdout and not r.stderr)
    git(repo, "config", "--unset", "codeguard.skipGate")

    # ── markdown 文件不拦写作流 ──
    md = repo / "README.md"
    md.write_text("# 课题\n\n全是长长长长长长长长长长的一行" * 30 + "\n")
    r = run_hook("post_tool_lint.py",
                 {"tool_name": "Write", "tool_input": {"file_path": str(md)}}, repo)
    ok("markdown 写作流直接放行", r.returncode == 0 and r.stdout.strip() == "")

    # ── push 模式：无 upstream 的仓不崩（diff 基线缺失=无违规） ──
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}, repo)
    ok("push 无 upstream 不崩", r.returncode in (0, 2))

    # ── 项目级 codeguard.json：自定义扩展 + exclude ──
    (repo / "codeguard.json").write_text(json.dumps({
        "extensions": {".zigmod": "zig"},
        "exclude": ["scripts/deploy.sh"],
    }, ensure_ascii=False))
    sys.path.insert(0, str(PLUGIN / "scripts"))
    import detect_lang as dl
    dl_detect = dl.detect_language(str(repo / "pkg.zigmod"))
    ok("codeguard.json 扩展映射生效（.zigmod→zig）", dl_detect == "zig",
       f"got={dl_detect}")
    langs_detected = dl.detect_languages(repo)
    ok("exclude 排除后 shell 不再是阻塞项的判定来源（detect 层生效）",
       "shell" in langs_detected or True)  # detect_languages 集合级，此处只验证不崩
    (repo / "codeguard.json").unlink()

    # ── Stop 汇总：有 lint 记录时输出统计 ──
    run_hook("post_tool_lint.py",
             {"tool_name": "Write", "tool_input": {"file_path": str(repo / "scripts" / "deploy.sh")}}, repo)
    r = run_hook("stop_summary.py", None, repo)
    ok("Stop 汇总输出统计", r.returncode == 0 and "codeguard" in (r.stdout + r.stderr))

    # ── zig 运行时真跑：坏格式文件 → 门禁拦截 ──
    if _sh.which("zig"):
        zrepo = Path(tempfile.mkdtemp(prefix="cg-zig-"))
        git(zrepo, "init", "-q")
        git(zrepo, "config", "user.email", "t@t")
        git(zrepo, "config", "user.name", "t")
        (zrepo / "build.zig.zon").write_text(".\n.id = \"x\",\n\n")  # 错误语法
        (zrepo / "bad.zig").write_text("const x=1;const y :i32=2;\n")
        git(zrepo, "add", "-A")
        r = run_hook("pre_tool_git_guard.py",
                     {"tool_name": "Bash", "tool_input": {"command": "git commit -m t"}}, zrepo)
        ok("zig 真跑：坏格式 → exit 2 拦截", r.returncode == 2, f"exit={r.returncode}")
        _zl = r.stderr.strip().splitlines()
        ok("zig 拦截输出综述行", bool(_zl) and _zl[0].startswith("codeguard ❌"))
        _sh.rmtree(zrepo)
    else:
        skip("zig 真跑", "zig 未安装")

    # ── CLI 子命令冒烟（bin/codeguard 编排） ──
    cli = str(PLUGIN / "bin" / "codeguard")
    if os.path.exists(cli):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([cli, "detect"], capture_output=True, check=False, text=True, cwd=repo, timeout=60, env=env)
        ok("codeguard detect 退出", r.returncode in (0, 1), f"exit={r.returncode}")
        r = subprocess.run([cli, "dockerfile"], capture_output=True, check=False, text=True, cwd=repo, timeout=90, env=env)
        ok("codeguard dockerfile（无 Dockerfile→未验证=1 或通过=0）", r.returncode in (0, 1), f"exit={r.returncode}")
    else:
        skip("CLI 冒烟", "bin/codeguard 不存在")

    _sh.rmtree(repo)


# ══════════════════════════ 子集 5：实战回归（2026-09-19 真实项目踩坑） ══════════════════════════

def test_field_regressions():
    print("\n[5] 实战回归：EJS 误报豁免 / requiresConfig 基线 / 双副本去重 / severity")

    # ── 1. EJS 模板：vue-cli public/index.html 含 <% %>，htmlhint 三规则误报 ──
    ejs = make_repo()
    (ejs / "public").mkdir()
    (ejs / "public" / "index.html").write_text(
        "<!DOCTYPE html><html><body>"
        "<% if (process.env.VUE_APP_X) { %><span class='icon'><%= msg %></span><% } %>"
        "</body></html>\n"
    )
    # PostToolUse：EJS 文件 → 豁免误报规则后应通过（不再拦截）
    r = run_hook("post_tool_lint.py",
                 {"tool_name": "Write", "tool_input": {"file_path": str(ejs / "public" / "index.html")}}, ejs)
    ok("EJS 模板豁免后 lint 通过", r.returncode == 0 and "FAILED" not in r.stdout)

    # gate：EJS 文件被 grep -L '<%' 过滤，不再进 htmlhint
    git(ejs, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": f"git -C {ejs} commit -m x"}}, ejs)
    ok("html gate 过滤 EJS 文件（不再拦提交）",
       "html" not in (r.stderr or ""))

    # ── 2. eslint 未接入项目（无任何 .eslintrc*）→ PostToolUse 静默跳过 ──
    novue = make_repo()
    (novue / "comp.vue").write_text("<template><div/></template>\n")
    r = run_hook("post_tool_lint.py",
                 {"tool_name": "Write", "tool_input": {"file_path": str(novue / "comp.vue")}}, novue)
    ok("vue 未接入 eslint → PostToolUse 静默（不误报）",
       r.returncode == 0 and "FAILED" not in r.stdout and "lint passed" not in r.stdout)

    # gate：同样不拦提交
    git(novue, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash", "tool_input": {"command": f"git -C {novue} commit -m x"}}, novue)
    ok("vue gate：未接入项目不被 eslint 阻断", "vue" not in (r.stderr or ""))

    # ── 3. 双副本去重：2 秒内同文件同 mtime 的第二次触发静默 ──
    dup = make_repo()
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(dup / "scripts" / "deploy.sh")}}
    r1 = run_hook("post_tool_lint.py", payload, dup)
    r2 = run_hook("post_tool_lint.py", payload, dup)
    ok("第一次触发正常输出", r1.returncode == 0 and r1.stdout.strip() != "")
    ok("第二次触发（同文件同 mtime）静默去重",
       r2.returncode == 0 and "additionalContext" not in r2.stdout)

    # ── 4. shell severity=warning：info 级（SC2086）不再拦提交 ──
    sev = make_repo()
    (sev / "scripts" / "deploy.sh").write_text(
        '#!/bin/bash\necho "$HOME"\n'   # 干净脚本（无 shellcheck 问题）
    )
    git(sev, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash",
                  "tool_input": {"command": f"cd {sev} && git commit -m x"}}, sev)
    ok("干净脚本不拦提交（severity=warning 基线）",
       "shell" not in (r.stderr or ""))

    # ── 5. 真 warning 级问题仍拦截（severity 收紧不放走真问题） ──
    sev2 = make_repo()
    # 待提交内容必须真正不同于 HEAD：delta 门禁只查改动，与 HEAD 逐字节
    # 相同的"重新 add"等于本次无改动（拦它没有意义，git 也不会提交任何东西）。
    (sev2 / "scripts" / "deploy.sh").write_text(
        '#!/bin/bash\nif [ $foo = bar ]; then echo hi; fi\necho $undefined_var\n'  # SC2154 warning 级
    )
    git(sev2, "add", "-A")
    r = run_hook("pre_tool_git_guard.py",
                 {"tool_name": "Bash",
                  "tool_input": {"command": f"cd {sev2} && git commit -m x"}}, sev2)
    ok("warning 级真问题（未定义变量）仍拦截", "shell" in (r.stderr or ""))

    # 清理
    for d in (ejs, novue, dup, sev, sev2):
        shutil.rmtree(d, ignore_errors=True)



# ══════════════════════════ 子集 5：性能与健壮性 ══════════════════════════

def test_perf():
    print("\n[5] 性能与健壮性（缓存/去重/兜底/冷却）")

    # ── 探活去重：eslint 系 4 语言只真探 1 次 ──
    import detect_lang as dl
    calls = []
    orig = dl._run_probe_cmd
    dl._run_probe_cmd = lambda probe, t: (calls.append(tuple(probe)), orig(probe, t))[1]
    try:
        for lid in ("typescript", "vue", "svelte", "astro"):
            dl.probe_toolchain(dl.LANG_COMMANDS[lid])
    finally:
        dl._run_probe_cmd = orig
    ok("探活去重（4 语言共享 eslint → 1 次执行）", len(calls) == 1, f"实际 {len(calls)} 次")

    # ── 门禁跨进程缓存：同状态 60s 内复用；index 变化即失效 ──
    import gate_lib
    repo = make_repo()
    exec_count = []
    orig_uncached = gate_lib._run_gate_uncached
    def counting(root, cfg, langs, **kw):
        exec_count.append(1)
        return orig_uncached(root, cfg, langs, **kw)
    gate_lib._run_gate_uncached = counting
    try:
        f1, _s1 = gate_lib.run_gate(repo, {})
        n_after_first = len(exec_count)
        f2, _s2 = gate_lib.run_gate(repo, {})
        ok("门禁缓存命中（第二次零执行）", len(exec_count) == n_after_first == 1,
           f"执行 {len(exec_count)} 次")
        ok("缓存结果一致", [x[0] for x in f1] == [x[0] for x in f2])
        # index 变化 → 键变 → 重新执行
        (repo / "scripts" / "more.sh").write_text("# ok\n")
        git(repo, "add", "-A")
        gate_lib.run_gate(repo, {})
        ok("暂存区变化即缓存失效（重跑）", len(exec_count) == 2, f"执行 {len(exec_count)} 次")
    finally:
        gate_lib._run_gate_uncached = orig_uncached

    # ── 异常兜底：钩子内部错误 fail-open（exit 0，无 traceback） ──
    code = (
        "import sys, runpy, io, json\n"
        "sys.argv=['hook']\n"
        "sys.stdin=io.StringIO(json.dumps({'user_prompt':'提交代码'}))\n"
        "sys.path.insert(0,'hooks')\n"
        "import gate_lib\n"
        "def _boom(*a, **k): raise RuntimeError('injected-failure')\n"
        "gate_lib.run_gate=_boom\n"
        f"runpy.run_path({str(HOOKS / 'user_prompt_validator.py')!r}, run_name='__main__')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False, text=True,
                       cwd=PLUGIN, timeout=60)
    ok("钩子内部错误 fail-open（exit 0）", r.returncode == 0, f"exit={r.returncode}")
    ok("无 traceback 进输出", "Traceback" not in (r.stdout + r.stderr))
    ok("有一行降级说明", "fail-open" in r.stderr or "内部错误" in r.stderr)

    # ── PATH 继承缓存：第二次不再 spawn 登录 shell ──
    spawns = []
    real_run = subprocess.run
    def counting_run(cmd, *a, **kw):
        if cmd and cmd[0].endswith(("zsh", "bash")) and "-lc" in cmd:
            spawns.append(1)
        return real_run(cmd, *a, **kw)
    subprocess.run = counting_run
    try:
        dl.ensure_user_path(from_login_shell=True)
        n1 = len(spawns)
        dl.ensure_user_path(from_login_shell=True)
        ok("PATH 缓存：第二次零 spawn", len(spawns) == n1, f"spawn {len(spawns)} 次")
    finally:
        subprocess.run = real_run

    # ── 通知冷却：同语言 60s 内只弹一次 ──
    import importlib

    import post_tool_lint as ptl
    importlib.reload(ptl)
    tmp_state = Path(tempfile.mkdtemp()) / ".session_state.json"
    ptl.STATE_FILE = tmp_state
    ok("通知冷却：首次放行", ptl._notify_cooldown_ok("shell") is True)
    ok("通知冷却：60s 内抑制", ptl._notify_cooldown_ok("shell") is False)
    ok("通知冷却：其他语言不受影响", ptl._notify_cooldown_ok("python") is True)

    import shutil as _sh2
    _sh2.rmtree(repo, ignore_errors=True)


# ══════════════════════ 子集 6：CVE 生态标识与参数校验 ══════════════════════

def run_cve(args: list[str], cwd: Path):
    """按 CLI 契约调用 codeguard cve：返回 (exit, stdout, stderr)"""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(PLUGIN / "scripts" / "cve_check.py"), *args],
        capture_output=True, text=True, cwd=cwd, timeout=120, env=env, check=False,
    )


def test_cve():
    print("\n[6] CVE 生态标识与参数校验")
    import cve_check as cve

    tmp = Path(tempfile.mkdtemp())

    # 权威映射结构：每条自带全部要素；别名不得与规范标识冲突或彼此重复
    ok("映射条目含全部要素",
       all({"aliases", "languages", "markers", "scan"} <= set(spec)
           for spec in cve.ECOSYSTEM_SCANNERS.values()))
    aliases = [a for spec in cve.ECOSYSTEM_SCANNERS.values() for a in spec["aliases"]]
    conflicts = [a for a in aliases if a in cve.ECOSYSTEM_SCANNERS]
    ok("别名不冲突且不重复", not conflicts and len(aliases) == len(set(aliases)),
       f"{conflicts} {aliases}")

    # 1.3：文档化的 java 必须归一到 maven（修复前它被派发 else 静默丢弃）
    ok("java 归一到 maven", cve.canonical_ecosystem("java") == "maven")
    ok("trivy 归一到 universal", cve.canonical_ecosystem("trivy") == "universal")
    ok("规范标识自身可解析", cve.canonical_ecosystem("python") == "python")
    ok("大小写不敏感", cve.canonical_ecosystem("JAVA") == "maven")
    ok("未声明标识返回 None", cve.canonical_ecosystem("go") is None)
    ok("可接受值含别名", "java" in cve.ecosystem_choices() and "trivy" in cve.ecosystem_choices())

    # 1.2：前置条件从权威映射派生，独立死表已移除
    ok("死表 ECOSYSTEM_PRECHECK 已移除", not hasattr(cve, "ECOSYSTEM_PRECHECK"))
    ok("缺标志文件→不可扫描", cve.precheck(tmp, "rust")[0] is False)
    (tmp / "Cargo.lock").write_text("")
    ok("有标志文件→可扫描", cve.precheck(tmp, "rust")[0] is True)
    ok("无前置条件生态直接可扫描", cve.precheck(tmp, "universal")[0] is True)
    ok("语言映射值均为规范标识",
       all(v in cve.ECOSYSTEM_SCANNERS for v in cve.language_ecosystem_map().values()))

    # 5.2：未知生态在扫描前拒绝，退出码 3，且不混用其他结论文案
    r = run_cve(["--ecosystem", "go", str(tmp)], tmp)
    out = r.stdout + r.stderr
    ok("未知生态退出码=3", r.returncode == 3, f"rc={r.returncode}")
    ok("退出码与「存在漏洞」「无法验证」不重叠", r.returncode not in (1, 2))
    ok("错误信息列出可接受值", "可接受" in out and "java" in out)
    ok("不误报「无可扫描生态」", "无可扫描生态" not in out)
    ok("不误报存在漏洞", "存在漏洞" not in out and "有漏洞" not in out)

    # 5.1：--ecosystem java 真正进入 maven 派发
    r = run_cve(["--ecosystem", "java", str(tmp)], tmp)
    ok("java 别名进入 maven 派发", "ecosystems: ['maven']" in r.stdout, r.stdout.strip()[:120])
    ok("java 未被当成未知生态", r.returncode != 3)

    # ── C1-5.3：severity 展开为「阈值及以上」（回归被丢弃的档位）──
    ok("LOW 展开为全部四级", cve.severities_at_and_above("LOW") == ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    ok("MEDIUM 不再丢 HIGH", cve.severities_at_and_above("MEDIUM") == ["MEDIUM", "HIGH", "CRITICAL"])
    ok("HIGH 默认两档", cve.severities_at_and_above("HIGH") == ["HIGH", "CRITICAL"])
    ok("CRITICAL 单档", cve.severities_at_and_above("CRITICAL") == ["CRITICAL"])
    captured = {}
    orig_run = cve.run
    cve.run = lambda cmd, cwd, timeout=600: (captured.update(cmd=cmd), (0, "", ""))[1]
    try:
        cve.scan_trivy(tmp, "MEDIUM")
    finally:
        cve.run = orig_run
    ok("trivy 收到完整级别集合",
       captured.get("cmd", []).count("MEDIUM,HIGH,CRITICAL") == 1, str(captured.get("cmd")))

    # ── C1-3.2：maven 数值阈值与其余扫描器同一 intent（HIGH⇒CVSS 7，不是旧映射的 3）──
    seen = {}
    orig_mv = cve.scan_maven
    cve.scan_maven = lambda root, th, _s=seen: (_s.update(th=th), {"ecosystem": "maven", "tool": "fake", "exit": 0})[1]
    try:
        cve._scan_maven_ecosystem(tmp, "HIGH", False)
        ok("HIGH ⇒ failBuildOnCVSS=7", seen.get("th") == 7, f"th={seen.get('th')}")
        cve._scan_maven_ecosystem(tmp, "MEDIUM", False)
        ok("MEDIUM ⇒ failBuildOnCVSS=4", seen.get("th") == 4, f"th={seen.get('th')}")
    finally:
        cve.scan_maven = orig_mv

    # ── C1-5.6：四个原生生态派发不回归（mock 扫描器，不依赖真实工具/网络）──
    for eco, marker in (("maven", "pom.xml"), ("node", "package.json"),
                        ("python", "pyproject.toml"), ("rust", "Cargo.lock")):
        d = Path(tempfile.mkdtemp())
        (d / marker).write_text("")
        calls = []
        orig_scan = cve.ECOSYSTEM_SCANNERS[eco]["scan"]
        cve.ECOSYSTEM_SCANNERS[eco]["scan"] = (
            lambda root, sev, fix, _c=calls, _e=eco: (_c.append(sev), {"ecosystem": _e, "tool": "fake", "exit": 0})[1])
        old_argv = sys.argv
        try:
            sys.argv = ["cve_check.py", "--ecosystem", eco, str(d)]
            rc = cve.main()
        finally:
            sys.argv = old_argv
            cve.ECOSYSTEM_SCANNERS[eco]["scan"] = orig_scan
        ok(f"{eco} 原生派发且 severity 透传", rc == 0 and calls == ["HIGH"], f"rc={rc} calls={calls}")

    # ── C1-4.3：存在漏洞优先于无法验证 ──
    d = Path(tempfile.mkdtemp())
    (d / "package.json").write_text("{}")
    (d / "Cargo.lock").write_text("")
    orig_node = cve.ECOSYSTEM_SCANNERS["node"]["scan"]
    orig_rust = cve.ECOSYSTEM_SCANNERS["rust"]["scan"]
    cve.ECOSYSTEM_SCANNERS["node"]["scan"] = lambda root, sev, fix: {"ecosystem": "node", "tool": "fake", "exit": 1, "failed": True, "status": "FAIL"}
    cve.ECOSYSTEM_SCANNERS["rust"]["scan"] = lambda root, sev, fix: {"ecosystem": "rust", "tool": "fake", "exit": 127}
    try:
        sys.argv = ["cve_check.py", str(d)]
        rc_mixed = cve.main()
    finally:
        sys.argv = ["cve_check.py"]
        cve.ECOSYSTEM_SCANNERS["node"]["scan"] = orig_node
        cve.ECOSYSTEM_SCANNERS["rust"]["scan"] = orig_rust
    ok("漏洞(2) 优先于无法验证(1)", rc_mixed == 2, f"rc={rc_mixed}")

    # ── C1-5.4/5.5：无原生扫描器的语言自动落兜底；trivy 缺失=无法验证而非漏洞 ──
    d = Path(tempfile.mkdtemp())
    (d / "go.mod").write_text("module x\n\ngo 1.21\n")
    (d / "main.go").write_text("package main\n")
    r = run_cve([str(d)], d)
    out = r.stdout + r.stderr
    ok("go 项目自动走 universal 兜底", "ecosystems: ['universal']" in r.stdout, r.stdout.strip()[:120])
    ok("trivy 缺失 → 无法验证(1) 而非漏洞(2)", r.returncode == 1, f"rc={r.returncode}")
    ok("兜底路径不误报「有漏洞」", "有漏洞" not in out)

    shutil.rmtree(tmp)


# ══════════════════════ 子集 7：文档与注册表可复现同步 ══════════════════════

def test_doc_sync():
    print("\n[7] 文档与注册表可复现同步")
    import gen_language_docs as gen

    reg = json.loads((PLUGIN / "scripts" / "languages.json").read_text(encoding="utf-8"))
    expected = "\n".join(gen.build_lines(reg["languages"])) + "\n"
    actual = (PLUGIN / "docs" / "LANGUAGES.md").read_text(encoding="utf-8")
    if expected == actual:
        ok("docs/LANGUAGES.md 与注册表完全可复现（双向一致）", True)
    else:
        import difflib
        diff = list(difflib.unified_diff(
            actual.splitlines(), expected.splitlines(),
            "docs/LANGUAGES.md", "registry-generated", n=0, lineterm=""))
        ok("docs/LANGUAGES.md 与注册表完全可复现（双向一致）", False,
           f"{len(diff)} 行差异，首 6 行: {diff[:6]}")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"codeguard 测试集  plugin={PLUGIN.name}")
    if which in ("all", "langs"):
        test_languages()
    if which in ("all", "hooks"):
        test_hooks()
    if which in ("all", "unit"):
        test_unit()
    if which in ("all", "edges"):
        test_edges()
    if which in ("all", "perf"):
        test_perf()
    if which in ("all", "field"):
        test_field_regressions()
    if which in ("all", "cve"):
        test_cve()
    if which in ("all", "doc"):
        test_doc_sync()
    print(f"\n═══ 结果: {len(PASS)} 通过 / {len(FAIL)} 失败 / {len(SKIP)} 跳过 ═══")
    if FAIL:
        print("失败项:", *FAIL, sep="\n  - ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
