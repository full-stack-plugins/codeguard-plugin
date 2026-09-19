#!/usr/bin/env python3
"""Vendor externally maintained Agent Skills into this plugin.

The source skill package is the single source of truth. This plugin keeps a
checksummed snapshot so an installed plugin remains complete and usable
without fetching another repository at runtime.

Only skill names listed in ``skills.lock.json`` are managed. Unlisted
directories under ``skills/`` are plugin-local custom skills and are never
removed or overwritten by this tool.

Commands:
  update  Fetch pinned sources, replace managed skill directories, and refresh
          resolved commits and per-skill digests.
  check   Verify the snapshot against the lockfile and, unless ``--offline``,
          verify the pinned upstream ref and content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def fail(message: str) -> None:
    print(f"ERROR: {message}")


def hash_skill_dir(skill_dir: Path) -> str:
    """Return a deterministic digest over every file in one skill."""
    digest = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(skill_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def resolve_ref(repo: str, ref: str) -> str:
    """Resolve a branch or lightweight/annotated tag to its commit SHA."""
    result = subprocess.run(
        ["git", "ls-remote", repo, ref, f"{ref}^{{}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not result:
        raise RuntimeError(f"{repo}: ref '{ref}' not found")

    resolved = None
    for line in result.splitlines():
        candidate, _, remote_name = line.partition("\t")
        short = remote_name.removeprefix("refs/tags/").removeprefix("refs/heads/")
        if short == f"{ref}^{{}}":
            resolved = candidate
        elif short == ref and resolved is None:
            resolved = candidate
    if resolved is None:
        raise RuntimeError(f"{repo}: could not resolve ref '{ref}'")
    return resolved


def fetch_checkout(repo: str, ref: str, workdir: Path) -> Path:
    """Fetch one pinned ref into an isolated checkout."""
    checkout = workdir / "checkout"
    subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin", repo], check=True)
    subprocess.run(
        ["git", "-C", str(checkout), "fetch", "--quiet", "--depth", "1", "origin", ref],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(checkout), "checkout", "--quiet", "--detach", "FETCH_HEAD"],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    print(f"fetched {repo}@{ref} -> {head}")
    return checkout


def load_lock(path: Path) -> dict:
    """Read and validate the lockfile version."""
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("version") != 1:
        raise RuntimeError(f"unsupported lockfile version: {lock.get('version')}")
    if not isinstance(lock.get("sources"), list) or not lock["sources"]:
        raise RuntimeError("lockfile requires a non-empty sources list")
    return lock


def validate_source(source: dict, root: Path) -> Path:
    """Validate one source entry and return its safe destination."""
    for key in ("package", "repo", "ref", "skills", "dest"):
        if key not in source:
            raise RuntimeError(f"source {source.get('package', '?')}: missing key '{key}'")
    if not isinstance(source["skills"], list) or not source["skills"]:
        raise RuntimeError(f"{source['package']}: skills must be a non-empty list")
    if len(source["skills"]) != len(set(source["skills"])):
        raise RuntimeError(f"{source['package']}: duplicate skill names in lock entry")
    for name in source["skills"]:
        if not isinstance(name, str) or not SKILL_NAME_RE.match(name):
            raise RuntimeError(f"{source['package']}: illegal skill name '{name}'")

    destination = (root / source["dest"]).resolve()
    if root != destination and root not in destination.parents:
        raise RuntimeError(f"{source['package']}: dest escapes repository root")
    return destination


def validate_no_cross_source_collisions(lock: dict) -> None:
    """Reject two upstream sources that manage the same destination skill."""
    owners: dict[tuple[str, str], str] = {}
    for source in lock["sources"]:
        names = source.get("skills", [])
        if len(names) != len(set(names)):
            raise RuntimeError(
                f"{source.get('package', '?')}: duplicate skill names in lock entry"
            )
        for name in names:
            key = (source.get("dest", ""), name)
            previous = owners.get(key)
            if previous:
                raise RuntimeError(
                    f"skill collision: {name} is managed by both {previous} and {source.get('package')}"
                )
            owners[key] = source.get("package", "?")


def source_checkout(source: dict, overrides: dict[str, str], workdir: Path) -> tuple[Path, str]:
    """Return ``(checkout, resolved_sha)`` for one source."""
    package = source["package"]
    if package in overrides:
        local = Path(overrides[package]).resolve()
        if not local.is_dir():
            raise RuntimeError(f"{package}: --source-path '{local}' is not a directory")
        sha = subprocess.run(
            ["git", "-C", str(local), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        print(f"using local override for {package}: {local} @ {sha}")
        return local, sha

    sha = resolve_ref(source["repo"], source["ref"])
    checkout = fetch_checkout(source["repo"], source["ref"], workdir / package)
    return checkout, sha


def cmd_update(lock_path: Path, overrides: dict[str, str]) -> int:
    """Refresh every managed skill while preserving plugin-local skills."""
    root = lock_path.parent
    lock = load_lock(lock_path)
    validate_no_cross_source_collisions(lock)
    errors = 0

    with tempfile.TemporaryDirectory(prefix="skill-vendor-") as temporary:
        for source in lock["sources"]:
            destination = validate_source(source, root)
            try:
                checkout, sha = source_checkout(source, overrides, Path(temporary))
            except (RuntimeError, subprocess.CalledProcessError) as error:
                fail(f"{source['package']}: {error}")
                errors += 1
                continue

            source["sha"] = sha
            digests = {}
            for name in source["skills"]:
                source_skill = checkout / "skills" / name
                if not (source_skill / "SKILL.md").is_file():
                    fail(f"{source['package']}: skills/{name}/SKILL.md not found at {source['ref']}")
                    errors += 1
                    continue
                target = destination / name
                if target.exists():
                    shutil.rmtree(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_skill, target)
                digests[name] = hash_skill_dir(target)
            source["sha256"] = digests
            print(f"{source['package']}: vendored {len(digests)} skills at {sha[:12]}")

    if errors:
        return 1
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"lockfile updated: {lock_path}")
    return 0


def cmd_check(lock_path: Path, offline: bool, overrides: dict[str, str]) -> int:
    """Verify local digests and optionally the remote immutable source."""
    root = lock_path.parent
    lock = load_lock(lock_path)
    validate_no_cross_source_collisions(lock)
    errors = 0

    with tempfile.TemporaryDirectory(prefix="skill-vendor-") as temporary:
        for source in lock["sources"]:
            package = source["package"]
            destination = validate_source(source, root)
            locked = source.get("sha256", {})
            for name in source["skills"]:
                target = destination / name
                if not (target / "SKILL.md").is_file():
                    fail(f"{package}: managed skill skills/{name} is missing from the tree")
                    errors += 1
                    continue
                if hash_skill_dir(target) != locked.get(name):
                    fail(f"{package}: skills/{name} content differs from the lockfile digest")
                    errors += 1

            if offline:
                continue

            try:
                checkout, sha = source_checkout(source, overrides, Path(temporary))
            except (RuntimeError, subprocess.CalledProcessError) as error:
                fail(f"{package}: {error}")
                errors += 1
                continue
            if sha != source.get("sha"):
                fail(
                    f"{package}: {source['ref']} moved to {sha[:12]} "
                    f"(locked at {str(source.get('sha'))[:12]}); run update"
                )
                errors += 1
                continue
            for name in source["skills"]:
                upstream_skill = checkout / "skills" / name
                if not (upstream_skill / "SKILL.md").is_file():
                    fail(f"{package}: skills/{name} missing upstream")
                    errors += 1
                    continue
                if hash_skill_dir(upstream_skill) != locked.get(name):
                    fail(f"{package}: skills/{name} upstream content differs from the lockfile")
                    errors += 1

    if errors:
        return 1
    suffix = " (offline)" if offline else ""
    print(f"skill vendor check: all managed skills match the lockfile{suffix}")
    return 0


def parse_overrides(pairs: list[str]) -> dict[str, str]:
    """Parse repeatable ``PACKAGE=PATH`` local-source overrides."""
    overrides = {}
    for pair in pairs:
        package, separator, path = pair.partition("=")
        if not separator:
            raise SystemExit(f"--source-path expects PKG=PATH, got '{pair}'")
        overrides[package] = path
    return overrides


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("update", "check"))
    parser.add_argument("--lock", default="skills.lock.json")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--source-path", action="append", default=[], metavar="PKG=PATH")
    args = parser.parse_args()

    lock_path = Path(args.lock).resolve()
    if not lock_path.is_file():
        fail(f"lockfile not found: {lock_path}")
        return 1
    try:
        if args.command == "update":
            return cmd_update(lock_path, parse_overrides(args.source_path))
        return cmd_check(lock_path, args.offline, parse_overrides(args.source_path))
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        fail(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
