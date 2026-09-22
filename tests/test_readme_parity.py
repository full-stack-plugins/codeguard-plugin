#!/usr/bin/env python3
"""README.md 与 README.zh-CN.md 的结构一致性门禁（bilingual-docs-consistency spec）。

守三类「机器可判定」的一致性（全部跳过 ``` 围栏，避免把 bash 注释当标题）：
1. 标题层级序列相等（语言不同、文字不同，但结构必须镜像）；
2. 本地链接目标集合相等（docs 改名必须两边同时改）；
3. `x.y.z` 版本串集合相等（Current version / vendor 快照等任一边漏改即失败）。

译文正确性不在门禁范围——由两份文件顶部的 parity 注 + review 把守。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "README.md"
ZH = ROOT / "README.zh-CN.md"

_HEADING_RE = re.compile(r"^(#{1,6})\s")
_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def _unfenced(text: str) -> str:
    """去掉 ``` 围栏内的行（bash 注释形如 # ... 会被误判成标题）。"""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def _heading_levels(text: str) -> list[int]:
    return [len(m.group(1)) for m in
            (_HEADING_RE.match(ln) for ln in _unfenced(text).splitlines()) if m]


def _local_links(text: str) -> set[str]:
    return {t for t in _LINK_RE.findall(_unfenced(text))
            if not t.startswith(("http://", "https://", "mailto:", "#"))}


def _versions(text: str) -> set[str]:
    return set(_VERSION_RE.findall(text))


class ReadmeParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.en = EN.read_text(encoding="utf-8")
        cls.zh = ZH.read_text(encoding="utf-8")

    def test_both_files_exist(self) -> None:
        self.assertTrue(EN.is_file(), "README.md missing")
        self.assertTrue(ZH.is_file(), "README.zh-CN.md missing")

    def test_parity_notes_present(self) -> None:
        self.assertIn("tests/test_readme_parity.py", self.en, "en parity note missing")
        self.assertIn("tests/test_readme_parity.py", self.zh, "zh parity note missing")

    def test_heading_level_sequences_match(self) -> None:
        en_h, zh_h = _heading_levels(self.en), _heading_levels(self.zh)
        self.assertEqual(en_h, zh_h,
                         msg=f"heading-level sequence drift:\n  en={en_h}\n  zh={zh_h}")

    def test_local_link_targets_match(self) -> None:
        en_l, zh_l = _local_links(self.en), _local_links(self.zh)
        self.assertEqual(en_l, zh_l,
                         msg=f"link drift: only_en={en_l - zh_l} only_zh={zh_l - en_l}")

    def test_version_strings_match(self) -> None:
        en_v, zh_v = _versions(self.en), _versions(self.zh)
        self.assertEqual(en_v, zh_v,
                         msg=f"version drift: only_en={en_v - zh_v} only_zh={zh_v - en_v}")


if __name__ == "__main__":
    unittest.main()
