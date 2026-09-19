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
        for manifest in MANIFESTS:
            with self.subTest(manifest=manifest.name):
                data = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertNotIn("mcpServers", data)

    def test_each_released_manifest_points_to_the_68_skill_bundle(self):
        expected = len(list((ROOT / "skills").glob("*/SKILL.md")))
        self.assertEqual(68, expected)
        for manifest in MANIFESTS:
            with self.subTest(manifest=manifest.name):
                data = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertIn(data["skills"], {"skills", "./skills/"})


if __name__ == "__main__":
    unittest.main()
