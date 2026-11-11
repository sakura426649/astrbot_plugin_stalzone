from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from command_parser import parse_command
from item_db_update import (
    build_merged_index,
    extract_full_icons,
    extract_official_items,
    icon_coverage,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"test-icon"


class ItemDBUpdateTests(unittest.TestCase):
    def _official_zip(self, directory: Path) -> Path:
        path = directory / "official.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                "stalzone-database-main/ru/items/weapon/rifle/abc.json",
                json.dumps(
                    {
                        "name": {
                            "key": "item.wpn.abc.name",
                            "lines": {"en": "New Gun", "ru": "Новая"},
                        },
                        "color": "RANK_RARE",
                    }
                ),
            )
            archive.writestr(
                "stalzone-database-main/ru/items/supply/food/food1.json",
                json.dumps(
                    {
                        "name": {
                            "key": "item.food.food1.name",
                            "lines": {"en": "Food", "ru": "Еда"},
                        },
                        "color": "DEFAULT",
                    }
                ),
            )
            archive.writestr(
                "stalzone-database-main/ru/items/weapon/rifle/_variants/abc/1.json",
                "{}",
            )
            archive.writestr(
                "stalzone-database-main/ru/icons/weapon/rifle/abc.png", PNG
            )
            archive.writestr(
                "stalzone-database-main/ru/icons/supply/food/food1.png", PNG
            )
        return path

    def test_extract_and_merge_preserves_chinese_and_flags_new_items(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self._official_zip(root)
            icons = root / "icons"
            extracted = extract_official_items(source, icons)
            self.assertEqual(set(extracted["items"]), {"abc", "food1"})
            self.assertEqual(extracted["missing_icons"], [])
            self.assertTrue((icons / "abc.png").is_file())
            self.assertTrue((icons / "food1.png").is_file())

            existing = {
                "items": [
                    {
                        "id": "abc",
                        "en": "Old Gun",
                        "ru": "Старая",
                        "zh": "旧枪",
                        "zh_source": "exact",
                        "cat": "weapon/rifle",
                        "color": "DEFAULT",
                        "icon": "https://old/abc.png",
                    },
                    {
                        "id": "oldskin",
                        "en": "Old Skin",
                        "zh": "旧皮肤",
                        "zh_source": "exact",
                        "cat": "other/skins",
                    },
                ]
            }
            merged, stats = build_merged_index(existing, extracted["items"], {})
            by_id = {item["id"]: item for item in merged["items"]}
            self.assertEqual(merged["official_count"], 2)
            self.assertEqual(merged["supplemental_count"], 1)
            self.assertEqual(by_id["abc"]["zh"], "旧枪")
            self.assertEqual(by_id["abc"]["en"], "New Gun")
            self.assertEqual(by_id["abc"]["official_cat"], "weapon/rifle")
            self.assertEqual(by_id["abc"]["icon"], "https://old/abc.png")
            self.assertEqual(by_id["oldskin"]["source"], "supplemental")
            self.assertEqual(by_id["food1"]["zh"], "Food")
            self.assertEqual(by_id["food1"]["zh_source"], "fallback")
            self.assertEqual(stats["untranslated"], ["food1"])

            translated, stats2 = build_merged_index(
                merged,
                extracted["items"],
                {"food1": "食物"},
            )
            by_id = {item["id"]: item for item in translated["items"]}
            self.assertEqual(by_id["food1"]["zh"], "食物")
            self.assertEqual(by_id["food1"]["zh_source"], "overlay")
            self.assertNotIn("food1", stats2["untranslated"])

    def test_extract_full_icons_and_coverage(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            archive_path = root / "full.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "astrbot_plugin_stalzone/item_icons/abc.png", PNG
                )
                archive.writestr("astrbot_plugin_stalzone/main.py", "x")
            dest = root / "icons"
            self.assertEqual(extract_full_icons(archive_path, dest), 1)
            self.assertTrue((dest / "abc.png").is_file())
            coverage = icon_coverage({"abc", "food1"}, [dest])
            self.assertEqual(coverage["matched"], 1)
            self.assertEqual(coverage["missing"], ["food1"])

    def test_command_aliases_do_not_shadow_version_check(self):
        self.assertEqual(parse_command("/sz 检查")[0], "item_db")
        self.assertEqual(parse_command("/sz 物品库检查")[0], "item_db")
        self.assertEqual(parse_command("/sz 物品库更新")[0], "item_db")
        self.assertEqual(parse_command("/sz 检查更新")[0], "check_version")


if __name__ == "__main__":
    unittest.main()
