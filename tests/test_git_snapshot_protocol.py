"""准确 Git 快照必须验证批量对象协议，不得把错位内容交给检查器。"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import git_snapshot
from codeguard.gate import run_gate
from codeguard.git_guard_application import evaluate_git_command


class GitSnapshotProtocolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cg-snapshot-protocol-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        self.content = b"first line\n\x00second line\r\n"
        (self.root / "sample.bin").write_bytes(self.content)
        subprocess.run(["git", "add", "sample.bin"], cwd=self.root,
                       check=True, capture_output=True)

    @staticmethod
    def corrupt_run(variant: str):
        real_run = subprocess.run

        def run(argv, *args, **kwargs):
            result = real_run(argv, *args, **kwargs)
            if argv[:2] != ["git", "cat-file"]:
                return result
            raw = result.stdout
            header, separator, rest = raw.partition(b"\n")
            if argv[2] == "--batch-check":
                if variant == "missing_check":
                    raw = b""
                elif variant == "duplicate_check":
                    raw += raw
                elif variant == "wrong_check_size":
                    oid, kind, size = header.split()
                    raw = b" ".join((oid, kind, str(int(size) + 1).encode())) + separator + rest
            elif argv[2] == "--batch":
                if variant in ("wrong_oid", "wrong_type", "wrong_batch_size"):
                    oid, kind, size = header.split()
                    if variant == "wrong_oid":
                        oid = b"0" * len(oid)
                    elif variant == "wrong_type":
                        kind = b"tree"
                    else:
                        size = str(int(size) - 1).encode()
                    raw = b" ".join((oid, kind, size)) + separator + rest
                elif variant == "truncated":
                    raw = raw[:-2]
                elif variant == "missing_delimiter":
                    raw = raw[:-1]
                elif variant == "trailing":
                    raw += b"unexpected"
                elif variant == "wrong_content_same_size":
                    raw = header + separator + b"X" + rest[1:]
            return subprocess.CompletedProcess(result.args, result.returncode, raw, result.stderr)

        return run

    @staticmethod
    def corrupt_listing(variant: str):
        real_run = subprocess.run

        def run(argv, *args, **kwargs):
            result = real_run(argv, *args, **kwargs)
            if argv not in (["git", "ls-files", "--stage", "-z"],
                            ["git", "ls-tree", "-r", "-z", "HEAD"]):
                return result
            raw = result.stdout
            first = raw.split(b"\0", 1)[0]
            if variant == "missing_terminator":
                raw = raw[:-1]
            elif variant == "duplicate":
                raw += first + b"\0"
            elif variant == "missing_complete_record":
                raw = first + b"\0"
            elif variant == "empty":
                raw = b""
            elif variant == "empty_record":
                raw = raw.replace(b"\0", b"\0\0", 1)
            elif variant == "empty_name":
                raw = first.split(b"\t", 1)[0] + b"\t\0"
            elif variant == "invalid_oid":
                metadata, name = first.split(b"\t", 1)
                fields = metadata.split()
                oid_index = 2 if argv[1] == "ls-tree" else 1
                fields[oid_index] = b"z" * len(fields[oid_index])
                raw = b" ".join(fields) + b"\t" + name + raw[len(first):]
            elif variant == "invalid_header":
                raw = b"bogus\t" + first.split(b"\t", 1)[1] + raw[len(first):]
            return subprocess.CompletedProcess(result.args, result.returncode, raw, result.stderr)

        return run

    def test_real_binary_blob_is_preserved_without_index_mutation(self):
        before = (self.root / ".git/index").read_bytes()
        with git_snapshot.validation_tree(self.root) as (snapshot, changed):
            self.assertEqual(self.content, (snapshot / "sample.bin").read_bytes())
            self.assertEqual(["sample.bin"], changed)
        self.assertEqual(before, (self.root / ".git/index").read_bytes())

    def test_empty_index_remains_a_valid_empty_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="cg-snapshot-empty-") as directory:
            root = Path(directory).resolve()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
            with git_snapshot.validation_tree(root) as (snapshot, changed):
                self.assertEqual([], list(snapshot.iterdir()))
                self.assertEqual([], changed)

    def test_push_snapshot_reads_head_not_dirty_worktree(self):
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "fixture"], cwd=self.root, check=True, capture_output=True)
        (self.root / "sample.bin").write_bytes(b"dirty worktree\n")
        before = (self.root / ".git/index").read_bytes()
        with git_snapshot.validation_tree(self.root, mode="push") as (snapshot, _changed):
            self.assertEqual(self.content, (snapshot / "sample.bin").read_bytes())
        self.assertEqual(before, (self.root / ".git/index").read_bytes())

    def test_sha256_repository_uses_its_object_format(self):
        with tempfile.TemporaryDirectory(prefix="cg-snapshot-sha256-") as directory:
            root = Path(directory).resolve()
            subprocess.run(["git", "init", "-q", "--object-format=sha256"], cwd=root,
                           check=True, capture_output=True)
            (root / "sample.bin").write_bytes(self.content)
            subprocess.run(["git", "add", "sample.bin"], cwd=root,
                           check=True, capture_output=True)
            before = (root / ".git/index").read_bytes()
            with git_snapshot.validation_tree(root) as (snapshot, changed):
                self.assertEqual(self.content, (snapshot / "sample.bin").read_bytes())
                self.assertEqual(["sample.bin"], changed)
            self.assertEqual(before, (root / ".git/index").read_bytes())

    def test_inconsistent_batch_protocol_never_yields_a_snapshot(self):
        before = (self.root / ".git/index").read_bytes()
        variants = ("missing_check", "duplicate_check", "wrong_check_size",
                    "wrong_oid", "wrong_type", "wrong_batch_size", "truncated",
                    "missing_delimiter", "trailing", "wrong_content_same_size")
        for variant in variants:
            with (self.subTest(variant=variant),
                  patch.object(git_snapshot.subprocess, "run",
                               side_effect=self.corrupt_run(variant)),
                  self.assertRaises(git_snapshot.SnapshotError),
                  git_snapshot.validation_tree(self.root)):
                pass
            self.assertEqual(before, (self.root / ".git/index").read_bytes())

    def test_incomplete_index_listing_never_yields_a_snapshot(self):
        (self.root / "second.txt").write_text("another file\n", encoding="utf-8")
        subprocess.run(["git", "add", "second.txt"], cwd=self.root,
                       check=True, capture_output=True)
        before = (self.root / ".git/index").read_bytes()
        variants = ("missing_terminator", "duplicate", "missing_complete_record",
                    "empty", "empty_record", "empty_name", "invalid_oid", "invalid_header")
        for variant in variants:
            with (self.subTest(variant=variant),
                  patch.object(git_snapshot.subprocess, "run",
                               side_effect=self.corrupt_listing(variant)),
                  self.assertRaises(git_snapshot.SnapshotError),
                  git_snapshot.validation_tree(self.root)):
                pass
            self.assertEqual(before, (self.root / ".git/index").read_bytes())

    def test_incomplete_head_listing_never_yields_a_push_snapshot(self):
        (self.root / "second.txt").write_text("another file\n", encoding="utf-8")
        subprocess.run(["git", "add", "second.txt"], cwd=self.root,
                       check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "fixture"], cwd=self.root, check=True, capture_output=True)
        for variant in ("missing_terminator", "missing_complete_record", "empty",
                        "duplicate", "invalid_oid"):
            with (self.subTest(variant=variant),
                  patch.object(git_snapshot.subprocess, "run",
                               side_effect=self.corrupt_listing(variant)),
                  self.assertRaises(git_snapshot.SnapshotError),
                  git_snapshot.validation_tree(self.root, mode="push")):
                pass

    def test_incomplete_path_name_response_is_not_treated_as_empty(self):
        real_run = subprocess.run

        def run(argv, *args, **kwargs):
            result = real_run(argv, *args, **kwargs)
            if argv[:4] == ["git", "diff", "--cached", "--name-only"]:
                return subprocess.CompletedProcess(result.args, result.returncode,
                                                   result.stdout[:-1], result.stderr)
            return result

        with (patch.object(git_snapshot.subprocess, "run", side_effect=run),
              self.assertRaises(git_snapshot.SnapshotError)):
            git_snapshot.proposed_paths(self.root)

    def test_malformed_listing_is_visible_to_exact_gate(self):
        with patch.object(git_snapshot.subprocess, "run",
                          side_effect=self.corrupt_listing("missing_terminator")):
            failures, skipped = run_gate(self.root, {}, ["python"], exact=True)
        self.assertEqual([], failures)
        self.assertTrue(any("git UNVERIFIED" in item for item in skipped), skipped)

    def test_special_filename_is_preserved_by_nul_listing(self):
        name = "tab\tline\n.txt"
        (self.root / name).write_text("content\n", encoding="utf-8")
        subprocess.run(["git", "add", name], cwd=self.root,
                       check=True, capture_output=True)
        with git_snapshot.validation_tree(self.root) as (snapshot, changed):
            self.assertEqual("content\n", (snapshot / name).read_text(encoding="utf-8"))
            self.assertIn(name, changed)

    def test_exact_gate_reports_corrupt_blob_as_unverified(self):
        with patch.object(git_snapshot.subprocess, "run",
                          side_effect=self.corrupt_run("wrong_oid")):
            failures, skipped = run_gate(self.root, {}, ["python"], exact=True)
        self.assertEqual([], failures)
        self.assertTrue(any("git UNVERIFIED" in item for item in skipped), skipped)

    def test_known_sensitive_path_still_blocks_when_blob_is_unverified(self):
        (self.root / ".env").write_text("FIXTURE_ONLY=not-a-secret\n", encoding="utf-8")
        subprocess.run(["git", "add", ".env"], cwd=self.root,
                       check=True, capture_output=True)
        before = (self.root / ".git/index").read_bytes()
        with patch.object(git_snapshot.subprocess, "run",
                          side_effect=self.corrupt_run("wrong_oid")):
            result = evaluate_git_command("git commit -m fixture", cwd=self.root,
                                          load_config=dict)
        self.assertEqual(2, result.exit_code)
        self.assertTrue(any("git UNVERIFIED" in item for item in result.contexts), result.contexts)
        self.assertIn(".env", result.stderr)
        self.assertEqual(before, (self.root / ".git/index").read_bytes())


if __name__ == "__main__":
    unittest.main()
