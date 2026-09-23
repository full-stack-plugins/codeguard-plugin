"""基线证据比较；无基线或未验证时绝不授予存量豁免。"""
from __future__ import annotations

from pathlib import Path

from .execution import execute


def _git(project_root: Path, *args: str) -> str | None:
    outcome = execute(["git", *args], project_root, 15)
    return outcome.stdout if outcome.returncode == 0 else None


def _mentioned_files(full: str, project_root: Path) -> set[str]:
    """从 linter 输出提取"提到的、且在仓内真实存在的"文件（仓根相对路径）。

    两类通行格式：`path/file.ext:12:`（javadoc/ruff/pylint/mvn——绝对路径先剥
    仓根前缀）与 `In path/file.ext line 12`（shellcheck）。只收 root 下真实
    存在的路径——裸 token（`version:1`）被存在性过滤挡掉。
    """
    import re
    root = Path(project_root)
    found: set[str] = set()
    pats = (
        # path/file.ext:12:（javadoc 绝对路径 / ruff / mvn）——目录前缀可选：
        # ruff 在仓根输出裸文件名 `old.py:1:1:`，强制含 / 会漏归因（实测）。
        # 无点的裸 token（SC2086:1 / version:1）不会命中；命中的再过存在性。
        re.compile(r"((?:[A-Za-z]:)?(?:/?(?:[\w.\-]+/)*)[\w.\-]+\.[A-Za-z0-9]+):\d+"),
        re.compile(r"\bIn ((?:[\w.\-]+/)+[\w.\-]+\.[A-Za-z0-9]+) line \d+"),
    )
    for pat in pats:
        for m in pat.findall(full):
            p = m
            root_s = str(root)
            if p.startswith(root_s + "/"):
                p = p[len(root_s) + 1:]
            p = p.lstrip("./")
            if p.startswith("/"):
                continue  # 仓外绝对路径不归因
            if (root / p).exists():
                found.add(p)
    return found


def _stale_attribution(full: str, project_root: Path, lang: str, lang_files: list[str]) -> str | None:
    """[已弃用·保留接口] delta 失败路径下的"历史债"弱归因。

    verdict-integrity 原则：**真正的豁免必须有基线复跑证据**（双跑
    baseline_stale_finding）——本函数对此**永远不豁免**，遵循"宁可误拦
    不误放行"：只靠失败文件是否在改动集推断存量债是危险的（同名文件被
    替换时也会"不在改动集"，但其实是新债），必须有 baseline_ref 上同
    命令同工具的实际复跑才能豁免。

    历史与契约：
    - 入口仍保留以兼容 tests/test_verdict_integrity.py 与 test_session_fixes
      中的调用；这些测试断言本函数返回 None（不豁免），本实现亦满足。
    - 真正的豁免路径在本模块 baseline_stale_finding，由 gate_checks 对实际 FAIL 调用。
    - 保留该旧导入面，但不作为位置启发式放行的扩展入口。

    本函数当前实现永远返回 None。
    """
    return None


def baseline_stale_finding(
    project_root: Path, rel_path: str, base_cmd: list[str], output: str, timeout: int = 60,
    *,
    baseline_ref: str = "HEAD",
) -> str | None:
    """同命令同工具跑**改动前版本**：基线已存在相同发现 → 存量豁免说明；否则 None。

    verdict-integrity 既有原则：**无基线证据绝不豁免**（`_stale_attribution` 因
    此恒返回 None）。本函数首次落地"双跑基线"：把 baseline_ref:<path> 的内容
    写到临时文件、用同一条 linter 命令跑一遍，两次输出各取逐条诊断与
    出现次数；只有基线本身确认失败且覆盖当前每条发现才可豁免。
    基线为空/提不出诊断/基线跑不起来 → 一律不豁免。

    baseline_ref 必须是"改动前"：commit 面（工作树/暂存改动）用 HEAD；push 面
    （检查未推送提交）必须用 @{upstream}——坏提交已经进了 HEAD，拿 HEAD 当基线
    会把本次新引入的坏内容误判成存量（实测踩过：push 面坏提交被豁免放行）。
    """
    from .verdict import FAIL, finding_instances, lint_verdict
    pre = _git(project_root, "show", f"{baseline_ref}:{rel_path}")
    if pre is None:
        return None
    new_sigs = finding_instances(output)
    if not new_sigs:
        return None
    import tempfile as _tf
    with _tf.TemporaryDirectory(prefix="cg-baseline-") as td:
        tmp = Path(td) / ("baseline" + (Path(rel_path).suffix or ".txt"))
        try:
            tmp.write_text(pre, encoding="utf-8", errors="replace")
        except OSError:
            return None
        joined = " ".join(base_cmd)
        cmd = ([c.replace("{file}", str(tmp)) for c in base_cmd] if "{file}" in joined
               else list(base_cmd) + [str(tmp)])
        proc = execute(cmd, project_root, timeout)
        if lint_verdict(proc.returncode, cmd, proc.stdout + proc.stderr)[0] != FAIL:
            return None
        base_sigs = finding_instances((proc.stdout or "") + (proc.stderr or ""))
    if not base_sigs:
        return None
    return ("存量问题（基线同命令同工具已存在）" if
            all(count <= base_sigs[diagnostic] for diagnostic, count in new_sigs.items()) else None)
