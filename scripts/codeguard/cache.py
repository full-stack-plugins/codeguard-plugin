"""可失效的软检查缓存；缓存损坏或输入未知只导致重跑，不产生权限。"""
from __future__ import annotations

import contextlib
import hashlib
import time
from pathlib import Path

from .storage import read_json, update_json

FORMAT = 2


def cache_path(home: Path, root: Path) -> Path:
    identity = hashlib.sha256(str(root.resolve()).encode()).hexdigest()
    return home / "gate-cache" / (identity + ".json")


def load_result(path: Path, key: str | None, ttl: float) -> tuple[list, list] | None:
    if key is None:
        return None
    try:
        data = read_json(path)
        if (data.get("format") != FORMAT or data.get("key") != key
                or not isinstance(data.get("ts"), (int, float))
                or not 0 <= time.time() - data["ts"] < ttl
                or data.get("skipped") != []):
            return None
        failures = data.get("failures")
        if not isinstance(failures, list) or not all(
                isinstance(row, list) and len(row) == 4 and all(isinstance(v, str) for v in row)
                for row in failures):
            return None
        return [tuple(row) for row in failures], []
    except (OSError, ValueError):
        return None


def store_result(path: Path, key: str | None, failures: list, skipped: list) -> None:
    # 旧 tuple 协议未区分每种 skipped；保守不缓存任何部分结果，不猜测未知是否可忽略。
    if key is None or skipped:
        return
    def change(data):
        data.clear()
        data.update(format=FORMAT, key=key, ts=time.time(), failures=failures, skipped=[])
    with contextlib.suppress(OSError):
        update_json(path, change)
