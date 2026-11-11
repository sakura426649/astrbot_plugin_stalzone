"""Runtime helpers for updating the item index from the official EXBO data.

The packaged plugin may not ship ``tools/`` (the marketplace zip intentionally
excludes it), so the chat command needs a small, dependency-free merger here.
The logic intentionally mirrors ``tools/sync_official_items.py`` while keeping
the already-shipped Chinese names and supplemental entries.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

OFFICIAL_REPO = "EXBO-Studio/stalzone-database"
OFFICIAL_ARCHIVE_URL = (
    f"https://github.com/{OFFICIAL_REPO}/archive/refs/heads/main.zip"
)
OFFICIAL_RAW_BASE = f"https://raw.githubusercontent.com/{OFFICIAL_REPO}/main"
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ICON_BYTES = 8 * 1024 * 1024

# Keep in sync with tools/sync_official_items.py.  Unknown categories fall
# back to "other" so an old plugin can still search the item by name.
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


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json_atomic(path: Path, payload: Any, *, indent: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=indent,
        separators=None if indent is not None else (",", ":"),
    )
    temporary.write_text(text + "\n", encoding="utf-8")
    temporary.replace(path)


def official_category_name(category: str) -> str:
    if category in CATEGORY_MAP:
        return CATEGORY_MAP[category]
    top = category.split("/", 1)[0]
    return category if top in TOP_LEVEL_CATEGORIES else "other"


def official_icon_relative(category: str, item_id: str) -> str:
    return f"ru/icons/{category}/{item_id}.png"


def official_icon_url(category: str, item_id: str) -> str:
    return f"{OFFICIAL_RAW_BASE}/{official_icon_relative(category, item_id)}"


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


def _zip_name(info: zipfile.ZipInfo) -> str:
    name = info.filename.replace("\\", "/").lstrip("/")
    pure = PurePosixPath(name)
    if not name or ".." in pure.parts:
        return ""
    return name


def _after_marker(name: str, marker: str) -> str | None:
    index = name.find(marker)
    if index < 0:
        return None
    return name[index + len(marker) :]


def _is_image_bytes(data: bytes) -> bool:
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith((b"GIF87a", b"GIF89a"))
        or (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def extract_official_items(
    archive_path: Path,
    icon_dir: Path | None = None,
) -> dict[str, Any]:
    """Read base item JSON and icons from an official repository zip.

    Returns ``{"items": {id: {...}}, "icon_written": n,
    "missing_icons": [...]}``.  ``_variants`` skin directories are skipped,
    matching the release workflow.
    """
    items: dict[str, dict[str, Any]] = {}
    icon_ids: set[str] = set()
    written_count = 0
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"官方物品库压缩包损坏：{bad}")
        for info in archive.infolist():
            name = _zip_name(info)
            if not name or info.is_dir():
                continue
            relative = _after_marker(name, "/ru/items/")
            if relative is None:
                relative = _after_marker(name, "ru/items/")
            if relative is None or not relative.endswith(".json"):
                continue
            parts = relative.split("/")
            if not parts or "_variants" in parts:
                continue
            item_id = parts[-1][:-5]
            if not ITEM_ID_RE.fullmatch(item_id):
                continue
            if info.file_size > MAX_JSON_BYTES:
                continue
            try:
                payload = json.loads(archive.read(info).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            category = "/".join(parts[:-1])
            items[item_id] = {"category": category, "payload": payload}
        if icon_dir is not None:
            icon_dir.mkdir(parents=True, exist_ok=True)
        for info in archive.infolist():
            name = _zip_name(info)
            if not name or info.is_dir() or not name.endswith(".png"):
                continue
            relative = _after_marker(name, "/ru/icons/")
            if relative is None:
                relative = _after_marker(name, "ru/icons/")
            if relative is None:
                continue
            parts = relative.split("/")
            if not parts or "_variants" in parts:
                continue
            item_id = parts[-1][:-4]
            if item_id not in items or not ITEM_ID_RE.fullmatch(item_id):
                continue
            if info.file_size > MAX_ICON_BYTES:
                continue
            icon_ids.add(item_id)
            if icon_dir is not None:
                data = archive.read(info)
                if _is_image_bytes(data):
                    (icon_dir / f"{item_id}.png").write_bytes(data)
                    written_count += 1

    missing = [item_id for item_id in items if item_id not in icon_ids]
    return {
        "items": items,
        "icon_written": written_count,
        "missing_icons": missing,
    }


def extract_full_icons(archive_path: Path, destination: Path) -> int:
    """Copy only ``item_icons/*.png`` from a plugin full package."""
    destination.mkdir(parents=True, exist_ok=True)
    written = 0
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"完整包压缩包损坏：{bad}")
        for info in archive.infolist():
            name = _zip_name(info)
            if not name or info.is_dir() or not name.endswith(".png"):
                continue
            marker = "/item_icons/"
            index = name.find(marker)
            if index < 0:
                if not name.startswith("item_icons/"):
                    continue
                relative = name[len("item_icons/") :]
            else:
                relative = name[index + len(marker) :]
            if "/" in relative or not relative.endswith(".png"):
                continue
            item_id = relative[:-4]
            if not ITEM_ID_RE.fullmatch(item_id):
                continue
            if info.file_size > MAX_ICON_BYTES:
                continue
            data = archive.read(info)
            if _is_image_bytes(data):
                (destination / f"{item_id}.png").write_bytes(data)
                written += 1
    return written


def icon_coverage(
    item_ids: set[str],
    icon_dirs: list[Path],
) -> dict[str, Any]:
    present: set[str] = set()
    for directory in icon_dirs:
        try:
            present.update(path.stem for path in directory.glob("*.png"))
        except OSError:
            continue
    matched = len(item_ids & present)
    return {
        "present": present,
        "matched": matched,
        "total": len(item_ids),
        "ratio": (matched / len(item_ids)) if item_ids else 1.0,
        "missing": sorted(item_ids - present),
    }


def _build_official_item(
    *,
    item_id: str,
    category: str,
    payload: dict[str, Any],
    existing: dict[str, Any] | None,
    overlay: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    existing = existing or {}
    lines = _translation_lines(payload)
    name = payload.get("name") if isinstance(payload.get("name"), dict) else {}
    en = lines.get("en") or str(existing.get("en") or "").strip()
    ru = lines.get("ru") or str(existing.get("ru") or "").strip()
    overlay_name = str(overlay.get(item_id) or "").strip()
    existing_zh = str(existing.get("zh") or "").strip()
    if overlay_name:
        zh = overlay_name
        zh_source = "overlay"
    elif existing_zh:
        zh = existing_zh
        zh_source = str(existing.get("zh_source") or "exact")
    else:
        zh = en or ru or item_id
        zh_source = "fallback"
    existing_source = str(existing.get("zh_source") or "").lower()
    existing_is_fallback = existing_source == "fallback" or (
        bool(existing_zh)
        and existing_zh in {en, ru, item_id}
        and not overlay_name
    )
    translated = bool(overlay_name) or (
        bool(existing_zh) and not existing_is_fallback
    )
    cat = str(existing.get("cat") or "").strip() or official_category_name(category)
    icon = str(existing.get("icon") or "").strip() or official_icon_url(
        category, item_id
    )
    item = {
        "id": item_id,
        "en": en,
        "ru": ru,
        "zh": zh,
        "zh_source": zh_source,
        "color": str(
            payload.get("color") or existing.get("color") or "DEFAULT"
        ),
        "cat": cat,
        "official_cat": category,
        "key": str(name.get("key") or existing.get("key") or ""),
        "icon": icon,
        "official_icon": official_icon_relative(category, item_id),
        "source": "official",
    }
    return item, translated


def _build_supplemental_item(
    *,
    item_id: str,
    existing: dict[str, Any],
    overlay: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    overlay_name = str(overlay.get(item_id) or "").strip()
    existing_zh = str(existing.get("zh") or "").strip()
    if overlay_name:
        zh = overlay_name
        zh_source = "overlay"
    elif existing_zh:
        zh = existing_zh
        zh_source = str(existing.get("zh_source") or "exact")
    else:
        zh = str(existing.get("en") or existing.get("ru") or item_id)
        zh_source = "fallback"
    existing_source = str(existing.get("zh_source") or "").lower()
    existing_is_fallback = existing_source == "fallback" or (
        bool(existing_zh)
        and existing_zh
        in {
            str(existing.get("en") or ""),
            str(existing.get("ru") or ""),
            item_id,
        }
        and not overlay_name
    )
    translated = bool(overlay_name) or (
        bool(existing_zh) and not existing_is_fallback
    )
    item = {
        "id": item_id,
        "en": str(existing.get("en") or ""),
        "ru": str(existing.get("ru") or ""),
        "zh": zh,
        "zh_source": zh_source,
        "color": str(existing.get("color") or "DEFAULT"),
        "cat": str(existing.get("cat") or ""),
        "key": str(existing.get("key") or ""),
        "icon": str(existing.get("icon") or ""),
        "source": "supplemental",
    }
    return item, translated


def build_merged_index(
    existing_payload: Any,
    official_items: dict[str, dict[str, Any]],
    overlay: dict[str, str] | None = None,
    *,
    official_commit: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge official items while preserving current Chinese and supplements."""
    overlay = {
        str(item_id): str(name).strip()
        for item_id, name in (overlay or {}).items()
        if isinstance(name, str) and str(name).strip()
    }
    existing_items = (
        existing_payload.get("items")
        if isinstance(existing_payload, dict)
        else None
    )
    existing_by_id: dict[str, dict[str, Any]] = {}
    ordered_existing: list[str] = []
    for item in existing_items if isinstance(existing_items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in existing_by_id:
            continue
        existing_by_id[item_id] = item
        ordered_existing.append(item_id)

    ordered_ids = [
        item_id for item_id in ordered_existing if item_id in official_items
    ]
    seen = set(ordered_ids)
    ordered_ids.extend(
        item_id for item_id in sorted(official_items) if item_id not in seen
    )

    items: list[dict[str, Any]] = []
    untranslated: list[str] = []
    for item_id in ordered_ids:
        official = official_items[item_id]
        item, translated = _build_official_item(
            item_id=item_id,
            category=str(official.get("category") or ""),
            payload=(
                official.get("payload")
                if isinstance(official.get("payload"), dict)
                else {}
            ),
            existing=existing_by_id.get(item_id),
            overlay=overlay,
        )
        items.append(item)
        if not translated:
            untranslated.append(item_id)

    for item_id in ordered_existing:
        if item_id in official_items:
            continue
        item, translated = _build_supplemental_item(
            item_id=item_id,
            existing=existing_by_id[item_id],
            overlay=overlay,
        )
        items.append(item)
        if not translated:
            untranslated.append(item_id)

    result = {
        "generated_at": date.today().isoformat(),
        "source": (
            "EXBO-Studio/stalzone-database (official items/icons) + "
            "community-maintained Chinese overlay (unofficial)"
        ),
        "official_count": len(official_items),
        "supplemental_count": len(items) - len(official_items),
        "count": len(items),
        "items": items,
    }
    if official_commit:
        result["official_commit"] = official_commit
    return result, {
        "official_count": len(official_items),
        "supplemental_count": result["supplemental_count"],
        "total_count": len(items),
        "untranslated": untranslated,
    }
