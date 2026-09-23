"""本地状态基础设施：锁覆盖整个读改写，替换对读者原子可见。"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

if os.name == "nt":  # Windows 也必须串行读改写，不能退化为仅原子写。
    import msvcrt
else:
    import fcntl

T = TypeVar("T")


@contextlib.contextmanager
def locked(path: Path):
    """稳定旁路锁文件，原子替换数据文件时不替换锁 inode。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a+b") as lock:
        if os.name == "nt":
            lock.seek(0, os.SEEK_END)
            if not lock.tell():
                lock.write(b"\0")
                lock.flush()
            deadline = time.monotonic() + 10
            while True:
                try:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.01)
        else:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read_json(path: Path) -> dict:
    """兼容不存在/损坏的旧 JSON；上层负责是否允许降级，不吞任意 IO 错误。"""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _replace(path: Path, content: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_private_text(path: Path, content: str) -> None:
    """以私有权限原子替换诊断日志，不向已存在的目录链接写入。"""
    if path.parent.is_symlink():
        raise OSError(f"diagnostic directory is a symlink: {path.parent}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise OSError(f"diagnostic directory is a symlink: {path.parent}")
    _replace(path, content)


def update_json(path: Path, change: Callable[[dict], T]) -> T:
    """在锁内读取、变更、替换；回调异常不写入任何部分结果。"""
    with locked(path):
        value = read_json(path)
        result = change(value)
        _replace(path, json.dumps(value, ensure_ascii=False))
        return result


def take_json(path: Path) -> dict:
    """原子消费一份状态；锁释放后的新写入留给下一轮，不被 Stop 清除。"""
    with locked(path):
        value = read_json(path)
        path.unlink(missing_ok=True)
        return value


def consume_if_unchanged(path: Path, expected: dict) -> bool:
    """输出完成后只消费原样快照；并发新写入优先保留以避免丢计数。"""
    with locked(path):
        if read_json(path) != expected:
            return False
        path.unlink(missing_ok=True)
        return True


def append_jsonl(path: Path, entry: dict, limit: int) -> None:
    """有界审计日志，保留窗口内并发写入不互相覆盖。"""
    with locked(path):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            lines = []
        lines.append(json.dumps(entry, ensure_ascii=False))
        _replace(path, "\n".join(lines[-max(1, limit):]) + "\n")
