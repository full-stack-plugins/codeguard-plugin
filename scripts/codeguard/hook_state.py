"""Hook 状态应用服务：归属、统计、审计和去重；不负责宿主输出。"""
from __future__ import annotations

import contextlib
import hashlib
import os
import time
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path

from .fingerprint import file_content
from .storage import append_jsonl, read_json, update_json

_SCOPE: ContextVar[str] = ContextVar("codeguard_hook_scope", default="")


def codeguard_home() -> Path:
    return Path(os.environ.get("CODEGUARD_HOME") or (Path.home() / ".codeguard"))


def scope_id() -> str:
    return _SCOPE.get()


@contextlib.contextmanager
def session_scope(payload: dict):
    """同一 session 在不同 worktree 不共享统计；无 ID 保留旧共享协议。"""
    session = payload.get("session_id")
    identity = ""
    if isinstance(session, str) and session:
        cwd = Path.cwd().resolve()
        root = next((p for p in (cwd, *cwd.parents) if (p / ".git").exists()), cwd)
        identity = hashlib.sha256((session + "\0" + str(root)).encode()).hexdigest()
    token = _SCOPE.set(identity)
    try:
        yield
    finally:
        _SCOPE.reset(token)


def session_state_path() -> Path:
    if scope_id():
        return codeguard_home() / "sessions" / (scope_id() + ".json")
    return codeguard_home() / "session_state.json"


def state_path(legacy: Path) -> Path:
    modern = session_state_path()
    # 旧记录没有归属，绝不能猜测它属于一个带 ID 的新会话。
    return modern if scope_id() or modern.exists() or not legacy.exists() else legacy


def bump_state(path: Path, lang: str, passed: bool, auto_fixed: bool = False) -> None:
    def change(state):
        entry = state.get(lang)
        if not isinstance(entry, dict):
            entry = {}
            state[lang] = entry
        for name in ("total", "passed", "failed", "auto_fixed"):
            entry.setdefault(name, 0)
        entry["total"] += 1
        entry["passed" if passed else "failed"] += 1
        entry["auto_fixed"] += int(auto_fixed)
    with contextlib.suppress(OSError):
        update_json(path, change)


def notification_allowed(path: Path, lang: str, cooldown: float) -> bool:
    def change(state):
        entry = state.get(lang)
        if not isinstance(entry, dict):
            entry = {}
            state[lang] = entry
        now = time.time()
        if 0 <= now - entry.get("last_notify", 0) < cooldown:
            return False
        entry["last_notify"] = now
        return True
    try:
        return update_json(path, change)
    except OSError:
        return True


def record_skip_event(kind: str, project_root: Path | None = None, detail: str | None = None) -> None:
    def change(state):
        meta = state.setdefault("_skip", {"count": 0, "kinds": {}})
        meta["count"] = int(meta.get("count", 0)) + 1
        kinds = meta.setdefault("kinds", {})
        kinds[kind] = int(kinds.get(kind, 0)) + 1
        events = meta.setdefault("events", [])
        events.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind,
                       "repo": project_root.name if project_root else None,
                       **({"detail": detail} if detail else {})})
        del events[:-20]
    with contextlib.suppress(OSError):
        update_json(session_state_path(), change)


def record_gate_decision(project_root: Path, lang: str, cmd: list[str], rc: int,
                         status: str, reason: str, limit: int = 500,
                         *, execution_root: Path | None = None) -> None:
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "repo": project_root.name,
             "worktree": str(project_root.resolve()), "lang": lang, "cmd": list(cmd),
             "rc": rc, "status": status, "reason": reason,
             "session_scope": scope_id(),
             "execution_root": str((execution_root or project_root).resolve())}
    with contextlib.suppress(OSError):
        append_jsonl(codeguard_home() / "gate-decisions.jsonl", entry, limit)


def should_suppress_event(key: str, window: float = 2.0) -> bool:
    """观察型事件短时去重；不能用它替代硬门禁结果。"""
    digest = hashlib.sha256((scope_id() + "\0" + key).encode()).hexdigest()
    def change(state):
        now = time.time()
        last = state.get(digest) or {}
        suppressed = 0 <= now - last.get("ts", 0) < window
        for stale in [k for k, v in state.items() if not 0 <= now - v.get("ts", 0) < 60]:
            state.pop(stale)
        state[digest] = {"ts": last["ts"] if suppressed else now}
        return suppressed
    try:
        return update_json(codeguard_home() / "event_dedup.json", change)
    except (OSError, ValueError):
        return False


def _file_key(path: str) -> str:
    return hashlib.sha256((scope_id() + "\0" + str(Path(path).resolve())).encode()).hexdigest()


def _file_stamp(path: str) -> str:
    return file_content(Path(path))[0]


def completed_file_check(path: str, store: Path, identity: str | None = None) -> bool:
    """只读已完成结果；未开始/未验证的检查不能先占用去重标记。"""
    try:
        last = read_json(store).get(_file_key(path)) or {}
        return (last.get("identity") == identity and last.get("stamp") == _file_stamp(path)
                and 0 <= time.time() - last.get("ts", 0) < 2)
    except (OSError, ValueError):
        return False


def record_file_check(path: str, store: Path, identity: str | None = None) -> None:
    try:
        stamp = _file_stamp(path)
        def change(state):
            now = time.time()
            for stale in [k for k, v in state.items() if not 0 <= now - v.get("ts", 0) < 60]:
                state.pop(stale)
            state[_file_key(path)] = {"stamp": stamp, "identity": identity, "ts": now}
        update_json(store, change)
    except (OSError, ValueError):
        pass


def _event_key(key: str) -> str:
    return hashlib.sha256((scope_id() + "\0" + key).encode()).hexdigest()


def completed_event(key: str) -> dict | None:
    """仅返回已完成的宿主结果；未完成事件不存在可放行的占位记录。"""
    try:
        result = read_json(codeguard_home() / "gate_event_results.json").get(_event_key(key))
        if (isinstance(result, dict) and 0 <= time.time() - result.get("ts", 0) < 2
                and result.get("code") in (0, 2)
                and isinstance(result.get("stdout"), str) and isinstance(result.get("stderr"), str)):
            return result
    except (OSError, ValueError):
        pass
    return None


def record_completed_event(key: str, code: int, stdout: str, stderr: str) -> None:
    def change(state):
        now = time.time()
        for stale in [k for k, v in state.items() if not 0 <= now - v.get("ts", 0) < 60]:
            state.pop(stale)
        state[_event_key(key)] = {"ts": now, "code": code, "stdout": stdout, "stderr": stderr}
    with contextlib.suppress(OSError):
        update_json(codeguard_home() / "gate_event_results.json", change)


def observe_once(key: str | None, operation: Callable[[], int]) -> int:
    """观察完成后才去重；异常可重试，并发未完成的副本允许重复观察。"""
    if key and completed_event(key) is not None:
        return 0
    code = operation()
    if key and code == 0:
        record_completed_event(key, code, "", "")
    return code
