"""只读 index/HEAD，物化一次性检查目录；从不 stash、checkout 或改写用户 index。"""
from __future__ import annotations

import contextlib
import os
import subprocess
import tempfile
from pathlib import Path, PurePosixPath


class SnapshotError(RuntimeError):
    """无法准确取得拟提交内容，调用者必须报告未验证。"""


def git(root: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True,
                              check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SnapshotError(str(exc)) from exc
    if proc.returncode:
        raise SnapshotError(proc.stderr.decode(errors="replace")[:500])
    return proc.stdout


def names(root: Path, *args: str) -> set[str]:
    return {os.fsdecode(p) for p in git(root, *args).split(b"\0") if p}


def safe_path(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if not parts or PurePosixPath(name).is_absolute() or ".." in parts or ".git" in parts:
        raise SnapshotError(f"不安全的快照路径: {name}")
    return root.joinpath(*parts)


def push_paths(root: Path, include_deleted=False) -> set[str]:
    for base in ("@{upstream}", "origin/" + git(root, "branch", "--show-current").decode().strip(),
                 "origin/main", "origin/master"):
        try:
            return names(root, "diff", "--name-only", "--diff-filter=ACMRD" if include_deleted else "--diff-filter=ACMR",
                         "--no-renames", "-z", f"{base}...HEAD")
        except SnapshotError:
            continue
    # 首次推送不能因为没有 upstream 而把整个 HEAD 当成已验证。
    return names(root, "ls-tree", "-r", "--name-only", "-z", "HEAD")


def overlays(root: Path, lanes=None, extra=None) -> set[str]:
    selected: set[str] = set()
    if "unstaged" in (lanes or ()):
        selected |= names(root, "diff", "--name-only", "-z")
    if "untracked" in (lanes or ()):
        selected |= names(root, "ls-files", "--others", "--exclude-standard", "-z")
    for name in extra or ():
        path = safe_path(root, name)
        # extra 已由暂存意图解析；文件名中的 * / : 不得再触发 pathspec。
        # --literal-pathspecs 仍让目录参数递归展开，保留旧字面目录调用面。
        selected |= names(root, "--literal-pathspecs", "ls-files", "--cached", "--others",
                          "--exclude-standard", "-z", "--", name)
        if path.is_file() or path.is_symlink():
            selected.add(name)
    return selected


def proposed_paths(root: Path, mode="commit", *, lanes=None, extra=None,
                   pending_commit=False, include_deleted=False) -> list[str]:
    """拟入库的新/修改路径，保留敏感文件与产物，删除文件不算新入库。"""
    selected = push_paths(root, include_deleted) if mode == "push" else set()
    if mode != "push" or pending_commit:
        selected |= names(root, "diff", "--cached", "--name-only", "--no-renames",
                          "--diff-filter=ACMRD" if include_deleted else "--diff-filter=ACMR", "-z")
        for name in overlays(root, lanes, extra):
            path = safe_path(root, name)
            if include_deleted or path.exists() or path.is_symlink():
                selected.add(name)
            else:
                selected.discard(name)
    return sorted(selected)


@contextlib.contextmanager
def validation_tree(root: Path, mode="commit", *, lanes=None, extra=None, pending_commit=False):
    """原始 Git blobs 构成快照；拒绝外链、submodule、冲突和超限内容。"""
    head = mode == "push" and not pending_commit
    raw = git(root, "ls-tree", "-r", "-z", "HEAD") if head else git(root, "ls-files", "--stage", "-z")
    entries = []
    for line in raw.split(b"\0"):
        if not line:
            continue
        meta, filename = line.split(b"\t", 1)
        mode_bits, middle, last = meta.decode().split()
        oid = last if head else middle
        if mode_bits not in ("100644", "100755") or (not head and last != "0"):
            raise SnapshotError("符号链接、子模块或未解决冲突需要独立检查")
        entries.append((mode_bits, oid, os.fsdecode(filename)))
    if len(entries) > 20000:
        raise SnapshotError("快照超过 20000 文件上限，需要独立 CI 检查")
    object_ids = "".join(oid + "\n" for _, oid, _ in entries).encode()
    try:
        sizes = subprocess.run(["git", "cat-file", "--batch-check"], input=object_ids,
                               cwd=root, capture_output=True, check=True, timeout=30).stdout
        if sum(int(line.split()[-1]) for line in sizes.splitlines()) > 256 * 1024 * 1024:
            raise SnapshotError("快照超过 256 MiB 上限，需要独立 CI 检查")
        blob = subprocess.run(["git", "cat-file", "--batch"], input=object_ids,
                              cwd=root, capture_output=True, check=True, timeout=30).stdout
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        raise SnapshotError(f"读取 Git 内容失败: {exc}") from exc
    changed = proposed_paths(root, mode, lanes=lanes, extra=extra, pending_commit=pending_commit, include_deleted=True)
    with tempfile.TemporaryDirectory(prefix="codeguard-snapshot-") as directory:
        target = Path(directory)
        offset = 0
        for mode_bits, _oid, name in entries:
            end = blob.index(b"\n", offset)
            size = int(blob[offset:end].split()[-1])
            dest = safe_path(target, name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob[end + 1:end + 1 + size])
            dest.chmod(0o755 if mode_bits == "100755" else 0o644)
            offset = end + size + 2
        if not head:
            for name in overlays(root, lanes, extra):
                source, dest = safe_path(root, name), safe_path(target, name)
                if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
                    raise SnapshotError(f"不跟随仓外路径/符号链接: {name}")
                if source.is_file():
                    if source.stat().st_size > 32 * 1024 * 1024:
                        raise SnapshotError(f"工作树文件过大: {name}")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(source.read_bytes())
                    dest.chmod(source.stat().st_mode & 0o777)
                elif dest.is_file():
                    dest.unlink()
        yield target, changed
