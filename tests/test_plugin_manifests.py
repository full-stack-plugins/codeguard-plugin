import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    ROOT / ".zcode-plugin" / "plugin.json",
    ROOT / ".codex-plugin" / "plugin.json",
    ROOT / "kimi.plugin.json",
)


class PluginManifestTest(unittest.TestCase):
    def test_released_manifests_do_not_publish_placeholder_mcp_server(self):
        self.assertFalse((ROOT / ".mcp.json").exists())
        for manifest in MANIFESTS:
            with self.subTest(manifest=manifest.name):
                data = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertNotIn("mcpServers", data)

    def test_zcode_uses_convention_based_hook_discovery_once(self):
        data = json.loads(MANIFESTS[0].read_text(encoding="utf-8"))
        self.assertNotIn("hooks", data)
        self.assertTrue((ROOT / "hooks" / "hooks.json").is_file())

    def test_each_released_manifest_points_to_the_lock_union_plus_local_skills(self):
        lock = json.loads((ROOT / "skills.lock.json").read_text(encoding="utf-8"))
        lock_union: set[str] = set()
        for source in lock["sources"]:
            lock_union.update(source.get("skills", []))
        local = set(json.loads((ROOT / "plugin-local-skills.json").read_text(encoding="utf-8"))["skills"])
        expected = lock_union | local
        on_disk = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(expected, on_disk,
                         msg=f"skills lock union ≠ on-disk: "
                             f"only_in_lock={expected - on_disk}, only_on_disk={on_disk - expected}")
        for manifest in MANIFESTS:
            with self.subTest(manifest=manifest.name):
                data = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertIn(data["skills"], {"skills", "./skills/"})


if __name__ == "__main__":
    unittest.main()
