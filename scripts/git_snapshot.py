"""只读 index/HEAD，物化一次性检查目录；从不 stash、checkout 或改写用户 index。"""
from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import stat
import tempfile
from pathlib import Path, PurePosixPath

from codeguard.execution import execute_bytes

_LISTING_MAX_BYTES = 16 * 1024 * 1024
_MAX_BLOB_BYTES = 256 * 1024 * 1024
_MAX_OVERLAY_FILE_BYTES = 32 * 1024 * 1024
_MAX_OVERLAY_BYTES = 256 * 1024 * 1024
_MAX_OVERLAY_FILES = 20000
_COPY_CHUNK_BYTES = 64 * 1024


class SnapshotError(RuntimeError):
    """无法准确取得拟提交内容，调用者必须报告未验证。"""


def git(root: Path, *args: str, input_data: bytes | None = None,
        max_output_bytes: int = _LISTING_MAX_BYTES) -> bytes:
    proc = execute_bytes(["git", *args], root, 30, input_data=input_data,
                         stdin_null=True, max_output_bytes=max_output_bytes)
    if proc.failure:
        raise SnapshotError(f"Git 执行未验证 ({proc.failure}): " +
                            proc.stderr.decode(errors="replace")[-500:])
    if proc.returncode:
        raise SnapshotError(proc.stderr.decode(errors="replace")[:500])
    return proc.stdout


def _nul_records(raw: bytes) -> list[bytes]:
    """Git -z 响应必须按完整记录结束，不能丢弃半条或空记录。"""
    if not raw:
        return []
    if not raw.endswith(b"\0"):
        raise SnapshotError("Git 路径列表缺少终止 NUL")
    records = raw[:-1].split(b"\0")
    if any(not record for record in records):
        raise SnapshotError("Git 路径列表包含空记录")
    return records


def names(root: Path, *args: str) -> set[str]:
    return {os.fsdecode(record) for record in _nul_records(git(root, *args))}


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
                   pending_commit=False, include_deleted=False,
                   overlay_paths: set[str] | None = None) -> list[str]:
    """拟入库的新/修改路径，保留敏感文件与产物，删除文件不算新入库。"""
    selected = push_paths(root, include_deleted) if mode == "push" else set()
    if mode != "push" or pending_commit:
        selected |= names(root, "diff", "--cached", "--name-only", "--no-renames",
                          "--diff-filter=ACMRD" if include_deleted else "--diff-filter=ACMR", "-z")
        candidate_paths = overlays(root, lanes, extra) if overlay_paths is None else overlay_paths
        for name in candidate_paths:
            path = safe_path(root, name)
            if include_deleted or path.exists() or path.is_symlink():
                selected.add(name)
            else:
                selected.discard(name)
    return sorted(selected)


def _batch_header(line: bytes, oid: str, *, expected_size: int | None = None) -> int:
    """验证 cat-file 单项响应，不能只相信响应声明的长度。"""
    fields = line.split(b" ")
    if len(fields) != 3 or fields[0] != oid.encode("ascii") or fields[1] != b"blob":
        raise SnapshotError("Git 对象批量响应身份或类型与 index/HEAD 不一致")
    try:
        size = int(fields[2])
    except ValueError as exc:
        raise SnapshotError("Git 对象批量响应大小无效") from exc
    if size < 0 or (expected_size is not None and size != expected_size):
        raise SnapshotError("Git 对象批量响应大小与 index/HEAD 不一致")
    return size


def _batch_sizes(raw: bytes, entries: list[tuple[str, str, str]]) -> tuple[int, ...]:
    """严格核对 batch-check 的数量、顺序与总量预算。"""
    if entries and not raw.endswith(b"\n"):
        raise SnapshotError("Git 对象大小响应不完整")
    lines = raw[:-1].split(b"\n") if raw else []
    if len(lines) != len(entries):
        raise SnapshotError("Git 对象大小响应数量与 index/HEAD 不一致")
    sizes = []
    total = 0
    for line, (_, oid, _) in zip(lines, entries, strict=True):
        size = _batch_header(line, oid)
        total += size
        if total > _MAX_BLOB_BYTES:
            raise SnapshotError("快照超过 256 MiB 上限，需要独立 CI 检查")
        sizes.append(size)
    return tuple(sizes)


def _batch_blob(raw: bytes, offset: int, oid: str, expected_size: int) -> tuple[memoryview, int]:
    """只交付身份、大小和完整分隔符均已验证的 blob 字节。"""
    header_end = raw.find(b"\n", offset)
    if header_end < 0:
        raise SnapshotError("Git 对象内容响应缺少头部")
    size = _batch_header(raw[offset:header_end], oid, expected_size=expected_size)
    start = header_end + 1
    end = start + size
    if end >= len(raw) or raw[end] != 10:
        raise SnapshotError("Git 对象内容响应截断或分隔符无效")
    content = memoryview(raw)[start:end]
    if len(oid) == 40:
        digest = hashlib.sha1()
    elif len(oid) == 64:
        digest = hashlib.sha256()
    else:
        raise SnapshotError("Git 对象 ID 格式未验证")
    digest.update(f"blob {size}\0".encode("ascii"))
    digest.update(content)
    if digest.hexdigest() != oid:
        raise SnapshotError("Git 对象内容哈希与 index/HEAD 不一致")
    return content, end + 1


def _snapshot_entries(root: Path, head: bool) -> list[tuple[str, str, str]]:
    """严格解析对象列表，并以独立的路径列举发现完整记录边界上的漏项。"""
    listing = ("ls-tree", "-r", "-z", "HEAD") if head else ("ls-files", "--stage", "-z")
    records = _nul_records(git(root, *listing))
    if len(records) > 20000:
        raise SnapshotError("快照超过 20000 文件上限，需要独立 CI 检查")
    object_format = git(root, "rev-parse", "--show-object-format").strip()
    oid_size = {b"sha1": 40, b"sha256": 64}.get(object_format)
    if oid_size is None:
        raise SnapshotError("Git 对象格式未验证")
    entries = []
    seen = set()
    for record in records:
        metadata, separator, filename = record.partition(b"\t")
        if not separator or not filename or filename in seen:
            raise SnapshotError("Git 对象列表路径缺失或重复")
        seen.add(filename)
        fields = metadata.split(b" ")
        if len(fields) != 3:
            raise SnapshotError("Git 对象列表元数据无效")
        mode_bits, second, third = fields
        if mode_bits not in (b"100644", b"100755"):
            raise SnapshotError("符号链接、子模块或未解决冲突需要独立检查")
        if head:
            if second != b"blob":
                raise SnapshotError("Git 树对象不是 blob")
            oid = third
        else:
            if third != b"0":
                raise SnapshotError("Git index 存在未解决冲突")
            oid = second
        if not re.fullmatch(rb"[0-9a-f]{%d}" % oid_size, oid):
            raise SnapshotError("Git 对象列表 ID 与仓库格式不一致")
        name = os.fsdecode(filename)
        safe_path(root, name)
        entries.append((mode_bits.decode("ascii"), oid.decode("ascii"), name))
    expected = (names(root, "ls-tree", "-r", "--name-only", "-z", "HEAD") if head
                else names(root, "ls-files", "--cached", "-z"))
    if {name for _, _, name in entries} != expected:
        raise SnapshotError("Git 对象列表与独立路径列举不一致")
    return entries


def _copy_overlay(source: Path, dest: Path, remaining_bytes: int) -> int:
    """以源文件描述符和有界块复制预测内容；资源不足不交付半成品。"""
    cap = min(_MAX_OVERLAY_FILE_BYTES, remaining_bytes)
    if cap < 0:
        raise SnapshotError("工作树覆盖层超过总量上限")
    try:
        descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                             getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as reader:
            before = os.fstat(reader.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise SnapshotError(f"工作树覆盖层包含特殊文件: {source}")
            if before.st_size > cap:
                raise SnapshotError(f"工作树覆盖层超过单文件或总量上限: {source}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            # 仅在一次性临时树内清理被普通文件替换的旧 Git 目录。
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            copied = 0
            with dest.open("wb") as writer:
                while chunk := reader.read(min(_COPY_CHUNK_BYTES, cap - copied + 1)):
                    copied += len(chunk)
                    if copied > cap:
                        raise SnapshotError(f"工作树覆盖层读取时超过上限: {source}")
                    writer.write(chunk)
            after = os.fstat(reader.fileno())
            if copied != before.st_size or after.st_size != before.st_size or \
                    after.st_mtime_ns != before.st_mtime_ns:
                raise SnapshotError(f"工作树覆盖层读取期间发生变化: {source}")
            dest.chmod(before.st_mode & 0o777)
            return copied
    except OSError as exc:
        raise SnapshotError(f"工作树覆盖层无法读取: {source}: {exc}") from exc


def _head_revision(root: Path) -> bytes:
    """返回 HEAD 提交 ID；尚无 HEAD 提交（如首次提交前）用空字节表示。"""
    proc = execute_bytes(["git", "rev-parse", "--verify", "-q", "HEAD"], root, 30,
                         stdin_null=True, max_output_bytes=1024)
    if proc.failure:
        raise SnapshotError(f"Git HEAD 身份未验证 ({proc.failure})")
    if proc.returncode == 1 and not proc.stdout and not proc.stderr:
        return b""
    identity = proc.stdout.strip()
    if proc.returncode or not re.fullmatch(rb"(?:[0-9a-f]{40}|[0-9a-f]{64})", identity):
        raise SnapshotError("Git HEAD 身份读取失败")
    return identity


def _verify_object_list_unchanged(root: Path, head: bool,
                                  expected: list[tuple[str, str, str]],
                                  head_oid: bytes) -> None:
    """复核路径、模式、对象 ID 和 HEAD 比较基线；不改真实 index。"""
    if (_snapshot_entries(root, head) != expected
            or _head_revision(root) != head_oid):
        raise SnapshotError("Git index/HEAD 对象列表在快照检查期间变化")


@contextlib.contextmanager
def validation_tree(root: Path, mode="commit", *, lanes=None, extra=None, pending_commit=False):
    """原始 Git blobs 构成快照；拒绝外链、submodule、冲突和超限内容。"""
    head = mode == "push" and not pending_commit
    head_oid = _head_revision(root)
    entries = _snapshot_entries(root, head)
    object_ids = "".join(oid + "\n" for _, oid, _ in entries).encode()
    sizes = _batch_sizes(git(root, "cat-file", "--batch-check", input_data=object_ids,
                             max_output_bytes=max(1024, 128 * len(entries))), entries)
    blob = git(root, "cat-file", "--batch", input_data=object_ids,
               max_output_bytes=max(1024, sum(sizes) + 128 * len(entries)))
    selected_overlays = overlays(root, lanes, extra) if not head else set()
    changed = proposed_paths(root, mode, lanes=lanes, extra=extra, pending_commit=pending_commit,
                             include_deleted=True, overlay_paths=selected_overlays)
    with tempfile.TemporaryDirectory(prefix="codeguard-snapshot-") as directory:
        target = Path(directory)
        offset = 0
        for (mode_bits, oid, name), size in zip(entries, sizes, strict=True):
            content, offset = _batch_blob(blob, offset, oid, size)
            dest = safe_path(target, name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            dest.chmod(0o755 if mode_bits == "100755" else 0o644)
        if offset != len(blob):
            raise SnapshotError("Git 对象内容响应存在多余尾部字节")
        if not head:
            if len(selected_overlays) > _MAX_OVERLAY_FILES:
                raise SnapshotError("工作树覆盖层超过文件数量上限")
            copied_total = 0
            # 父路径先处理：文件转目录时须先移除旧 blob，才能写入新子项。
            for name in sorted(selected_overlays, key=lambda value: (value.count("/"), value)):
                source, dest = safe_path(root, name), safe_path(target, name)
                if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
                    raise SnapshotError(f"不跟随仓外路径/符号链接: {name}")
                if source.is_file():
                    copied_total += _copy_overlay(source, dest, _MAX_OVERLAY_BYTES - copied_total)
                elif source.exists() and not source.is_dir():
                    raise SnapshotError(f"工作树覆盖层包含特殊文件: {name}")
                elif dest.is_file():
                    dest.unlink()
        _verify_object_list_unchanged(root, head, entries, head_oid)
        yield target, changed
        _verify_object_list_unchanged(root, head, entries, head_oid)
