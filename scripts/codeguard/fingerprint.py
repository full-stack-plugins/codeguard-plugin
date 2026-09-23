"""有预算的输入身份采集；不是安全快照，失败时拒绝生成缓存身份。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

from .execution import execute

MAX_FILES = 10000
MAX_BYTES = 64 * 1024 * 1024

# 即使被 gitignore 忽略，这些常见根配置也影响检查；任意外部动态配置不在缓存证明范围内。
CONFIG_NAMES = (
    "codeguard.json", "pyproject.toml", "ruff.toml", ".ruff.toml", "setup.cfg", "tox.ini",
    "package.json", "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    ".eslintrc", ".eslintrc.json", ".eslintrc.js", ".eslintrc.cjs", ".eslintignore",
    "tsconfig.json", "Cargo.toml", "Cargo.lock", "pom.xml", "build.gradle", "build.gradle.kts",
    ".shellcheckrc", ".golangci.yml", ".golangci.yaml", ".prettierrc", ".prettierignore",
)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _git(root: Path, *args: str) -> str | None:
    result = execute(["git", *args], root, 15)
    # 无法往返编码的路径不能生成看似可靠的键。
    return result.stdout if result.returncode == 0 and "\ufffd" not in result.stdout else None


def file_content(path: Path, budget: int = MAX_BYTES) -> tuple[str, int]:
    """散列普通文件内容和权限；拒绝符号链接/设备及读取期间变化。"""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > budget:
        raise ValueError("无法在缓存预算内读取普通文件")
    total = 0
    h = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("读取前文件被替换")
        while chunk := stream.read(min(65536, budget - total + 1)):
            total += len(chunk)
            if total > budget:
                raise ValueError("文件增长超过缓存预算")
            h.update(chunk)
        after = os.fstat(stream.fileno())
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("读取期间文件变化")
    return digest([h.hexdigest(), stat.S_IMODE(after.st_mode)]), total


def repository_identity(root: Path, *, extra_files=(), max_files: int = MAX_FILES,
                        max_bytes: int = MAX_BYTES) -> str | None:
    """Git 内容索引兼容 linked worktree；NUL 分隔保留空格与换行文件名。"""
    root = root.resolve()
    listing = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    index = _git(root, "ls-files", "--stage", "-z")
    if listing is None or index is None:
        return None
    names = set(listing.rstrip("\0").split("\0")) - {""}
    names.update(CONFIG_NAMES)
    names.update(str(p) for p in extra_files)
    if len(names) > max_files:
        return None
    records = []
    remaining = max_bytes
    try:
        for name in sorted(names):
            path = root / name
            if not path.resolve().is_relative_to(root):
                return None
            try:
                content, used = file_content(path, remaining)
                remaining -= used
            except FileNotFoundError:
                content = "missing"
            records.append((name, content))
        return digest({"root": str(root), "head": _git(root, "rev-parse", "--verify", "HEAD"),
                       "index": index, "upstream": _git(root, "rev-parse", "--verify", "@{upstream}"),
                       "files": records})
    except (OSError, ValueError):
        return None


def check_identity(root: Path, config: dict, definitions: dict, *, extra_files=()) -> str | None:
    """输入内容、实际参数、配置及本地工具身份的摘要，不落盘环境明文。"""
    declared = set(extra_files)
    tools = []
    try:
        for definition in definitions.values():
            for pattern in definition.get("requiresConfig") or []:
                declared.update(str(p.relative_to(root)) for p in root.glob(pattern))
            for key in ("lint", "gate", "format", "probe"):
                command = definition.get(key) or []
                if not command:
                    continue
                executable = shutil.which(command[0]) or command[0]
                for arg in [executable, *command[1:]]:
                    path = Path(arg)
                    if not path.is_absolute():
                        path = root / path
                    if path.is_file():
                        info = path.stat()
                        tools.append((str(path.resolve()), info.st_size, info.st_mtime_ns,
                                      info.st_ctime_ns, info.st_mode))
        tree = repository_identity(root, extra_files=declared)
        if tree is None:
            return None
        environment = {key: os.environ.get(key) for key in
                       ("PATH", "JAVA_HOME", "NODE_OPTIONS", "PYTHONPATH", "VIRTUAL_ENV", "RUSTUP_TOOLCHAIN")}
        return digest({"inputs": tree, "config": config, "commands": definitions,
                       "tools": tools, "environment": environment})
    except (OSError, ValueError):
        return None
