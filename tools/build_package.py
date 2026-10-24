#!/usr/bin/env python3
"""Build the small plugin package plus the optional full icon pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_NAME = "astrbot_plugin_stalzone"
PLUGIN_ZIP = "astrbot_plugin_stalzone.zip"
ICON_ZIP = "stalzone_icons_full.zip"
MAX_PLUGIN_BYTES = 16 * 1024 * 1024

# Weapons, ammo, armor, artefacts, containers, devices and backpacks are the
# common query surface; everything else is supplied by the icon extension pack.
BASE_CATEGORY_PREFIXES = (
    "artefact/",
    "weapon/",
    "weapon_modules/",
    "consumables/bullet",
    "armor",
    "containers",
    "device",
    "backpacks",
)

EXCLUDED_TOP_LEVEL = {
    ".git",
    ".github",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "package",
    "tests",
    "tools",
    "item_icons",
}


def _is_base_category(category: str) -> bool:
    return any(
        category == prefix.rstrip("/") or category.startswith(prefix)
        for prefix in BASE_CATEGORY_PREFIXES
    )


def _base_icon_ids() -> list[str]:
    index_path = ROOT / "item_index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else payload
    result: list[str] = []
    seen: set[str] = set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in seen:
            continue
        if not _is_base_category(str(item.get("cat") or "")):
            continue
        if not (ROOT / "item_icons" / f"{item_id}.png").is_file():
            continue
        seen.add(item_id)
        result.append(item_id)
    return result


def _package_files(outputs: set[Path]):
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() in outputs:
            continue
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if path.suffix == ".pyc" or path.name in {PLUGIN_ZIP, ICON_ZIP, "SHA256SUMS"}:
            continue
        if path.name == ".coverage":
            continue
        yield path, relative


def _write_plugin_zip(output: Path, base_ids: list[str]) -> None:
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in _package_files({output.resolve()}):
            archive.write(path, f"{PLUGIN_NAME}/{relative.as_posix()}")
        for item_id in base_ids:
            icon = ROOT / "item_icons" / f"{item_id}.png"
            archive.write(icon, f"{PLUGIN_NAME}/item_icons/{icon.name}")


def _write_icon_zip(output: Path) -> None:
    note = (
        "STALZONE 图标扩展包\n"
        "===================\n\n"
        "把本压缩包内的 item_icons 文件夹解压到 AstrBot 插件数据目录：\n"
        "  data/plugin_data/astrbot_plugin_stalzone/\n\n"
        "最终目录应为：\n"
        "  data/plugin_data/astrbot_plugin_stalzone/item_icons/<物品ID>.png\n\n"
        "然后在 AstrBot WebUI 重载 STALZONE 插件即可。\n"
        "插件基础包已包含常用武器/弹药/护甲/神器等图标；本扩展包提供完整图标。\n"
    )
    icons = sorted((ROOT / "item_icons").glob("*.png"))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("图标扩展包说明.txt", note)
        for icon in icons:
            archive.write(icon, f"item_icons/{icon.name}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=".", help="directory for zip artifacts")
    parser.add_argument(
        "--with-icon-pack",
        action="store_true",
        help="also build the optional full icon pack zip",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    plugin_zip = output_dir / PLUGIN_ZIP
    icon_zip = output_dir / ICON_ZIP
    base_ids = _base_icon_ids()
    _write_plugin_zip(plugin_zip, base_ids)
    if args.with_icon_pack:
        _write_icon_zip(icon_zip)
    size = plugin_zip.stat().st_size
    checksums = [f"{_sha256(plugin_zip)}  {PLUGIN_ZIP}"]
    if args.with_icon_pack:
        checksums.append(f"{_sha256(icon_zip)}  {ICON_ZIP}")
    (output_dir / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print(f"base icons: {len(base_ids)}")
    print(f"plugin zip: {size / 1024 / 1024:.2f} MiB -> {plugin_zip}")
    if args.with_icon_pack:
        print(f"icon pack : {icon_zip.stat().st_size / 1024 / 1024:.2f} MiB -> {icon_zip}")
    if size > MAX_PLUGIN_BYTES:
        print(f"ERROR: plugin zip exceeds {MAX_PLUGIN_BYTES / 1024 / 1024:.0f} MiB")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
