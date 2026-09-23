"""可选 OpenSpec 验证适配器；进程故障保留为未验证，不生成宿主输出。"""
from __future__ import annotations

import shutil
from pathlib import Path

from .execution import execute
from .reporting import _truncate_detail


def validate(project_root: Path, timeout_seconds: int = 300) -> dict:
    if not (project_root / "openspec" / "config.yaml").is_file():
        return {"failures": [], "skipped": None}
    cli = shutil.which("openspec")
    if cli is None:
        return {"failures": [], "skipped": "openspec CLI 未安装，跳过验证"}
    try:
        proc = execute([cli, "validate", "--all", "--strict", "--no-interactive", "--json"],
                       project_root, timeout_seconds)
    except Exception as exc:  # noqa: BLE001 — 可选集成异常必须可见，保留原兼容合同
        return {"failures": [], "skipped": f"openspec validate 异常未验证: {exc!r}"}
    if proc.failure:
        return {"failures": [], "skipped": f"openspec validate 未验证: {proc.failure} {proc.stderr}"}
    if proc.returncode == 0:
        return {"failures": [], "skipped": None}
    detail = _truncate_detail(proc.stdout + proc.stderr, project_root, "openspec")
    fix = f"{cli} validate --all --strict --no-interactive"
    hint = "见 https://openspec.dev 或 `npm i -g @fission-ai/openspec`"
    return {"failures": [("openspec", detail, fix, hint)], "skipped": None}
