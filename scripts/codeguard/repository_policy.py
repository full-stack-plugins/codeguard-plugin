"""仓库路径安全与显式豁免；不处理宿主协议或语言检查。"""
from __future__ import annotations

import os
from pathlib import Path

from git_snapshot import proposed_paths

from .execution import execute
from .hook_state import record_skip_event
from .path_policy import check_paths

_ENV_TRUE_VALUES = ("1", "true", "yes")


def env_skip_gate() -> bool:
    """环境变量豁免：只认 1/true/yes（与 skip_gate_via_git_config 同值词表）。

    存在性判断是缺陷：CODEGUARD_SKIP_GATE=0 曾被当真值**静默关闭门禁**，
    而 config 路径是严格词表——两条豁免路径值语义必须一致。
    """
    return os.environ.get("CODEGUARD_SKIP_GATE", "").strip().lower() in _ENV_TRUE_VALUES


def check_commit_safety(project_root: Path, mode: str, *, lanes=None, extra=None,
                        pending_commit=False) -> list[tuple[str, str, str]]:
    paths = proposed_paths(project_root, mode, lanes=lanes, extra=extra,
                           pending_commit=pending_commit)
    return check_paths(paths)


def skip_gate_via_git_config(project_root: Path) -> bool:
    """失败重试两次；不存在的配置是未豁免，进程失败另记审计。"""
    last_error = ""
    for _ in range(2):
        outcome = execute(["git", "config", "--get", "codeguard.skipGate"], project_root, 3)
        if outcome.failure:
            last_error = outcome.stderr or outcome.failure
            continue
        return outcome.returncode == 0 and outcome.stdout.strip().lower() in ("true", "1", "yes")
    record_skip_event("skipGate-read-error", project_root,
                      detail=f"git config 读取失败(重试2次): {last_error}")
    return False
