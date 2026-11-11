#!/usr/bin/env python3
"""Regenerate ``item_index.json`` from the official EXBO item database.

The official repository (https://github.com/EXBO-Studio/stalzone-database)
is the canonical source for item IDs, English/Russian names, quality colors,
categories and icons.  It does not ship Chinese names, so this project keeps
a community translation overlay in ``translations/zh_items.json``.

Typical release workflow::

    # one-time / occasional: fetch a local checkout or source archive
    git clone --depth 1 https://github.com/EXBO-Studio/stalzone-database

    # regenerate the index (Chinese overlay is applied automatically)
    python tools/sync_official_items.py --source ../stalzone-database

    # also refresh bundled icons (only overwrites icons we already ship)
    python tools/sync_official_items.py --source ../stalzone-database \
        --sync-icons item_icons

Items that exist in our wiki-era index but are absent from the official
database (old event skins, for example) are kept as ``supplemental`` entries
so existing queries and aliases keep working.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "item_index.json"
DEFAULT_OVERLAY = ROOT / "translations" / "zh_items.json"
DEFAULT_ICONS = ROOT / "item_icons"

OFFICIAL_ICON_BASE = (
    "https://raw.githubusercontent.com/EXBO-Studio/stalzone-database/main"
)

# Official paths are grouped by game systems; the plugin's ``cat`` values are
# the labels used by the existing Chinese category filters.  Unknown official
# categories fall back to ``other`` rather than inventing a new filter group.
CATEGORY_MAP = {
    "bullet": "consumables/bullet",
    "grenade": "consumables/grenade",
    "medicine": "consumables/medicine",
    "supply": "consumables",
    "supply/bullet": "consumables/bullet",
    "supply/grenade": "consumables/grenade",
    "supply/medicine": "consumables/medicine",
    "supply/food": "consumables/food",
    "supply/drink": "consumables/drink",
    "supply/plates": "consumables/plates",
    "misc": "other/misc",
    "other": "other",
    "other/skins": "other/skins",
    "other/armor_motif": "other/misc",
    "armor/device": "device",
    "device/device": "device",
    "weapon/device": "device",
    "weapon_modules/weapon_module": "weapon_modules/module",
    "weapon_modules/weapon_module_core": "weapon_modules/core",
    "weapon_modules/weapon_module_remover": "weapon_modules/remover",
}

TOP_LEVEL_CATEGORIES = {
    "armor",
    "artefact",
    "attachment",
    "backpacks",
    "containers",
    "device",
    "weapon",
    "weapon_modules",
}


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _iter_official_items(source: Path) -> Iterator[tuple[str, str, Path]]:
    """Yield ``(item_id, official_category, json_path)`` for base items."""
    items_root = source / "ru" / "items"
    for path in sorted(items_root.rglob("*.json")):
        parts = path.relative_to(items_root).parts
        if "_variants" in parts:
            continue
        category = "/".join(parts[:-1])
        item_id = path.stem.strip()
        if item_id:
            yield item_id, category, path


def _translation_lines(payload: dict[str, Any]) -> dict[str, str]:
    name = payload.get("name")
    if not isinstance(name, dict):
        return {}
    lines = name.get("lines")
    if not isinstance(lines, dict):
        return {}
    return {
        str(key): str(value).strip()
        for key, value in lines.items()
        if isinstance(value, str) and value.strip()
    }


def _official_category_name(official_category: str) -> str:
    if official_category in CATEGORY_MAP:
        return CATEGORY_MAP[official_category]
    top = official_category.split("/", 1)[0]
    if top in TOP_LEVEL_CATEGORIES:
        return official_category
    return "other"


def _official_icon_relative(official_category: str, item_id: str) -> str:
    return f"ru/icons/{official_category}/{item_id}.png"


def _official_icon_url(official_category: str, item_id: str) -> str:
    return f"{OFFICIAL_ICON_BASE}/{_official_icon_relative(official_category, item_id)}"


def _build_item(
    *,
    item_id: str,
    official_category: str | None,
    payload: dict[str, Any] | None,
    existing: dict[str, Any] | None,
    overlay: dict[str, str],
) -> dict[str, Any]:
    existing = existing or {}
    payload = payload or {}
    lines = _translation_lines(payload)
    name = payload.get("name") if isinstance(payload.get("name"), dict) else {}

    en = lines.get("en") or str(existing.get("en") or "").strip()
    ru = lines.get("ru") or str(existing.get("ru") or "").strip()
    zh = str(overlay.get(item_id) or "").strip()
    if not zh:
        zh = str(existing.get("zh") or "").strip()
    if not zh:
        zh = en or ru or item_id

    existing_zh = str(existing.get("zh") or "").strip()
    if existing_zh and zh == existing_zh:
        zh_source = str(existing.get("zh_source") or "exact")
    elif overlay.get(item_id):
        zh_source = "overlay"
    else:
        zh_source = "fallback"

    if official_category:
        cat = str(existing.get("cat") or "").strip() or _official_category_name(
            official_category
        )
        icon = str(existing.get("icon") or "").strip() or _official_icon_url(
            official_category, item_id
        )
        item = {
            "id": item_id,
            "en": en,
            "ru": ru,
            "zh": zh,
            "zh_source": zh_source,
            "color": str(payload.get("color") or existing.get("color") or "DEFAULT"),
            "cat": cat,
            "official_cat": official_category,
            "key": str(name.get("key") or existing.get("key") or ""),
            "icon": icon,
            "official_icon": _official_icon_relative(official_category, item_id),
            "source": "official",
        }
    else:
        item = {
            "id": item_id,
            "en": en,
            "ru": ru,
            "zh": zh,
            "zh_source": zh_source,
            "color": str(existing.get("color") or "DEFAULT"),
            "cat": str(existing.get("cat") or ""),
            "key": str(existing.get("key") or ""),
            "icon": str(existing.get("icon") or ""),
            "source": "supplemental",
        }
    return item


def _sync_icons(
    source: Path,
    items: list[dict[str, Any]],
    icons_dir: Path,
) -> tuple[int, list[str]]:
    """Copy official icons over bundled icons, keeping extra supplemental files."""
    icons_dir.mkdir(parents=True, exist_ok=True)
    updated = 0
    missing: list[str] = []
    for item in items:
        official_icon = str(item.get("official_icon") or "").strip()
        if not official_icon:
            continue
        target = icons_dir / f"{item['id']}.png"
        if not target.is_file():
            # The market package only bundles common categories; never grow it
            # implicitly while syncing icons.
            continue
        origin = source / official_icon
        if not origin.is_file():
            missing.append(item["id"])
            continue
        shutil.copyfile(origin, target)
        updated += 1
    return updated, missing


def _export_full_icons(
    source: Path,
    items: list[dict[str, Any]],
    output_dir: Path,
    seed_dir: Path | None,
) -> tuple[int, int, list[str]]:
    """Build a complete icon directory: official first, legacy extras kept."""
    output_dir.mkdir(parents=True, exist_ok=True)
    seeded = 0
    if seed_dir and seed_dir.is_dir():
        for icon in seed_dir.glob("*.png"):
            shutil.copyfile(icon, output_dir / icon.name)
            seeded += 1
    official = 0
    missing: list[str] = []
    for item in items:
        official_icon = str(item.get("official_icon") or "").strip()
        if not official_icon:
            continue
        origin = source / official_icon
        if origin.is_file():
            shutil.copyfile(origin, output_dir / f"{item['id']}.png")
            official += 1
        else:
            missing.append(item["id"])
    # Supplemental entries (old skins etc.) only exist in the bundled set.
    for icon in DEFAULT_ICONS.glob("*.png"):
        target = output_dir / icon.name
        if not target.is_file():
            shutil.copyfile(icon, target)
    return seeded, official, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        help="path to a stalzone-database checkout (contains ru/items and ru/icons)",
    )
    parser.add_argument("--out", default=str(DEFAULT_INDEX), help="index output path")
    parser.add_argument(
        "--overlay",
        default=str(DEFAULT_OVERLAY),
        help="Chinese name overlay JSON (default: translations/zh_items.json)",
    )
    parser.add_argument(
        "--existing",
        default=str(DEFAULT_INDEX),
        help="previous index used for Chinese fallback and supplemental items",
    )
    parser.add_argument(
        "--sync-icons",
        nargs="?",
        const=str(DEFAULT_ICONS),
        default=None,
        help="copy official icons over this bundled icon directory",
    )
    parser.add_argument(
        "--full-icons-out",
        help="build a complete icon directory (official + legacy supplemental)",
    )
    parser.add_argument(
        "--seed-icons",
        help="optional legacy icon directory used to seed --full-icons-out",
    )
    args = parser.parse_args(argv)

    source = Path(args.source).resolve()
    items_root = source / "ru" / "items"
    icons_root = source / "ru" / "icons"
    if not items_root.is_dir():
        print(f"ERROR: official items directory not found: {items_root}")
        return 1
    snapshot = _load_json(source / "official_snapshot.json", {})
    official_commit = (
        str(snapshot.get("commit") or "").strip()
        if isinstance(snapshot, dict)
        else ""
    )

    existing_payload = _load_json(Path(args.existing), {})
    existing_items = (
        existing_payload.get("items")
        if isinstance(existing_payload, dict)
        else None
    )
    existing_by_id = {
        str(item.get("id")): item
        for item in (existing_items if isinstance(existing_items, list) else [])
        if isinstance(item, dict) and item.get("id")
    }
    overlay_payload = _load_json(Path(args.overlay), {})
    overlay_raw = (
        overlay_payload.get("names")
        if isinstance(overlay_payload, dict)
        else None
    )
    overlay = {
        str(item_id): str(name).strip()
        for item_id, name in (overlay_raw if isinstance(overlay_raw, dict) else {}).items()
        if isinstance(name, str) and name.strip()
    }

    official: dict[str, tuple[str, Path, dict[str, Any]]] = {}
    duplicates: list[str] = []
    for item_id, category, path in _iter_official_items(source):
        if item_id in official:
            duplicates.append(item_id)
            continue
        payload = _load_json(path, {})
        if not isinstance(payload, dict):
            payload = {}
        official[item_id] = (category, path, payload)

    if not official:
        print("ERROR: no official item JSON files found")
        return 1

    missing_icons = [
        item_id
        for item_id, (category, _path, _payload) in official.items()
        if not (icons_root / category / f"{item_id}.png").is_file()
    ]

    ordered_ids: list[str] = []
    seen: set[str] = set()
    for item_id in existing_by_id:
        if item_id in official:
            ordered_ids.append(item_id)
            seen.add(item_id)
    # New official items are appended in a stable category/id order.
    for item_id in sorted(official):
        if item_id not in seen:
            ordered_ids.append(item_id)
            seen.add(item_id)

    items: list[dict[str, Any]] = []
    for item_id in ordered_ids:
        category, _path, payload = official[item_id]
        items.append(
            _build_item(
                item_id=item_id,
                official_category=category,
                payload=payload,
                existing=existing_by_id.get(item_id),
                overlay=overlay,
            )
        )
    # Preserve wiki-era entries that EXBO does not publish.
    for item_id, existing in existing_by_id.items():
        if item_id in official:
            continue
        items.append(
            _build_item(
                item_id=item_id,
                official_category=None,
                payload=None,
                existing=existing,
                overlay=overlay,
            )
        )

    output = {
        "generated_at": dt.date.today().isoformat(),
        "source": (
            "EXBO-Studio/stalzone-database (official items/icons) + "
            "community-maintained Chinese overlay (unofficial)"
        ),
        "official_count": len(official),
        "supplemental_count": len(items) - len(official),
        "count": len(items),
        "items": items,
    }
    if official_commit:
        output["official_commit"] = official_commit
    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(f"official items : {len(official)}")
    print(f"supplemental   : {output['supplemental_count']}")
    print(f"total          : {len(items)}")
    untranslated = [
        item
        for item in items
        if item.get("source") == "official"
        and item.get("zh_source") == "fallback"
    ]
    print(f"untranslated   : {len(untranslated)}")
    for item in untranslated[:10]:
        print(f"  {item['id']}  {item.get('en') or item.get('ru') or ''}")
    if len(untranslated) > 10:
        print(f"  ... and {len(untranslated) - 10} more")
    if duplicates:
        print(f"duplicate ids  : {len(duplicates)} ({', '.join(duplicates[:5])})")
    if missing_icons:
        print(
            f"official icons missing: {len(missing_icons)} "
            f"({', '.join(missing_icons[:5])})"
        )
    if args.sync_icons:
        updated, broken = _sync_icons(source, items, Path(args.sync_icons))
        print(f"bundled icons updated: {updated}")
        if broken:
            print(f"bundled icons missing source: {len(broken)}")
    if args.full_icons_out:
        seeded, official_icons, broken = _export_full_icons(
            source,
            items,
            Path(args.full_icons_out),
            Path(args.seed_icons) if args.seed_icons else None,
        )
        print(f"full icons seeded: {seeded}")
        print(f"full icons official: {official_icons}")
        print(f"full icons total: {len(list(Path(args.full_icons_out).glob('*.png')))}")
        if broken:
            print(f"full icons missing source: {len(broken)}")
    print(f"index written  : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
