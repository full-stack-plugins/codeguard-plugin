"""Cross-platform invariants for raw-byte, locked skill snapshots."""
from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vendor_portability", ROOT / "scripts/vendor/skill_vendor.py")
assert SPEC and SPEC.loader
VENDOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VENDOR)


class SkillVendorPortabilityTest(unittest.TestCase):
    def test_digest_uses_case_sensitive_posix_relative_string_order(self):
        # Explicit order is identical on NTFS and POSIX, including file/directory prefixes.
        ordered = ["A-long.md", "B.md", "a.md", "q-early.md", "q/nested.md", "Å.md"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = hashlib.sha256()
            for name in reversed(ordered):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((name + "\n").encode("utf-8"))
            for name in ordered:
                expected.update(name.encode("utf-8") + b"\0")
                expected.update(hashlib.sha256((name + "\n").encode("utf-8")).hexdigest().encode("ascii") + b"\n")
            self.assertEqual(VENDOR.hash_skill_dir(root), expected.hexdigest())

    def test_hash_keeps_crlf_distinct_from_locked_lf_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "SKILL.md"
            path.write_bytes(b"line one\nline two\n")
            lf = VENDOR.hash_skill_dir(root)
            path.write_bytes(b"line one\r\nline two\r\n")
            self.assertNotEqual(VENDOR.hash_skill_dir(root), lf)

    def test_hash_keeps_binary_bytes_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = b"\0binary\r\n\xff"
            (root / "data.bin").write_bytes(value)
            expected = hashlib.sha256(b"data.bin\0" + hashlib.sha256(value).hexdigest().encode("ascii") + b"\n").hexdigest()
            self.assertEqual(VENDOR.hash_skill_dir(root), expected)


class SkillVendorCheckoutTest(unittest.TestCase):
    def test_upstream_checkout_is_lf_despite_inherited_autocrlf(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            upstream = root / "upstream"
            upstream.mkdir()
            text = b"controlled upstream\nsecond line\n"
            binary = b"\0binary\r\n\xff"
            (upstream / "SKILL.md").write_bytes(text)
            (upstream / "data.bin").write_bytes(binary)
            def git(*arguments):
                result = subprocess.run(["git", "-c", "core.autocrlf=false", "-C", str(upstream), *arguments], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            git("init", "--quiet")
            git("add", "SKILL.md", "data.bin")
            git("-c", "user.name=Vendor Test", "-c", "user.email=vendor@example.invalid", "commit", "--quiet", "-m", "fixture")
            git("tag", "v1.0.0")
            config = root / "user.gitconfig"
            config_bytes = b"[core]\n\tautocrlf = true\n\teol = crlf\n"
            config.write_bytes(config_bytes)
            environment = {**os.environ, "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.autocrlf", "GIT_CONFIG_VALUE_0": "true"}
            runner = ("import importlib.util,sys;from pathlib import Path;"
                      "s=importlib.util.spec_from_file_location('vendor',sys.argv[1]);"
                      "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                      "m.fetch_checkout(sys.argv[2],'v1.0.0',Path(sys.argv[3]))")
            result = subprocess.run([sys.executable, "-B", "-c", runner, str(ROOT / "scripts/vendor/skill_vendor.py"), str(upstream), str(root / "fetch")], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "fetch/checkout/SKILL.md").read_bytes(), text)
            self.assertEqual((root / "fetch/checkout/data.bin").read_bytes(), binary)
            self.assertEqual(config.read_bytes(), config_bytes)

    def test_skill_attributes_preserve_lf_text_and_binary_bytes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            (repo / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
            (repo / "skills/example").mkdir(parents=True)
            text = b"controlled skill\nsecond line\n"
            binary = b"\0binary\r\n\xff"
            (repo / "skills/example/SKILL.md").write_bytes(text)
            (repo / "skills/example/data.bin").write_bytes(binary)
            for arguments in [["init", "--quiet"], ["add", ".gitattributes", "skills"], ["checkout-index", "--all", "--prefix=" + (root / "export").as_posix() + "/"]]:
                result = subprocess.run(["git", "-c", "core.autocrlf=true", "-C", str(repo), *arguments], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "export/skills/example/SKILL.md").read_bytes(), text)
            self.assertEqual((root / "export/skills/example/data.bin").read_bytes(), binary)


if __name__ == "__main__":
    unittest.main()
