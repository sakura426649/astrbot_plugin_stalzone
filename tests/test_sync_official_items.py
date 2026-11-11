from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import sync_official_items


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class SyncOfficialItemsTests(unittest.TestCase):
    def _fixture(self, directory: Path) -> tuple[Path, Path, Path, Path]:
        source = directory / "official"
        pistol = source / "ru" / "items" / "weapon" / "pistol" / "abc12.json"
        _write_json(
            pistol,
            {
                "id": "abc12",
                "category": "weapon/pistol",
                "name": {
                    "key": "item.wpn.abc12.name",
                    "lines": {"en": "Official Pistol", "ru": "Официальный"},
                },
                "color": "RANK_RARE",
            },
        )
        food = source / "ru" / "items" / "supply" / "food" / "food1.json"
        _write_json(
            food,
            {
                "id": "food1",
                "category": "supply/food",
                "name": {
                    "key": "item.food.food1.name",
                    "lines": {"en": "Official Food", "ru": "Еда"},
                },
                "color": "DEFAULT",
            },
        )
        # Skins must not become base items.
        _write_json(
            source
            / "ru"
            / "items"
            / "weapon"
            / "pistol"
            / "_variants"
            / "abc12"
            / "1.json",
            {"id": "variant", "name": {"lines": {"en": "Skin"}}},
        )
        for relative in (
            "ru/icons/weapon/pistol/abc12.png",
            "ru/icons/supply/food/food1.png",
        ):
            icon = source / relative
            icon.parent.mkdir(parents=True, exist_ok=True)
            icon.write_bytes(b"official-png")

        existing = directory / "item_index.json"
        _write_json(
            existing,
            {
                "items": [
                    {
                        "id": "abc12",
                        "en": "Old Pistol",
                        "ru": "Старый",
                        "zh": "旧手枪",
                        "zh_source": "exact",
                        "color": "DEFAULT",
                        "cat": "weapon/pistol",
                        "key": "old.key",
                        "icon": "https://cdn.example/abc12.png",
                    },
                    {
                        "id": "oldskin",
                        "en": "Old Skin",
                        "ru": "Старый скин",
                        "zh": "旧皮肤",
                        "color": "DEFAULT",
                        "cat": "other/skins",
                        "key": "old.skin",
                        "icon": "https://cdn.example/oldskin.png",
                    },
                ]
            },
        )
        overlay = directory / "zh.json"
        _write_json(overlay, {"names": {"abc12": "官方手枪"}})
        return source, existing, overlay, directory / "out.json"

    def test_official_index_merges_overlay_and_supplemental(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            source, existing, overlay, output = self._fixture(directory)
            code = sync_official_items.main(
                [
                    "--source",
                    str(source),
                    "--existing",
                    str(existing),
                    "--overlay",
                    str(overlay),
                    "--out",
                    str(output),
                ]
            )
            self.assertEqual(code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["official_count"], 2)
            self.assertEqual(payload["supplemental_count"], 1)
            self.assertEqual(payload["count"], 3)
            items = {item["id"]: item for item in payload["items"]}
            pistol = items["abc12"]
            self.assertEqual(pistol["en"], "Official Pistol")
            self.assertEqual(pistol["zh"], "官方手枪")
            self.assertEqual(pistol["cat"], "weapon/pistol")
            self.assertEqual(pistol["official_cat"], "weapon/pistol")
            self.assertEqual(pistol["color"], "RANK_RARE")
            self.assertEqual(pistol["source"], "official")
            self.assertEqual(
                pistol["official_icon"], "ru/icons/weapon/pistol/abc12.png"
            )
            # Existing wiki CDN URLs stay as the network fallback; bundled
            # icons are replaced from the official library separately.
            self.assertEqual(pistol["icon"], "https://cdn.example/abc12.png")

            food = items["food1"]
            self.assertEqual(food["cat"], "consumables/food")
            self.assertEqual(food["zh"], "Official Food")
            self.assertEqual(food["zh_source"], "fallback")

            skin = items["oldskin"]
            self.assertEqual(skin["source"], "supplemental")
            self.assertEqual(skin["zh"], "旧皮肤")
            self.assertEqual(skin["icon"], "https://cdn.example/oldskin.png")
            self.assertNotIn("official_cat", skin)

    def test_sync_icons_only_overwrites_bundled_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            source, existing, overlay, output = self._fixture(directory)
            icons = directory / "item_icons"
            icons.mkdir()
            (icons / "abc12.png").write_bytes(b"old-bundled")
            code = sync_official_items.main(
                [
                    "--source",
                    str(source),
                    "--existing",
                    str(existing),
                    "--overlay",
                    str(overlay),
                    "--out",
                    str(output),
                    "--sync-icons",
                    str(icons),
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual((icons / "abc12.png").read_bytes(), b"official-png")
            # food1 has no bundled icon yet, so syncing must not grow the pack.
            self.assertFalse((icons / "food1.png").exists())


if __name__ == "__main__":
    unittest.main()
