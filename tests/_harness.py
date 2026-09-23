"""tests/_harness.py：run_all 回归集共享夹具（ok/skip 收集、宿主协议钩子触发、临时 git 仓）。"""
from __future__ import annotations

import json
import os
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
