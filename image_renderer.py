"""Optional Pillow renderer for the text cards.

The plugin still works without Pillow or without a CJK font: the caller gets
``None`` and falls back to the plain-text card.  This keeps Docker/NapCat
deployments safe on minimal Linux images.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from .pda_format import parse_pda_segments, strip_pda_formatting
except ImportError:  # Direct execution / flat import fallback.
    from pda_format import parse_pda_segments, strip_pda_formatting

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
except Exception:  # pragma: no cover - Pillow is optional at runtime.
    Image = ImageDraw = ImageEnhance = ImageFilter = ImageFont = ImageOps = None  # type: ignore[assignment]

WIDTH = 960
PAD = 44
CARD_BG = "#101923"
CANVAS_BG = "#070c12"
BORDER = "#26384a"
TEXT = "#e7edf5"
MUTED = "#93a6ba"
ACCENT = "#ffb454"
GREEN = "#54d6a1"
SEP_CHARS = set("━─")
SIGNATURE_PREFIX = "Created By"
SIGNATURE_NAME = "@Sakura_Akira"
SIGNATURE = f"{SIGNATURE_PREFIX} {SIGNATURE_NAME}"
SIGNATURE_COLOR = "#e7c27d"
SIGNATURE_HEIGHT = 38
MORE_FEATURES_TIP = "更多功能：/sz help 获取菜单"
CREATOR_WATERMARK_HIDDEN = False


def set_creator_watermark_hidden(hidden: bool) -> None:
    """Toggle the bottom-right creator signature for every rendered card."""
    global CREATOR_WATERMARK_HIDDEN
    CREATOR_WATERMARK_HIDDEN = bool(hidden)


RANK_COLORS = {
    "newbie": "#53C353",
    "stalker": "#4EA8FF",
    "veteran": "#FF6FB5",
    "master": "#FF5C5C",
    "legend": "#FFD166",
}
ITEM_COLOR_MAP = {
    "RANK_NEWBIE": "#53C353",
    "RANK_STALKER": "#4EA8FF",
    "RANK_VETERAN": "#FF6FB5",
    "RANK_MASTER": "#FF5C5C",
    "RANK_LEGEND": "#FFD166",
    "DEFAULT": "#E7EDF5",
    "QUEST_ITEM": "#FFB454",
    "EXCLUSIVE": "#FF5C5C",
}
SIGNATURE_BAND = 26
_LAST_TEMP_CLEANUP = 0.0
HELP_WIDTH = 1600
HELP_HEIGHT = 1100
HELP_BACKGROUND = Path(__file__).with_name("assets") / "help_background.jpg"
BACKGROUND_DIR = Path(__file__).with_name("assets") / "backgrounds"
BACKGROUND_OPTIONS = ["default"] + [
    f"官方壁纸 {index:02d}" for index in range(1, 17)
]
_CARD_BACKGROUND = HELP_BACKGROUND
_CARD_PANEL_ALPHA = int(round(0.90 * 255))


def set_card_background(
    preset: Any = None,
    custom: Any = None,
    opacity: Any = 0.90,
) -> Path:
    """Select the shared card wallpaper and panel opacity."""
    global _CARD_BACKGROUND, _CARD_PANEL_ALPHA
    selected = HELP_BACKGROUND
    custom_text = str(custom or "").strip()
    if custom_text:
        candidate = Path(custom_text).expanduser()
        if not candidate.is_absolute():
            candidate = Path(__file__).resolve().parent / candidate
        if candidate.is_file():
            selected = candidate
    if selected == HELP_BACKGROUND:
        match = re.search(r"(\d{1,2})", str(preset or ""))
        if match:
            number = int(match.group(1))
            candidate = BACKGROUND_DIR / f"wallpaper_{number:02d}.jpg"
            if 1 <= number <= len(BACKGROUND_OPTIONS) - 1 and candidate.is_file():
                selected = candidate
    _CARD_BACKGROUND = selected
    try:
        value = float(opacity)
    except (TypeError, ValueError):
        value = 0.90
    value = min(1.0, max(0.0, value))
    _CARD_PANEL_ALPHA = int(round(value * 255))
    return selected


def card_background_stamp() -> str:
    """Cache key component for help/overlay background changes."""
    try:
        stamp = str(_CARD_BACKGROUND.stat().st_mtime_ns)
    except OSError:
        stamp = "missing"
    return f"{_CARD_BACKGROUND}|{stamp}|{_CARD_PANEL_ALPHA}"



def _candidate_fonts() -> list[Path]:
    paths: list[Path] = []
    explicit = os.getenv("STALZONE_FONT_PATH", "").strip()
    if explicit:
        paths.append(Path(explicit))
    windir = os.getenv("WINDIR", "").strip()
    if windir:
        fonts = Path(windir) / "Fonts"
        paths.extend(
            [
                fonts / "msyh.ttc",
                fonts / "msyhbd.ttc",
                fonts / "simhei.ttf",
                fonts / "simsun.ttc",
                fonts / "arialuni.ttf",
            ]
        )
    paths.extend(
        [
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
            Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        ]
    )
    return paths


def find_cjk_font(explicit: str | None = None) -> Path | None:
    """Return a usable CJK font path, or None."""
    if ImageFont is None:
        return None
    candidates = [Path(explicit)] if explicit else []
    candidates.extend(_candidate_fonts())
    for path in candidates:
        try:
            if path.is_file():
                ImageFont.truetype(str(path), 24)
                return path
        except Exception:
            continue
    return None


def _artist_font_candidates() -> list[Path]:
    paths: list[Path] = []
    explicit = os.getenv("STALZONE_SIGNATURE_FONT", "").strip()
    if explicit:
        paths.append(Path(explicit))
    paths.append(Path(__file__).with_name("assets") / "PlayfairDisplay-Italic.ttf")
    windir = os.getenv("WINDIR", "").strip()
    if windir:
        fonts = Path(windir) / "Fonts"
        paths.extend(
            [
                fonts / "Inkfree.ttf",
                fonts / "Gabriola.ttf",
                fonts / "BRUSHSCI.TTF",
                fonts / "FRSCRIPT.TTF",
                fonts / "LHANDW.TTF",
                fonts / "SCRIPTBL.TTF",
                fonts / "georgiai.ttf",
                fonts / "timesi.ttf",
            ]
        )
    paths.extend(
        [
            Path("/System/Library/Fonts/Supplemental/Snell Roundhand.ttc"),
            Path("/System/Library/Fonts/Supplemental/Zapfino.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
            Path("/usr/share/fonts/type1/urw-base35/Z003-MediumItalic.t1"),
        ]
    )
    return paths


FACTION_ICONS = {
    "freedom": "freedom.png",
    "rise": "freedom.png",
    "duty": "duty.png",
    "frontier": "duty.png",
    "merc": "mercenaries.png",
    "mercenary": "mercenaries.png",
    "mercenaries": "mercenaries.png",
    "covenant": "covenant.png",
    "stalker": "stalkers.png",
    "stalkers": "stalkers.png",
    "loners": "stalkers.png",
    "bandit": "bandits.png",
    "bandits": "bandits.png",
}


def faction_icon_path(faction: str | None) -> Path | None:
    name = str(faction or "").strip().lower()
    filename = FACTION_ICONS.get(name)
    if not filename:
        return None
    path = Path(__file__).with_name("assets") / "factions" / filename
    return path if path.is_file() else None


def find_mono_font(font_path: str | Path | None = None) -> Path | None:
    """Return a usable monospace font for PDA ASCII art."""
    if ImageFont is None:
        return None
    candidates: list[Path] = []
    explicit = os.getenv("STALZONE_MONO_FONT", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    windir = os.getenv("WINDIR", "").strip()
    if windir:
        fonts = Path(windir) / "Fonts"
        candidates.extend(
            [
                fonts / "consola.ttf",
                fonts / "cour.ttf",
                fonts / "lucon.ttf",
            ]
        )
    candidates.extend(
        [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"),
            Path("/System/Library/Fonts/Menlo.ttc"),
        ]
    )
    for candidate in candidates:
        try:
            if candidate.is_file():
                ImageFont.truetype(str(candidate), 12)
                return candidate
        except Exception:
            continue
    return find_cjk_font(str(font_path) if font_path else None)


def find_cjk_mono_font(font_path: str | Path | None = None) -> Path | None:
    """Return a font that can render CJK while keeping art rows stable."""
    if ImageFont is None:
        return None
    candidates: list[Path] = []
    explicit = os.getenv("STALZONE_CJK_MONO_FONT", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    windir = os.getenv("WINDIR", "").strip()
    if windir:
        fonts = Path(windir) / "Fonts"
        candidates.extend(
            [
                fonts / "simsun.ttc",
                fonts / "simhei.ttf",
                fonts / "msyh.ttc",
            ]
        )
    candidates.extend(
        [
            Path("/usr/share/fonts/opentype/noto/NotoSansMonoCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        ]
    )
    for candidate in candidates:
        try:
            if candidate.is_file():
                ImageFont.truetype(str(candidate), 13)
                return candidate
        except Exception:
            continue
    return find_cjk_font(str(font_path) if font_path else None)


def _find_artist_font(font_path: str | Path | None = None) -> Path | None:
    if ImageFont is None:
        return None
    for path in _artist_font_candidates():
        try:
            if path.is_file():
                ImageFont.truetype(str(path), 24)
                return path
        except Exception:
            continue
    return find_cjk_font(str(font_path) if font_path else None)


ARTIFACT_GOOD_POSITIVE = {
    "生命",
    "健康",
    "耐力",
    "耐力恢复",
    "耐力再生",
    "生命恢复",
    "生命再生",
    "治疗效率",
    "周期性治疗",
    "即时治疗",
    "移动速度",
    "奔跑速度",
    "速度",
    "瞄准速度",
    "瞄准时移动速度",
    "拔枪速度",
    "负重",
    "稳定性",
    "稳定化",
    "伤害",
    "最低伤害",
    "最高伤害",
    "攻击速度",
    "射速",
    "弹匣容量",
    "附加弹匣容量",
    "最大射程",
    "射程",
    "最大伤害距离",
    "最小伤害距离",
    "武器攻击距离",
    "被动范围",
    "主动范围",
    "耐久",
    "最大耐久",
    "状态",
    "人体工学",
    "效率",
    "容量",
    "伤害吸收",
    "内部防护",
    "穿透",
    "穿甲",
    "护甲板穿透",
    "停止作用",
    "减伤",
    "对变异体伤害",
    "四肢伤害倍率",
    "对建筑伤害",
    "爆炸伤害",
    "寒冷伤害",
    "撕裂伤害",
    "化学伤害",
    "电伤害",
    "火焰伤害",
    "绝对伤害",
    "中心伤害",
    "伤害范围",
    "活动收益",
    "子弹防护",
    "爆炸防护",
    "撕裂防护",
    "流血防护",
    "精神辐射防护",
    "辐射防护",
    "高温防护",
    "生物感染防护",
    "防寒",
    "防毒",
    "火抗性",
    "化学抗性",
    "电抗性",
    "撕裂反应",
    "燃烧反应",
    "电反应",
    "化学灼烧反应",
}
ARTIFACT_GOOD_NEGATIVE = {
    "辐射",
    "精神辐射",
    "生物感染",
    "流血",
    "中毒",
    "温度",
    "寒冷",
    "燃烧",
    "重量",
    "后坐力",
    "水平后坐力",
    "垂直后坐力",
    "后坐力增长",
    "晃动",
    "散布",
    "腰射散布",
    "换弹时间",
    "战术换弹时间",
    "完整换弹",
    "单发装填",
    "瞄准时间",
    "拔枪时间",
}
STAT_GREEN = "#6FE0A8"
STAT_RED = "#FF6B6B"


def _stat_direction(label: str) -> int:
    value = re.sub(r"（附加[^）]*）$", "", str(label or "")).strip()
    if value in ARTIFACT_GOOD_POSITIVE:
        return 1
    if value in ARTIFACT_GOOD_NEGATIVE:
        return -1
    return 0


def _artifact_label_color(direction: int, value: str) -> str:
    if direction == 0:
        return MUTED
    signs: list[int] = []
    for match in re.finditer(r"[+-]?\d(?:[\d.,]*\d)?\s*%?", value):
        token = match.group()
        numeric = float(re.sub(r"[^0-9.]", "", token) or 0)
        if numeric:
            signs.append(-1 if token.startswith("-") else 1)
    if not signs:
        return MUTED
    if all(sign == direction for sign in signs):
        return STAT_GREEN
    if all(sign == -direction for sign in signs):
        return STAT_RED
    return TEXT


def _draw_artifact_stat_line(
    draw: Any, x: int, y: int, line: str, font: Any
) -> None:
    label, sep, value = line.partition("：")
    if not sep:
        draw.text((x, y), line, font=font, fill=TEXT)
        return
    direction = _stat_direction(label)
    label_fill = _artifact_label_color(direction, value)
    draw.text((x, y), label + "：", font=font, fill=label_fill)
    cursor = int(x + draw.textlength(label + "：", font=font))
    last = 0
    for match in re.finditer(r"[+-]?\d(?:[\d.,]*\d)?\s*%?", value):
        if match.start() > last:
            draw.text((cursor, y), value[last : match.start()], font=font, fill=TEXT)
            cursor += int(draw.textlength(value[last : match.start()], font=font))
        token = match.group()
        numeric = float(re.sub(r"[^0-9.]", "", token) or 0)
        sign = -1 if token.startswith("-") else 1
        if direction == 0 or numeric == 0:
            fill = TEXT
        elif sign == direction:
            fill = STAT_GREEN
        else:
            fill = STAT_RED
        draw.text((cursor, y), token, font=font, fill=fill)
        cursor += int(draw.textlength(token, font=font))
        last = match.end()
    if last < len(value):
        draw.text((cursor, y), value[last:], font=font, fill=TEXT)


def _wrap(text: str, font: Any, max_width: int) -> list[str]:
    if not text:
        return [""]
    # Preserve indentation for detail rows, then wrap by character.  This is
    # reliable for mixed Chinese/English and avoids breaking Cyrillic names.
    indent = text[: len(text) - len(text.lstrip(" "))]
    body = text[len(indent) :]
    lines: list[str] = []
    current = indent
    for char in body:
        candidate = current + char
        if ImageDraw is not None:
            width = font.getlength(candidate)
        else:  # pragma: no cover
            width = len(candidate) * 12
        if width <= max_width or current.strip() == "":
            current = candidate
        else:
            lines.append(current.rstrip())
            current = indent + char
    if current.strip() or not lines:
        lines.append(current.rstrip())
    return lines


def _remove_old_files(directory: Path, max_age_seconds: int = 86400) -> None:
    global _LAST_TEMP_CLEANUP
    now = time.time()
    # Rendering can happen several times per minute; scanning the temp folder
    # on every render is wasteful once it contains many old cards.
    if now - _LAST_TEMP_CLEANUP < 3600:
        return
    _LAST_TEMP_CLEANUP = now
    try:
        for path in directory.glob("*.png"):
            if now - path.stat().st_mtime > max_age_seconds:
                path.unlink(missing_ok=True)
    except OSError:
        pass


def _normalize_icon(icon: Any, size: int) -> Any:
    """Scale an RGBA icon to fill a square box without distorting it."""
    icon = icon.convert("RGBA")
    icon.thumbnail((size, size), Image.LANCZOS)
    if icon.width < size or icon.height < size:
        scale = min(size / icon.width, size / icon.height)
        if scale > 1:
            icon = icon.resize(
                (
                    max(1, round(icon.width * scale)),
                    max(1, round(icon.height * scale)),
                ),
                Image.LANCZOS,
            )
    return icon


@lru_cache(maxsize=128)
def _normalized_icon_cached(path: str, stamp_ns: int, size: int) -> Any:
    return _normalize_icon(Image.open(path), size)


def _load_normalized_icon(icon_path: str | Path, size: int) -> Any:
    path = Path(icon_path)
    return _normalized_icon_cached(str(path), path.stat().st_mtime_ns, size)


def _paste_corner_icon(
    image: Any,
    icon_path: str | Path | None,
    width: int,
    size: int = 124,
    *,
    pad: int = PAD,
    top: int = PAD - 4,
) -> bool:
    """Draw the top-right item icon in a consistent frame."""
    if image is None or icon_path is None or Image is None:
        return False
    try:
        icon = _load_normalized_icon(icon_path, size)
        left = width - pad - size + (size - icon.width) // 2
        icon_top = top + (size - icon.height) // 2
        image.paste(icon, (left, icon_top), icon)
        return True
    except Exception:
        return False


def _draw_candidate_icon(
    canvas: Any,
    icon_path: str,
    left: int,
    top: int,
    size: int,
) -> bool:
    """Draw a candidate icon with a neutral rim glow for dark artwork."""
    if canvas is None or Image is None:
        return False
    try:
        icon = _load_normalized_icon(icon_path, size)
        if ImageEnhance is not None:
            alpha = icon.getchannel("A")
            rgb = ImageEnhance.Brightness(icon.convert("RGB")).enhance(1.12)
            rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
            rgb = rgb.point(lambda value: int(255 * ((value / 255) ** 0.76)))
            icon = rgb.convert("RGBA")
            icon.putalpha(alpha)
        if ImageFilter is not None:
            pad = 7
            glow = Image.new(
                "RGBA", (size + pad * 2, size + pad * 2), (0, 0, 0, 0)
            )
            silhouette = Image.new("RGBA", icon.size, (190, 200, 212, 0))
            silhouette.putalpha(icon.getchannel("A"))
            glow.alpha_composite(silhouette, (pad, pad))
            glow = glow.filter(ImageFilter.GaussianBlur(5))
            glow.putalpha(
                glow.getchannel("A").point(lambda value: int(value * 0.42))
            )
            canvas.alpha_composite(glow, (left - pad, top - pad))
        canvas.alpha_composite(icon, (left, top))
        return True
    except Exception:
        return False


def _draw_candidate_icon_frame(
    canvas: Any, draw: Any, left: int, top: int, size: int
) -> None:
    """Subtle neutral gradient behind a candidate icon."""
    gradient = Image.new("RGBA", (1, size))
    for offset in range(size):
        ratio = offset / max(1, size - 1)
        gradient.putpixel(
            (0, offset),
            (
                int(32 - 17 * ratio),
                int(45 - 22 * ratio),
                int(60 - 27 * ratio),
                235,
            ),
        )
    gradient = gradient.resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=12, fill=255
    )
    canvas.paste(gradient, (left, top), mask)
    draw.rounded_rectangle(
        (left, top, left + size, top + size),
        radius=12,
        outline=(105, 130, 155, 90),
        width=1,
    )


@lru_cache(maxsize=6)
def _background_base(
    path: str, stamp_ns: int, width: int, height: int
) -> Any:
    """Resize/brighten/blur a wallpaper once per card size.

    Auction cards are rendered repeatedly at the same few heights; avoiding
    a fresh LANCZOS fit and Gaussian blur on every query removes the largest
    fixed cost in image output.  ``stamp_ns`` keeps the cache honest when the
    user swaps a custom background file.
    """
    base = Image.open(path).convert("RGB")
    base = ImageOps.fit(base, (width, height), method=Image.LANCZOS)
    base = ImageEnhance.Brightness(base).enhance(0.48)
    return base.filter(ImageFilter.GaussianBlur(1.4))


def _card_canvas(width: int, height: int, *, alpha: int = 232) -> Any:
    """Dark, wallpaper-backed canvas with a readable translucent card."""
    if Image is None or ImageDraw is None:
        return None
    try:
        background = _CARD_BACKGROUND
        if not background.is_file():
            background = HELP_BACKGROUND
        if (
            ImageEnhance is None
            or ImageFilter is None
            or ImageOps is None
            or not background.is_file()
        ):
            raise OSError("background unavailable")
        base = _background_base(
            str(background),
            background.stat().st_mtime_ns,
            width,
            height,
        )
        canvas = base.convert("RGBA")
    except Exception:
        canvas = Image.new("RGBA", (width, height), (16, 25, 35, 255))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, width, height), fill=(3, 7, 12, 35))
    panel_alpha = (
        _CARD_PANEL_ALPHA if _CARD_PANEL_ALPHA is not None else alpha
    )
    draw.rounded_rectangle(
        (12, 12, width - 12, height - 12),
        radius=26,
        fill=(10, 17, 26, panel_alpha),
        outline=(100, 122, 146, 70),
        width=2,
    )
    return Image.alpha_composite(canvas, overlay)


def render_text_card(
    text: str,
    *,
    font_path: str | None = None,
    width: int = WIDTH,
    icon_path: str | Path | None = None,
    item_meta: dict[str, Any] | None = None,
) -> Path | None:
    """Render a card-like text block to a PNG in the system temp directory."""
    if Image is None or ImageDraw is None or ImageFont is None:
        return None
    path = find_cjk_font(font_path)
    if path is None:
        return None

    try:
        title_font = ImageFont.truetype(str(path), 34)
        subtitle_font = ImageFont.truetype(str(path), 20)
        section_font = ImageFont.truetype(str(path), 24)
        body_font = ImageFont.truetype(str(path), 20)
        footer_font = ImageFont.truetype(str(path), 16)
        item_name_font = ImageFont.truetype(str(path), 30)
    except Exception:
        return None

    raw_lines = text.splitlines()
    # Drop the leading/trailing separators; the renderer draws its own rules.
    while raw_lines and raw_lines[0].strip() and set(raw_lines[0].strip()) <= SEP_CHARS:
        raw_lines.pop(0)
    while raw_lines and raw_lines[-1].strip() and set(raw_lines[-1].strip()) <= SEP_CHARS:
        raw_lines.pop()

    content_width = width - PAD * 2
    blocks: list[tuple[str, str, Any, str, int]] = []
    # (kind, text, font, color, gap_before)

    # First line = title, following lines before a separator = subtitle.
    title = ""
    subtitle: list[str] = []
    body_start = 0
    for index, line in enumerate(raw_lines):
        stripped = line.strip()
        if not stripped:
            continue
        if set(stripped) <= SEP_CHARS:
            body_start = index + 1
            break
        if not title:
            title = stripped
        else:
            subtitle.append(stripped)
    if not title:
        title = "STALZONE"
    blocks.append(("title", title, title_font, TEXT, 0))
    if item_meta:
        blocks.append(("spacer", "", body_font, TEXT, 60))
    else:
        for line in subtitle:
            blocks.append(("subtitle", line, subtitle_font, MUTED, 4))
    blocks.append(("rule", "", body_font, BORDER, 18))

    footer_start = len(raw_lines)
    for index in range(len(raw_lines) - 1, body_start - 1, -1):
        stripped = raw_lines[index].strip()
        if stripped and set(stripped) <= SEP_CHARS:
            footer_start = index
            break

    for index in range(body_start, footer_start):
        line = raw_lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            blocks.append(("gap", "", body_font, TEXT, 8))
            continue
        if set(stripped) <= SEP_CHARS:
            blocks.append(("rule", "", body_font, BORDER, 14))
            continue
        if stripped.startswith(("▸", "◆")):
            blocks.append(("section", stripped, section_font, ACCENT, 18))
            continue
        for wrapped in _wrap(line, body_font, content_width):
            blocks.append(("body", wrapped, body_font, TEXT, 3))

    footer = [line.strip() for line in raw_lines[footer_start:] if line.strip()]
    if footer:
        blocks.append(("rule", "", body_font, BORDER, 18))
        for line in footer:
            if set(line) <= SEP_CHARS:
                continue
            for wrapped in _wrap(line, footer_font, content_width):
                blocks.append(("footer", wrapped, footer_font, MUTED, 3))

    # Measure height. The signature sits immediately below the final content
    # line instead of being pinned to the bottom of a fixed-height card.
    height = PAD
    for kind, line, font, _color, gap in blocks:
        height += gap
        if kind == "rule":
            height += 2
        elif kind == "gap":
            height += 6
        elif kind == "spacer":
            pass  # the spacer gap was already added above
        else:
            bbox = font.getbbox(line or "Ag")
            height += bbox[3] - bbox[1] + 6
    content_height = height
    height = max(240, content_height + 8 + SIGNATURE_HEIGHT + 18)

    image = _card_canvas(width, height, alpha=214)
    if image is None:
        return None
    draw = ImageDraw.Draw(image)
    # Accent bar next to the title.
    draw.rounded_rectangle((PAD, PAD + 4, PAD + 7, PAD + 44), radius=3, fill=ACCENT)

    _paste_corner_icon(image, icon_path, width, 124)

    y = PAD
    left = PAD + 26 if title else PAD
    for kind, line, font, color, gap in blocks:
        y += gap
        if kind == "rule":
            draw.line((PAD, y, width - PAD, y), fill=color, width=1)
            y += 2
            continue
        if kind == "gap":
            y += 6
            continue
        if kind == "spacer":
            continue
        if kind == "title":
            draw.text((left, y), line, font=font, fill=color)
            bbox = font.getbbox(line or "Ag")
            y += bbox[3] - bbox[1] + 6
        elif (
            kind == "body"
            and item_meta
            and str(item_meta.get("cat") or "").startswith(("artefact", "attachment"))
            and "：" in line
            and re.search(r"[+-]\s*\d", line)
            and not line.startswith(("ID：", "类别：", "等级：", "距离衰减："))
        ):
            _draw_artifact_stat_line(draw, PAD, y, line, font)
            bbox = font.getbbox(line or "Ag")
            y += bbox[3] - bbox[1] + 6
        elif kind == "body" and line.startswith("等级："):
            rank = line[len("等级：") :].strip()
            colored = rank_color(rank)
            if colored:
                prefix = "等级："
                draw.text((PAD, y), prefix, font=font, fill=TEXT)
                draw.text(
                    (PAD + draw.textlength(prefix, font=font), y),
                    rank,
                    font=font,
                    fill=colored,
                )
            else:
                draw.text((PAD, y), line, font=font, fill=color)
            bbox = font.getbbox(line or "Ag")
            y += bbox[3] - bbox[1] + 6
        elif kind == "body" and (
            line.startswith("不用超载：") or line.startswith("使用超载：")
        ):
            match = re.match(
                r"^(不用超载|使用超载)：(.*?) → (\d+)(（\+\d+级）)$", line
            )
            if match:
                prefix = f"{match.group(1)}：{match.group(2)} → "
                level = match.group(3)
                suffix = match.group(4)
                draw.text((PAD, y), prefix, font=font, fill=TEXT)
                level_x = PAD + draw.textlength(prefix, font=font)
                draw.text((level_x, y), level, font=font, fill="#FFD166")
                draw.text(
                    (level_x + draw.textlength(level, font=font), y),
                    suffix,
                    font=font,
                    fill="#6FE0A8",
                )
            else:
                draw.text((PAD, y), line, font=font, fill=color)
            bbox = font.getbbox(line or "Ag")
            y += bbox[3] - bbox[1] + 6
        else:
            draw.text((PAD, y), line, font=font, fill=color)
            bbox = font.getbbox(line or "Ag")
            y += bbox[3] - bbox[1] + 6

    if item_meta:
        meta = item_meta if isinstance(item_meta, dict) else {}
        en = str(meta.get("en") or "").strip()
        zh = str(meta.get("zh") or "").strip()
        if not en:
            en = zh or str(meta.get("id") or "未知物品")
        show_zh = bool(zh and zh.casefold() != en.casefold())
        name_color = item_color(meta)
        name_y = PAD + 52
        name_width = width - left - PAD
        name = f"{en} ({zh})" if show_zh else en
        fitted = _fit_text(draw, name, item_name_font, name_width)
        draw.text((left, name_y), fitted, font=item_name_font, fill=name_color)

    _draw_signature(draw, width, y + 8, font_path, footer_font, max_bottom=height)

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        image.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def render_notice_card(
    view: dict[str, Any] | None,
    *,
    font_path: str | None = None,
    width: int = 1100,
) -> Path | None:
    """Render the selected N2 banner-style not-found card."""
    if (
        Image is None
        or ImageDraw is None
        or ImageFont is None
        or not isinstance(view, dict)
    ):
        return None
    path = find_cjk_font(font_path)
    if path is None:
        return None
    display_path = _find_display_font(font_path) or path
    mono_path = find_mono_font(path)
    try:
        eyebrow_font = ImageFont.truetype(str(mono_path or path), 13)
        header_region_font = ImageFont.truetype(str(path), 13)
        headline_font = ImageFont.truetype(str(display_path), 40)
        meta_font = ImageFont.truetype(str(path), 15)
        section_font = ImageFont.truetype(str(path), 14)
        note_font = ImageFont.truetype(str(path), 20)
        hint_font = ImageFont.truetype(str(path), 13)
        footer_font = ImageFont.truetype(str(path), 13)
    except Exception:
        return None

    kind = str(view.get("kind_label") or "数据").strip()
    query = str(view.get("query") or "").strip() or "未知"
    region = str(view.get("region") or "").strip().upper()
    now = str(view.get("now") or "").strip()
    note = str(view.get("note") or "").strip() or "请检查查询内容后重试。"
    accent = str(view.get("accent") or ACCENT)
    is_error = bool(view.get("error"))
    footer_text = str(view.get("footer") or "STALZONE · 查询结果")

    headline_labels = {
        "玩家": "没有找到这个玩家",
        "物品": "没有找到这个物品",
        "拍卖": "没有找到相关拍卖",
        "战队": "没有找到这个战队",
        "平衡调整": "没有找到相关调整",
    }
    headline = str(
        view.get("headline")
        or headline_labels.get(kind, "没有找到相关信息")
    )
    hints = {
        "玩家": "可尝试切换区服、检查角色名拼写，或直接提供 UUID。",
        "物品": "可尝试更短的关键词、检查物品 ID，或先查看候选。",
        "拍卖": "可尝试切换区服、检查物品名/ID，或先查看候选。",
        "战队": "可尝试切换区服、检查战队名/标签，或直接提供 UUID。",
        "平衡调整": "可尝试检查物品名/ID，或先确认物品是否存在。",
    }
    hint = str(
        view.get("hint") or hints.get(kind, "可尝试检查查询内容后重试。")
    )

    query_max_w = min(640, width - 2 * PAD - 150)
    query_size = 56
    query_font = ImageFont.truetype(str(display_path), query_size)
    query_lines = _wrap(query, query_font, query_max_w)
    while len(query_lines) > 2 and query_size > 38:
        query_size -= 2
        query_font = ImageFont.truetype(str(display_path), query_size)
        query_lines = _wrap(query, query_font, query_max_w)
    if len(query_lines) > 3:
        query_lines = query_lines[:3]
    query_line_h = max(58, query_size + 16)

    query_y = 150
    query_bottom = query_y + len(query_lines) * query_line_h
    meta_y = query_bottom + 20
    divider_y = meta_y + 42
    note_title_y = divider_y + 26
    note_lines = _wrap(note, note_font, width - 2 * PAD)[:3]
    note_y = note_title_y + 30
    hint_lines = _wrap(hint, hint_font, width - 2 * PAD)[:2]
    hint_y = note_y + len(note_lines) * 29 + 16
    content_bottom = hint_y + len(hint_lines) * 18 + 30
    footer_y = max(430, content_bottom + 24)
    height = footer_y + 82

    canvas = _card_canvas(width, height, alpha=238)
    if canvas is None:
        return None
    draw = ImageDraw.Draw(canvas)

    # Large, deliberately low-contrast watermark.
    if is_error:
        draw.text(
            (width - PAD, 76),
            str(view.get("watermark") or "RETRY"),
            font=ImageFont.truetype(str(display_path), 130),
            fill="#16222E",
            anchor="ra",
        )
    else:
        draw.text(
            (width - 404, 84),
            "404",
            font=ImageFont.truetype(str(display_path), 190),
            fill="#16222E",
        )
    draw.text(
        (PAD, 32),
        "STALZONE / SERVICE NOTICE" if is_error else "STALZONE / QUERY RESULT",
        font=eyebrow_font,
        fill=accent,
    )
    draw.text(
        (width - PAD, 32),
        f"{region} · RESULT" if region else "RESULT",
        font=header_region_font, fill=MUTED, anchor="ra",
    )
    draw.text((PAD, 94), headline, font=headline_font, fill=TEXT)
    qy = query_y
    for line in query_lines:
        draw.text((PAD, qy), line, font=query_font, fill=accent)
        qy += query_line_h

    meta_parts = [kind]
    if region:
        meta_parts.append(region)
    if now:
        meta_parts.append(f"{now} UTC+8")
    draw.text((PAD + 2, meta_y), " · ".join(meta_parts), font=meta_font, fill=MUTED)
    draw.line((PAD, divider_y, width - PAD, divider_y), fill=(90, 110, 130, 70), width=1)

    draw.text((PAD, note_title_y), "建议 / RECOMMENDATION", font=section_font, fill=accent)
    ny = note_y
    for line in note_lines:
        draw.text((PAD, ny), line, font=note_font, fill=TEXT)
        ny += 29
    hy = hint_y
    for line in hint_lines:
        draw.text((PAD, hy), line, font=hint_font, fill=MUTED)
        hy += 18
    draw.text(
        (PAD, hy + 6), "插件状态：/sz diag 或 /sz 状态",
        font=hint_font, fill="#71889A",
    )

    draw.line((PAD, footer_y, width - PAD, footer_y), fill=(90, 110, 130, 65), width=1)
    draw.text((PAD, footer_y + 12), footer_text, font=footer_font, fill=MUTED)
    _draw_signature(
        draw, width, height - 50, path, footer_font, max_bottom=height,
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_notice_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def _fit_text(draw: Any, text: str, font: Any, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    trimmed = text
    while trimmed and draw.textlength(trimmed + "…", font=font) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + "…") if trimmed else "…"


def _fit_auction_name(
    draw: Any, text: str, font: Any, max_width: int
) -> str:
    """Truncate the base name but keep `＋level` / `×amount` visible."""
    value = str(text)
    marker = ""
    for candidate in ("＋", "×"):
        index = value.rfind(candidate)
        if index <= 0:
            continue
        tail = value[index + 1 :]
        if tail and re.fullmatch(r"\d[\d,]*", tail):
            marker = candidate
            suffix = value[index:]
            base = value[:index].rstrip()
            break
    if not marker:
        return _fit_text(draw, value, font, max_width)
    suffix_w = int(draw.textlength(suffix, font=font))
    if max_width <= suffix_w + 12:
        return _fit_text(draw, suffix, font, max_width)
    fitted = _fit_text(draw, base, font, max_width - suffix_w - 4)
    return f"{fitted}{suffix}"


def _auction_name_column_width(
    active_width: float,
    recent_width: float,
    badge_extra: float,
    cap: float,
) -> float:
    """Budget the name column for both tables, including the recent indent.

    Recent rows start 16px to the right of the active rows and still end 12px
    before the price column, so their text needs 28px of the column itself.
    Six extra pixels keep a five-character name from ending in an ellipsis on
    rounding alone.
    """
    return min(
        max(
            160.0,
            active_width + 18 + badge_extra,
            recent_width + 34 + badge_extra,
        ),
        cap,
    )


def _find_display_font(explicit: str | None = None) -> Path | None:
    """Prefer a bold CJK face for the emission poster, then the configured font."""
    if ImageFont is None:
        return None
    candidates: list[Path] = []
    windir = os.getenv("WINDIR", "").strip()
    if windir:
        fonts = Path(windir) / "Fonts"
        candidates.extend(
            [
                fonts / "msyhbd.ttc",
                fonts / "simhei.ttf",
                fonts / "msyh.ttc",
            ]
        )
    candidates.extend(
        [
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        ]
    )
    if explicit:
        candidates.append(Path(explicit))
    for candidate in candidates:
        try:
            if candidate.is_file():
                ImageFont.truetype(str(candidate), 24)
                return candidate
        except Exception:
            continue
    return find_cjk_font(explicit)


def _emission_canvas(width: int, height: int) -> Any:
    """Doomsday-style dark poster: dim wallpaper, red core glow, trefoil watermark."""
    if Image is None or ImageDraw is None:
        return None
    try:
        background = _CARD_BACKGROUND
        if not background.is_file():
            background = HELP_BACKGROUND
        if (
            ImageEnhance is None
            or ImageFilter is None
            or ImageOps is None
            or not background.is_file()
        ):
            raise OSError("background unavailable")
        base = Image.open(background).convert("RGB")
        base = ImageOps.fit(base, (width, height), method=Image.LANCZOS)
        base = ImageEnhance.Brightness(base).enhance(0.20)
        base = base.filter(ImageFilter.GaussianBlur(2.1))
        canvas = base.convert("RGBA")
    except Exception:
        canvas = Image.new("RGBA", (width, height), (8, 8, 10, 255))

    size = 220
    glow = Image.new("L", (size, size), 0)
    pixels = glow.load()
    centre = size / 2
    for yy in range(size):
        for xx in range(size):
            dx = (xx - centre) / centre
            dy = (yy - centre) / centre
            distance = min(1.0, (dx * dx + dy * dy) ** 0.5)
            pixels[xx, yy] = int(255 * (max(0.0, 1.0 - distance) ** 2.2))
    glow = glow.resize((width, height), Image.LANCZOS)
    red = Image.new("RGBA", (width, height), (128, 16, 10, 255))
    canvas = Image.composite(red, canvas, glow.point(lambda value: int(value * 0.58)))

    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    for step in range(80):
        alpha = min(150, int(step * 1.7))
        vdraw.rectangle(
            (step, step, width - step, height - step),
            outline=(0, 0, 0, alpha),
            width=1,
        )
    canvas = Image.alpha_composite(canvas, vignette)

    icon_path = Path(__file__).with_name("assets") / "factions" / "stalkers.png"
    try:
        icon = Image.open(icon_path).convert("RGBA")
        icon_size = max(380, int(min(width, height) * 0.68))
        scale = icon_size / max(icon.size)
        icon = icon.resize(
            (int(icon.width * scale), int(icon.height * scale)), Image.LANCZOS
        )
        alpha = icon.getchannel("A").point(lambda value: int(value * 0.10))
        tint = Image.new("RGBA", icon.size, (190, 38, 22, 255))
        tint.putalpha(alpha)
        canvas.alpha_composite(
            tint,
            ((width - icon.width) // 2, (height - icon.height) // 2),
        )
    except Exception:
        pass

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (16, 16, width - 16, height - 16),
        radius=24,
        outline=(150, 45, 30, 130),
        width=2,
    )
    draw.rectangle((0, 0, width, 9), fill=(165, 28, 18, 220))
    draw.rectangle((0, height - 9, width, height), fill=(165, 28, 18, 220))
    for x in range(-height, width, 72):
        draw.line((x, 0, x + 36, 10), fill=(210, 55, 35, 70), width=3)
        draw.line((x, height - 10, x + 36, height), fill=(210, 55, 35, 70), width=3)
    return canvas


def render_emission_alert_card(
    view: dict[str, Any] | None,
    *,
    font_path: str | None = None,
    width: int = 1200,
    height: int = 700,
) -> Path | None:
    """Render the proactive "emission started" alert in the same poster style."""
    if (
        Image is None
        or ImageDraw is None
        or ImageFont is None
        or not isinstance(view, dict)
        or not view.get("headline")
    ):
        return None
    path = _find_display_font(font_path)
    if path is None:
        return None
    canvas = _emission_canvas(width, height)
    if canvas is None:
        return None
    draw = ImageDraw.Draw(canvas)
    try:
        header_font = ImageFont.truetype(str(path), 32)
        kicker_font = ImageFont.truetype(str(path), 15)
        headline_font = ImageFont.truetype(str(path), 66)
        clock_font = ImageFont.truetype(str(path), 118)
        sub_font = ImageFont.truetype(str(path), 21)
        small_font = ImageFont.truetype(str(path), 16)
        chip_font = ImageFont.truetype(str(path), 18)
        action_font = ImageFont.truetype(str(path), 27)
        artifact_font = ImageFont.truetype(str(path), 20)
        tip_font = ImageFont.truetype(str(path), 14)
    except Exception:
        return None

    red = "#ff4b32"
    ember = "#ff9b5c"
    bone = "#f2e6d0"
    muted = "#b49a83"
    pad = 60
    centre = width / 2
    draw.rectangle((pad, 46, pad + 6, 90), fill=red)
    draw.text((pad + 22, 38), "STALZONE · 辐射风暴警报", font=header_font, fill=bone)
    draw.text(
        (width - pad, 44), f"{view.get('region', '')} · 自动监测",
        font=small_font, fill=muted, anchor="ra",
    )
    chip_text = "风暴进行中"
    chip_w = int(draw.textlength(chip_text, font=chip_font)) + 50
    chip_x = width - pad - chip_w
    draw.rounded_rectangle(
        (chip_x, 78, chip_x + chip_w, 116), radius=19,
        fill=(35, 8, 6, 220), outline=red, width=2,
    )
    draw.ellipse((chip_x + 14, 91, chip_x + 24, 101), fill=red)
    draw.text((chip_x + 32, 84), chip_text, font=chip_font, fill=red)

    draw.text(
        (centre, 154), "E M I S S I O N   D E T E C T E D",
        font=kicker_font, fill="#b34735", anchor="mm",
    )
    draw.text((centre, 204), "风暴已开始", font=headline_font, fill=bone, anchor="mm")

    clock = str(view.get("start_clock") or "--:--")
    clock_x = centre
    if ImageFilter is not None:
        halo_mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(halo_mask).text(
            (clock_x, 310), clock, font=clock_font, fill=255, anchor="mm"
        )
        halo_mask = halo_mask.filter(ImageFilter.GaussianBlur(25))
        halo = Image.new("RGBA", (width, height), (255, 55, 30, 255))
        halo.putalpha(halo_mask.point(lambda value: int(value * 0.5)))
        canvas.alpha_composite(halo)
    draw.text(
        (clock_x + 4, 316), clock, font=clock_font,
        fill=(0, 0, 0, 160), anchor="mm",
    )
    draw.text(
        (clock_x, 310), clock, font=clock_font, fill=red, anchor="mm",
        stroke_width=2, stroke_fill=(60, 5, 2, 255),
    )
    draw.text(
        (centre, 390),
        f"实际开始于 {view.get('start_date', '')}  ·  {view.get('region', '')}",
        font=sub_font, fill=bone, anchor="mm",
    )
    draw.text(
        (centre, 424),
        f"已持续 {view.get('elapsed_text', '—')}",
        font=small_font, fill=muted, anchor="mm",
    )
    draw.text(
        (centre, 466),
        str(view.get("artifact_notice") or "风暴结束后 30 分钟内将伴随神器爆发"),
        font=artifact_font, fill="#ffb27a", anchor="mm",
    )
    draw.text((centre, 506), "请尽快上线", font=action_font, fill=ember, anchor="mm")

    draw.line((pad, 546, width - pad, 546), fill=(150, 45, 30, 130), width=1)
    draw.text(
        (pad, 562),
        f"实际开始：{view.get('start_time', '')}",
        font=small_font, fill=muted,
    )
    draw.text(
        (width - pad, 562),
        "自动检测 · 官方 API · UTC+8",
        font=small_font, fill=muted, anchor="ra",
    )
    draw.text(
        (pad, height - 70),
        str(view.get("more_tip") or "更多功能：sz help 获取菜单"),
        font=tip_font,
        fill=muted,
    )
    draw.text(
        (pad, height - 42),
        str(view.get("artifact_tip") or "Tip：神器会在大世界的各处异常点中生成"),
        font=tip_font,
        fill=muted,
    )
    _draw_signature(
        draw,
        width,
        height - 58,
        path,
        small_font,
        max_bottom=height,
        more_tip=False,
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_emission_alert_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def render_emission_card(
    view: dict[str, Any] | None,
    *,
    font_path: str | None = None,
    width: int = 1200,
    height: int = 780,
) -> Path | None:
    """Render the emission query as a large doomsday-style count-up poster."""
    if (
        Image is None
        or ImageDraw is None
        or ImageFont is None
        or not isinstance(view, dict)
        or not view.get("headline")
    ):
        return None
    path = _find_display_font(font_path)
    if path is None:
        return None

    canvas = _emission_canvas(width, height)
    if canvas is None:
        return None
    draw = ImageDraw.Draw(canvas)

    try:
        header_font = ImageFont.truetype(str(path), 32)
        sub_font = ImageFont.truetype(str(path), 19)
        kicker_font = ImageFont.truetype(str(path), 15)
        chip_font = ImageFont.truetype(str(path), 21)
        label_font = ImageFont.truetype(str(path), 54)
        detail_font = ImageFont.truetype(str(path), 22)
        small_font = ImageFont.truetype(str(path), 16)
        value_font = ImageFont.truetype(str(path), 18)
    except Exception:
        return None

    alert_red = "#ff4b32"
    ember = "#ff8a4c"
    bone = "#f2e6d0"
    muted = "#a89684"
    dim_red = "#8f3d30"
    pad = 60
    centre_x = width / 2
    state_key = str(view.get("state_key") or "unknown")
    state_label = str(view.get("state_label") or "暂无数据")
    active = state_key == "active"
    state_color = alert_red if active else ("#d9a05c" if state_key == "idle" else muted)

    draw.rectangle((pad, 50, pad + 6, 94), fill=alert_red)
    draw.text((pad + 22, 42), "STALZONE · 辐射爆发", font=header_font, fill=bone)
    draw.text(
        (pad, 92),
        f"{view.get('region', '')}｜{view.get('now', '')} UTC+8",
        font=sub_font,
        fill=muted,
    )

    draw.text(
        (width - pad, 48),
        "R A D I A T I O N   A L E R T",
        font=kicker_font,
        fill=dim_red,
        anchor="ra",
    )
    chip_text = state_label
    chip_width = int(draw.textlength(chip_text, font=chip_font)) + 58
    chip_x = width - pad - chip_width
    chip_y = 80
    draw.rounded_rectangle(
        (chip_x, chip_y, chip_x + chip_width, chip_y + 42),
        radius=21,
        fill=(28, 7, 6, 205),
        outline=state_color,
        width=2,
    )
    draw.ellipse(
        (chip_x + 16, chip_y + 15, chip_x + 26, chip_y + 25),
        fill=state_color,
    )
    draw.text(
        (chip_x + 34, chip_y + 8),
        chip_text,
        font=chip_font,
        fill=state_color,
    )

    kicker = (
        "C U R R E N T   E M I S S I O N"
        if active
        else "T I M E   S I N C E   L A S T   E M I S S I O N"
    )
    draw.text((centre_x, 180), kicker, font=kicker_font, fill=dim_red, anchor="mm")

    headline = str(view["headline"])
    label_y = 232
    draw.text((centre_x, label_y), headline, font=label_font, fill=bone, anchor="mm")
    label_width = draw.textlength(headline, font=label_font)
    for direction in (-1, 1):
        inner = centre_x + direction * (label_width / 2 + 28)
        outer = inner + direction * 76
        draw.line((inner, label_y, outer, label_y), fill=(150, 50, 35, 180), width=2)

    elapsed = str(view.get("elapsed_text") or "暂无数据")
    time_size = 118
    max_time_width = width - pad * 2 - 80
    while time_size > 54:
        time_font = ImageFont.truetype(str(path), time_size)
        if draw.textlength(elapsed, font=time_font) <= max_time_width:
            break
        time_size -= 4
    time_font = ImageFont.truetype(str(path), time_size)
    time_y = 358
    if ImageFilter is not None:
        halo_mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(halo_mask).text(
            (centre_x, time_y),
            elapsed,
            font=time_font,
            fill=255,
            anchor="mm",
        )
        halo_mask = halo_mask.filter(ImageFilter.GaussianBlur(24))
        halo = Image.new("RGBA", (width, height), (255, 55, 30, 255))
        halo.putalpha(halo_mask.point(lambda value: int(value * 0.55)))
        canvas.alpha_composite(halo)
    draw.text(
        (centre_x + 4, time_y + 6),
        elapsed,
        font=time_font,
        fill=(0, 0, 0, 165),
        anchor="mm",
    )
    draw.text(
        (centre_x, time_y),
        elapsed,
        font=time_font,
        fill=alert_red,
        anchor="mm",
        stroke_width=2,
        stroke_fill=(60, 5, 2, 255),
    )

    rule_y = 452
    draw.line(
        (centre_x - 250, rule_y, centre_x + 250, rule_y),
        fill=(150, 45, 30, 150),
        width=2,
    )
    draw.text(
        (centre_x, 492),
        _fit_text(draw, str(view.get("reference_line") or ""), detail_font, width - pad * 2),
        font=detail_font,
        fill=bone,
        anchor="mm",
    )
    details = view.get("details") or []
    for index, line in enumerate(details[:2]):
        draw.text(
            (centre_x, 534 + index * 32),
            _fit_text(draw, str(line), value_font, width - pad * 2),
            font=value_font,
            fill=muted,
            anchor="mm",
        )

    bottom_y = 650
    draw.text(
        (pad + 10, bottom_y),
        f"状态：{state_label}",
        font=value_font,
        fill=state_color,
    )
    draw.text(
        (width - pad - 10, bottom_y),
        f"区服：{view.get('region', '')}",
        font=value_font,
        fill=muted,
        anchor="ra",
    )

    footer = _fit_text(
        draw,
        str(view.get("footer") or ""),
        small_font,
        width - pad * 2 - 280,
    )
    draw.text((pad + 10, 694), footer, font=small_font, fill=muted)
    _draw_signature(
        draw,
        width,
        height - 62,
        path,
        small_font,
        right_margin=62,
        max_bottom=height,
        tip_color=muted,
        tip_x=pad,
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_emission_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def render_help_card(
    *,
    region: str = "EU",
    demo: bool = False,
    version: str = "",
    font_path: str | None = None,
    background_path: str | Path | None = None,
    output: str | Path | None = None,
) -> Path | None:
    """Render the full help menu as a cached, wallpaper-backed card."""
    if Image is None or ImageDraw is None or ImageFont is None:
        return None
    font_file = find_cjk_font(font_path)
    if font_file is None:
        return None
    if (
        ImageEnhance is None
        or ImageFilter is None
        or ImageOps is None
    ):
        return None
    try:
        title_font = ImageFont.truetype(str(font_file), 64)
        subtitle_font = ImageFont.truetype(str(font_file), 24)
        chip_font = ImageFont.truetype(str(font_file), 19)
        tag_font = ImageFont.truetype(str(font_file), 18)
        command_font = ImageFont.truetype(str(font_file), 23)
        desc_font = ImageFont.truetype(str(font_file), 19)
        index_font = ImageFont.truetype(str(font_file), 40)
        small_font = ImageFont.truetype(str(font_file), 17)
    except Exception:
        return None

    width, height = HELP_WIDTH, HELP_HEIGHT
    background = Path(background_path) if background_path else _CARD_BACKGROUND
    try:
        canvas = Image.open(background).convert("RGB")
        canvas = ImageOps.fit(canvas, (width, height), method=Image.LANCZOS)
        canvas = ImageEnhance.Brightness(canvas).enhance(0.64)
        canvas = canvas.filter(ImageFilter.GaussianBlur(1.1))
        canvas = canvas.convert("RGBA")
    except Exception:
        canvas = Image.new("RGBA", (width, height), (8, 14, 22, 255))

    shade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.rectangle((0, 0, width, height), fill=(4, 8, 14, 95))
    sd.rectangle((0, 0, width, 200), fill=(3, 7, 12, 80))
    sd.rectangle((0, height - 120, width, height), fill=(3, 7, 12, 95))
    canvas = Image.alpha_composite(canvas, shade)

    chips = [
        f"{region.upper()} · {'演示环境' if demo else '生产环境'}",
        "UTC+8",
        f"v{version}" if version else "STALZONE",
    ]
    chip_boxes: list[tuple[str, int, int, int, int]] = []
    chip_right = width - 60
    for text in reversed(chips):
        chip_w = int(chip_font.getlength(text)) + 34
        chip_boxes.append((text, chip_right - chip_w, 52, chip_w, 38))
        chip_right -= chip_w + 10
    chip_boxes.reverse()

    modules = [
        (
            "拍卖行",
            "AUCTION",
            "/sz 拍卖 <物品> [品质] [日期] [数量]",
            ["查看在售、成交与成交历史", "可按品质、日期、数量筛选"],
            ACCENT,
        ),
        (
            "辐射爆发",
            "EMISSION",
            "/sz 风暴 [区服]",
            ["查看上次风暴时间与当前状态", "可指定 EU/RU/NA/SEA/NEA"],
            GREEN,
        ),
        (
            "玩家资料",
            "PLAYER",
            "/sz 玩家 <角色名/UUID> [区服]",
            ["查看角色资料、战队与区服", "可指定 EU/RU/NA/SEA/NEA，默认配置区服"],
            "#4EA8FF",
        ),
        (
            "战队",
            "CLAN",
            "/sz 战队 <名称/括号标签/ID>",
            ["优先匹配名称括号内标签", "标签长度不限，不区分大小写"],
            "#FF6FB5",
        ),
        (
            "物品图鉴",
            "ITEM",
            "/sz 物品 <中文名/英文名/ID>",
            ["查看物品属性、描述和 ID", "支持中文名、英文名与物品 ID"],
            "#FFD166",
        ),
        (
            "调整历史",
            "BALANCE",
            "/sz 调整 <装备>",
            ["查看官方平衡调整历史", "覆盖 2023-2026 武器/神器/配件"],
            "#FF9D5C",
        ),
        (
            "通行证计算",
            "PASS",
            "/sz 通行证计算 <等级> <每日> [超载] <天数> [周天数]",
            ["计算通行证经验与等级预测", "支持超载、剩余天数与每周天数"],
            "#B69CFF",
        ),
        (
            "其他",
            "MORE",
            "/sz 战队列表 · /sz 行动 · /sz 区服 · /sz 帮助",
            ["战队列表、行动记录、区服列表", "候选 /sz 候选 <序号>｜诊断 /sz diag / 状态"],
            "#8FA2B8",
        ),
    ]
    card_w = (width - 120 - 24) // 2
    card_h = 180
    start_y = 214
    row_gap = 20
    cards: list[tuple[int, str, str, str, list[str], str, int, int]] = []
    for index, (tag, code, command, lines, color) in enumerate(modules, 1):
        x = 60 + ((index - 1) % 2) * (card_w + 24)
        y = start_y + ((index - 1) // 2) * (card_h + row_gap)
        cards.append((index, tag, code, command, lines, color, x, y))

    panels = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panels)
    for _text, x, y, chip_w, chip_h in chip_boxes:
        pd.rounded_rectangle(
            (x, y, x + chip_w, y + chip_h),
            radius=19,
            fill=(5, 10, 17, 155),
            outline=(255, 255, 255, 36),
            width=1,
        )
    for _index, _tag, _code, _command, _lines, _color, x, y in cards:
        pd.rounded_rectangle(
            (x, y, x + card_w, y + card_h),
            radius=20,
            fill=(7, 13, 21, 176),
            outline=(255, 255, 255, 30),
            width=1,
        )
    canvas = Image.alpha_composite(canvas, panels)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((18, 18, width - 18, height - 18), radius=30, outline="#334353", width=2)
    draw.rounded_rectangle((60, 54, 68, 120), radius=4, fill=ACCENT)
    draw.text((90, 30), "STALZONE", font=title_font, fill=TEXT)
    draw.text(
        (92, 112),
        "数据查询帮助  ·  斜杠可省略，sz 后加空格即可触发",
        font=subtitle_font,
        fill="#C6D3E2",
    )
    for text, x, y, chip_w, chip_h in chip_boxes:
        draw.text((x + 17, y + 8), text, font=chip_font, fill="#DCE7F3")
    draw.line((60, 186, width - 60, 186), fill="#3A4A5C", width=1)

    for index, tag, code, command, lines, color, x, y in cards:
        draw.rounded_rectangle((x + 22, y + 24, x + 28, y + card_h - 24), radius=3, fill=color)
        draw.text((x + 48, y + 20), f"{tag}  /  {code}", font=tag_font, fill=color)
        draw.text(
            (x + card_w - 76, y + 12),
            f"{index:02d}",
            font=index_font,
            fill="#5B6C80",
        )
        fitted = _fit_text(draw, command, command_font, card_w - 150)
        draw.text((x + 48, y + 56), fitted, font=command_font, fill="#F2F6FB")
        for line_index, line in enumerate(lines):
            fitted_line = _fit_text(draw, line, desc_font, card_w - 100)
            draw.text(
                (x + 48, y + 102 + line_index * 28),
                fitted_line,
                font=desc_font,
                fill="#A9BACD",
            )

    draw.line((60, 1018, width - 60, 1018), fill="#2A3A4A", width=1)

    footer = "数据：STALZONE 官方 API｜时间：UTC+8｜玩家/战队/风暴可加区服 EU/RU/NA/SEA/NEA｜背景：可配置官方壁纸"
    draw.text((60, 1030), footer, font=small_font, fill="#8FA2B8")
    _draw_signature(
        draw,
        width,
        1052,
        font_file,
        small_font,
        right_margin=60,
        max_bottom=height,
        more_tip=False,
    )

    if output is not None:
        target = Path(output)
        temporary: Path | None = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".tmp")
            canvas.convert("RGB").save(temporary, "PNG", compress_level=1)
            temporary.replace(target)
            return target
        except OSError:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    target = out_dir / f"sz_help_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(target, "PNG", compress_level=1)
    except OSError:
        return None
    return target


def rank_color(rank: Any) -> str | None:
    return RANK_COLORS.get(str(rank or "").strip().lower())


def item_color(meta: dict[str, Any] | None) -> str:
    meta = meta if isinstance(meta, dict) else {}
    mapped = ITEM_COLOR_MAP.get(str(meta.get("color") or "").strip().upper())
    if mapped:
        return mapped
    return rank_color(meta.get("rank")) or TEXT


def _draw_signature(
    draw: Any,
    width: int,
    y: int,
    font_path: str | Path | None = None,
    fallback_font: Any = None,
    *,
    right_margin: int = PAD,
    max_bottom: int | None = None,
    more_tip: bool = True,
    tip_color: str = MUTED,
    tip_x: int = PAD,
) -> int:
    """Draw the bottom-right artistic signature with a shared text baseline."""
    if ImageFont is None:
        return y
    if max_bottom is not None:
        # Keep the signature and the shared-baseline tip inside the rounded
        # border (inset 12px) with a small visible margin.
        y = max(0, min(y, int(max_bottom) - SIGNATURE_HEIGHT - 16))
    art_path = _find_artist_font(font_path)
    name_path = find_cjk_font(str(font_path) if font_path else None)
    if art_path is None and name_path is None:
        return y
    try:
        art_font = ImageFont.truetype(str(art_path or name_path), 28)
        name_font = (
            ImageFont.truetype(str(name_path), 19)
            if name_path is not None
            else fallback_font
        )
    except Exception:
        if fallback_font is None:
            return y
        art_font = fallback_font
        name_font = fallback_font
    if name_font is None:
        name_font = art_font
    art_ascent, art_descent = art_font.getmetrics()
    name_ascent, name_descent = name_font.getmetrics()
    baseline = y + max(art_ascent, name_ascent)
    if more_tip:
        tip_font = None
        for size in (15, 14):
            try:
                tip_font = ImageFont.truetype(str(name_path or art_path), size)
                break
            except Exception:
                continue
        if tip_font is None and fallback_font is not None:
            tip_font = fallback_font
        if tip_font is not None:
            tip_ascent, _ = tip_font.getmetrics()
            draw.text(
                (tip_x, baseline - tip_ascent),
                MORE_FEATURES_TIP,
                font=tip_font,
                fill=tip_color,
            )
    if CREATOR_WATERMARK_HIDDEN:
        return y
    prefix_w = draw.textlength(SIGNATURE_PREFIX, font=art_font)
    gap = 9
    name_w = draw.textlength(SIGNATURE_NAME, font=name_font)
    total_w = prefix_w + gap + name_w
    x = max(16, width - right_margin - int(total_w))
    art_top = baseline - art_ascent
    name_top = baseline - name_ascent
    # Soft drop shadow + gold script text; both parts share one baseline.
    draw.text(
        (x + 1, art_top + 2),
        SIGNATURE_PREFIX,
        font=art_font,
        fill="#3b2d18",
    )
    draw.text(
        (x, art_top),
        SIGNATURE_PREFIX,
        font=art_font,
        fill=SIGNATURE_COLOR,
    )
    draw.text(
        (x + prefix_w + gap + 1, name_top + 1),
        SIGNATURE_NAME,
        font=name_font,
        fill="#3b2d18",
    )
    draw.text(
        (x + prefix_w + gap, name_top),
        SIGNATURE_NAME,
        font=name_font,
        fill="#d9c79f",
    )
    return max(
        y + SIGNATURE_HEIGHT,
        baseline + max(art_descent, name_descent) + 2,
    )


def _color_is_dark(color: str) -> bool:
    value = str(color or "").lstrip("#")
    if len(value) != 6:
        return False
    try:
        red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    return (red * 299 + green * 587 + blue * 114) / 255000 < 0.26


def _draw_pda_line(
    draw: Any,
    x: int,
    y: int,
    line: str,
    font: Any,
    default_color: str = TEXT,
) -> int:
    """Draw one PDA-formatted line and return its width."""
    start = x
    for run, color in parse_pda_segments(line, default_color):
        if not run:
            continue
        if _color_is_dark(color):
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                draw.text((x + dx, y + dy), run, font=font, fill="#9DB0C2")
        draw.text((x, y), run, font=font, fill=color)
        x += int(draw.textlength(run, font=font))
    return x - start


def _profile_bio_layout(
    view: dict[str, Any],
    width: int,
    body_font: Any,
    mono_path: Path | None,
    cjk_mono_path: Path | None = None,
) -> dict[str, Any]:
    raw_lines = [line.rstrip() for line in str(view.get("bio") or "").splitlines()]
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()
    raw_lines = raw_lines[:22]
    plain_lines = [strip_pda_formatting(line) for line in raw_lines]
    art_like = any(
        len(line) > 55 or (len(line) > 20 and line.count("  ") >= 3)
        for line in plain_lines
    )
    has_cjk = any(re.search(r"[一-鿿]", line) for line in plain_lines)
    max_width = width - 2 * PAD - 36
    art_path = (cjk_mono_path or mono_path) if has_cjk else mono_path
    if art_like and art_path is not None:
        size = 13
        font = ImageFont.truetype(str(art_path), size)
        while size > 8 and max(
            (font.getlength(line) for line in plain_lines), default=0
        ) > max_width:
            size -= 1
            font = ImageFont.truetype(str(art_path), size)
        line_h = size + 4
    elif art_like:
        font = body_font
        line_h = 20
    else:
        font = body_font
        line_h = 26
    return {
        "lines": raw_lines,
        "font": font,
        "line_h": line_h,
        "height": 36 + len(raw_lines) * line_h if raw_lines else 0,
        "art_like": art_like,
    }


def _profile_fact(
    draw: Any,
    x: int,
    y: int,
    label: str,
    value: str,
    label_font: Any,
    value_font: Any,
    max_width: int,
) -> None:
    draw.text((x, y), label, font=label_font, fill=MUTED)
    label_width = int(draw.textlength(label, font=label_font))
    fitted = _fit_text(draw, value, value_font, max(40, max_width - label_width - 12))
    draw.text((x + label_width + 10, y), fitted, font=value_font, fill=TEXT)


def _draw_section_heading(draw: Any, x: int, y: int, text: str, fnt: Any, accent: str = ACCENT) -> None:
    """Draw a section label with the accent aligned to the actual glyph box."""
    draw.text((x + 12, y), text, font=fnt, fill=TEXT)
    try:
        bbox = fnt.getbbox(text)
        top = y + int(bbox[1])
        bottom = y + int(bbox[3])
    except Exception:
        top, bottom = y + 2, y + 20
    if bottom - top < 12:
        top, bottom = y + 2, y + 20
    draw.rounded_rectangle((x, top, x + 4, bottom), radius=2, fill=accent)


def render_profile_card(
    view: dict[str, Any],
    *,
    font_path: str | None = None,
) -> Path | None:
    """Render the selected tactical-dossier profile layout."""
    if Image is None or ImageDraw is None or ImageFont is None:
        return None
    path = find_cjk_font(font_path)
    if path is None:
        return None
    display_path = _find_display_font(font_path) or path
    mono_path = find_mono_font(path)
    cjk_mono_path = find_cjk_mono_font(path)
    try:
        title_font = ImageFont.truetype(str(display_path), 37)
        section_font = ImageFont.truetype(str(path), 21)
        body_font = ImageFont.truetype(str(path), 20)
        small_font = ImageFont.truetype(str(path), 15)
        label_font = ImageFont.truetype(str(path), 13)
        chip_font = ImageFont.truetype(str(path), 14)
        metric_font = ImageFont.truetype(str(path), 17)
        score_font = ImageFont.truetype(str(display_path), 54)
        hero_score_font = ImageFont.truetype(str(display_path), 48)
        pvp_label_font = ImageFont.truetype(str(display_path), 18)
        meta_label_font = ImageFont.truetype(str(path), 16)
        meta_value_font = ImageFont.truetype(str(path), 17)
        combat_label_font = ImageFont.truetype(str(path), 18)
        combat_value_font = ImageFont.truetype(str(path), 20)
        stat_label_font = ImageFont.truetype(str(path), 18)
        stat_value_font = ImageFont.truetype(str(path), 19)
        achievement_font = ImageFont.truetype(str(path), 16)
        mono_font = ImageFont.truetype(str(mono_path or path), 14)
    except Exception:
        return None

    width = 1200
    left_x, left_w = PAD, 330
    right_x = 408
    right_w = width - right_x - PAD
    header_y = 36
    divider_y = 68
    content_y = 104

    bio = _profile_bio_layout(
        view, right_w + 2 * PAD, body_font, mono_path, cjk_mono_path
    )
    bio_lines = bio.get("lines") or []
    bio_height = int(bio.get("height") or 0)
    stat_rows = [str(row) for row in (view.get("stat_rows") or [])]
    stat_note = ""
    if stat_rows and stat_rows[-1].startswith("另有"):
        stat_note = stat_rows.pop()
    per_col = max(1, (len(stat_rows) + 1) // 2)
    stats_height = per_col * 36
    achievements = [str(x) for x in (view.get("achievements") or [])]
    hq = view.get("hq") if isinstance(view.get("hq"), dict) else None
    ach_y = 692
    ach_chip_h = 44
    ach_gap = 10
    ach_block_h = len(achievements) * ach_chip_h + max(0, len(achievements) - 1) * ach_gap if achievements else 0
    ach_end = ach_y + 30 + ach_block_h if achievements else 0

    y = content_y
    if bio_height:
        y += 42 + bio_height + 28
    y += 42 + 128 + 24  # combat heading + panel + gap
    y += 42 + stats_height + (24 if stat_note else 0) + 28
    right_end = y
    height = max(1120, right_end + 110, ach_end + 300 if achievements else 0)

    image = _card_canvas(width, height, alpha=232)
    if image is None:
        return None
    draw = ImageDraw.Draw(image)

    draw.text(
        (PAD, header_y), "STALZONE / PLAYER DOSSIER",
        font=mono_font, fill="#7FC4FF",
    )
    draw.text(
        (width - PAD, header_y), f"{view.get('region', '')} · PUBLIC RECORD",
        font=mono_font, fill=MUTED, anchor="ra",
    )
    draw.line((PAD, divider_y, width - PAD, divider_y), fill=(90, 110, 130, 90), width=1)

    # Left identity rail. Keep it dark: no full-height accent stripe.
    rail_top = 92
    rail_bottom = height - 44
    draw.rounded_rectangle(
        (left_x, rail_top, left_x + left_w, rail_bottom),
        radius=18, fill=(8, 14, 23, 215),
        outline=(100, 130, 160, 85), width=1,
    )
    faction_path = faction_icon_path(str(view.get("alliance_raw") or ""))
    if faction_path is not None:
        try:
            faction = Image.open(faction_path).convert("RGBA")
            bbox = faction.getchannel("A").getbbox()
            if bbox:
                faction = faction.crop(bbox)
            faction.thumbnail((176, 176), Image.LANCZOS)
            fx = left_x + (left_w - faction.width) // 2
            image.alpha_composite(faction, (fx, rail_top + 58))
        except Exception:
            pass
    faction_label = f"{view.get('alliance', '未知')} / {str(view.get('alliance_raw') or '').upper()}"
    draw.text(
        (left_x + left_w // 2, rail_top + 190),
        faction_label,
        font=chip_font, fill="#FFD166", anchor="ma",
    )
    raw_name = str(view.get("name") or "未知")
    name_size = 37
    name_font = title_font
    while name_size > 22 and name_font.getlength(raw_name) > left_w - 34:
        name_size -= 1
        name_font = ImageFont.truetype(str(display_path), name_size)
    draw.text(
        (left_x + left_w // 2, rail_top + 218),
        _fit_text(draw, raw_name, name_font, left_w - 34),
        font=name_font, fill=TEXT, anchor="ma",
    )

    region_text = f"区服 {str(view.get('region') or '未知').upper()}"
    region_w = int(draw.textlength(region_text, font=chip_font)) + 26
    chip_x = left_x + (left_w - region_w) // 2
    draw.rounded_rectangle(
        (chip_x, rail_top + 290, chip_x + region_w, rail_top + 322),
        radius=16, fill=(18, 39, 57, 235),
        outline=(90, 160, 210, 160), width=1,
    )
    draw.text((chip_x + 13, rail_top + 297), region_text, font=chip_font, fill="#9FD4FF")
    draw.line(
        (left_x + 24, rail_top + 338, left_x + left_w - 24, rail_top + 338),
        fill=(110, 135, 160, 70), width=1,
    )

    meta_rows = [
        ("战队", str(view.get("clan_label") or "无")),
        ("职位", str(view.get("clan_rank") or "—")),
        (
            "战队等级",
            str(
                view.get("clan_level")
                if view.get("clan_level") is not None
                else ("未公开" if view.get("has_clan") else "—")
            ),
        ),
        ("最后登录", str(view.get("last_login") or "未知").replace(" UTC+8", "")),
    ]
    my = rail_top + 360
    for key, value in meta_rows:
        draw.text((left_x + 26, my), key, font=meta_label_font, fill="#B4C6D6")
        fitted = _fit_text(draw, value, meta_value_font, left_w - 100)
        draw.text(
            (left_x + left_w - 26 - int(draw.textlength(fitted, font=meta_value_font)), my),
            fitted, font=meta_value_font, fill=TEXT,
        )
        my += 48

    if achievements:
        _draw_section_heading(
            draw, left_x + 24, ach_y, "展示成就 / ACHIEVEMENTS",
            ImageFont.truetype(str(path), 15), "#FFD166",
        )
        cy = ach_y + 30
        for item in achievements:
            draw.rounded_rectangle(
                (left_x + 24, cy, left_x + left_w - 24, cy + ach_chip_h),
                radius=12, fill=(17, 25, 34, 235), outline=(82, 104, 124, 90), width=1,
            )
            draw.ellipse((left_x + 39, cy + 18, left_x + 47, cy + 26), fill="#9DB8CC")
            draw.text(
                (left_x + 58, cy + 11),
                _fit_text(draw, item, achievement_font, left_w - 100),
                font=achievement_font, fill="#DCE6EF",
            )
            cy += ach_chip_h + ach_gap

    source_y = max(rail_top + 680, rail_bottom - 220)
    draw.text((left_x + 28, source_y), "记录来源", font=label_font, fill=MUTED)
    draw.text((left_x + 28, source_y + 22), "官方公开资料 + StalzoneHQ", font=small_font, fill=TEXT)
    draw.text(
        (left_x + 28, source_y + 46),
        f"查询时间 {view.get('now', '')} UTC+8", font=small_font, fill=MUTED,
    )

    # Right-hand content column.
    ry = content_y
    if bio_height:
        _draw_section_heading(
            draw, right_x, ry, "简介 / STATUS", section_font, "#FFD166"
        )
        panel_y = ry + 42
        draw.rounded_rectangle(
            (right_x, panel_y, right_x + right_w, panel_y + bio_height),
            radius=14, fill=(7, 13, 21, 155),
            outline=(82, 104, 126, 75), width=1,
        )
        line_y = panel_y + 18
        for line in bio_lines:
            _draw_pda_line(draw, right_x + 18, line_y, line, bio["font"], "#E2EBF5")
            line_y += int(bio.get("line_h") or 17)
        ry += 42 + bio_height + 28

    section_y = ry
    _draw_section_heading(
        draw, right_x, section_y, "战斗概览 / COMBAT", section_font, "#FFD166"
    )
    panel_y = section_y + 40
    draw.rounded_rectangle(
        (right_x, panel_y, right_x + right_w, panel_y + 128),
        radius=14, fill=(12, 19, 28, 195),
        outline=(78, 98, 118, 70), width=1,
    )
    if hq:
        draw.text((right_x + 22, panel_y + 13), "PvP SCORE", font=pvp_label_font, fill="#F0D49C")
        draw.text((right_x + 20, panel_y + 40), f"{hq.get('score', 0):,}", font=hero_score_font, fill="#FFD166")
        values = [
            ("击杀", f"{hq.get('kills', 0):,}"),
            ("助攻", f"{hq.get('assists', 0):,}"),
            ("PvP 死亡", f"{hq.get('deaths', 0):,}"),
            ("K/D", f"{hq.get('kd', 0):.2f}"),
        ]
        for index, (key, value) in enumerate(values):
            mx = right_x + 258 + index * 116
            draw.text((mx, panel_y + 22), key, font=combat_label_font, fill="#B4C6D6")
            draw.text((mx, panel_y + 48), value, font=combat_value_font, fill=TEXT)
    else:
        draw.text((right_x + 22, panel_y + 42), "暂无 PvP 统计", font=body_font, fill=MUTED)
    ry = panel_y + 128 + 24
    section_label_y = ry
    _draw_section_heading(
        draw, right_x, section_label_y, "官方统计 / STATISTICS", section_font, "#FFD166"
    )
    stats_y = section_label_y + 42
    col_w = right_w // 2
    for index, row in enumerate(stat_rows):
        label_text, sep, value = row.partition("：")
        if not sep:
            label_text, value = row, ""
        col = index // per_col
        row_index = index % per_col
        xx = right_x + col * col_w
        yy = stats_y + row_index * 36
        draw.text((xx, yy), _fit_text(draw, label_text, stat_label_font, col_w - 90), font=stat_label_font, fill="#B4C6D6")
        draw.text((xx + col_w - 20, yy), value, font=stat_value_font, fill=TEXT, anchor="ra")
    if stat_note:
        draw.text((right_x, stats_y + per_col * 36 + 4), stat_note, font=label_font, fill=MUTED)
    ry = stats_y + per_col * 36 + (24 if stat_note else 0) + 28

    footer_y = height - 100
    draw.line((right_x, footer_y, right_x + right_w, footer_y), fill=(90, 110, 130, 65), width=1)
    draw.text((right_x, footer_y + 15), "STALZONE · 玩家档案", font=small_font, fill=MUTED)
    draw.text(
        (right_x, footer_y + 37),
        "数据：STALZONE 官方公开 API｜PvP：StalzoneHQ 公式｜时间：UTC+8",
        font=small_font, fill=MUTED,
    )
    _draw_signature(
        draw,
        width,
        footer_y + 62,
        path,
        small_font,
        max_bottom=height,
        tip_x=60,
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_profile_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        image.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def render_diag_card(
    view: dict[str, Any] | None,
    *,
    font_path: str | None = None,
) -> Path | None:
    """Render a dense, readable diagnostics dashboard."""
    if (
        Image is None
        or ImageDraw is None
        or ImageFont is None
        or not isinstance(view, dict)
    ):
        return None
    path = find_cjk_font(font_path)
    if path is None:
        return None
    mono_path = find_mono_font(path)
    display_path = _find_display_font(font_path) or path
    try:
        title_font = ImageFont.truetype(str(display_path), 34)
        section_font = ImageFont.truetype(str(path), 20)
        body_font = ImageFont.truetype(str(path), 15)
        label_font = ImageFont.truetype(str(path), 13)
        small_font = ImageFont.truetype(str(path), 12)
        mono_font = ImageFont.truetype(str(mono_path or path), 12)
        metric_font = ImageFont.truetype(str(display_path), 31)
        chip_font = ImageFont.truetype(str(path), 13)
    except Exception:
        return None

    def text_width(value: Any, fnt: Any) -> int:
        return int(draw.textlength(str(value), font=fnt))

    width = 1200
    groups = [
        group for group in (view.get("groups") or [])
        if isinstance(group, dict)
    ]
    left = [g for g in groups if g.get("column") != 1]
    right = [g for g in groups if g.get("column") == 1]
    col_x = (PAD, 610)
    col_w = (540, 544)
    body_top = 322

    def group_height(group: dict[str, Any]) -> int:
        return 38 + len(group.get("rows") or []) * 29 + 12

    left_groups_h = sum(group_height(g) for g in left)
    right_h = sum(group_height(g) for g in right)
    summary_h = 160
    left_h = left_groups_h + summary_h + 12
    body_h = max(left_h, right_h)
    footer_h = 102
    height = max(1040, body_top + body_h + footer_h)
    canvas = _card_canvas(width, height, alpha=234)
    if canvas is None:
        return None
    draw = ImageDraw.Draw(canvas)

    accent = "#5AD1FF"
    state_key = str(view.get("status_key") or "ok")
    state_color = {
        "ok": "#69F0B0",
        "warn": "#FFD166",
        "bad": "#FF7A7A",
    }.get(state_key, "#A9B8C8")
    draw.text((PAD, 34), "STALZONE · 运行状态", font=title_font, fill=TEXT)
    status_text = str(view.get("status") or "未知")
    chip_w = text_width(status_text, chip_font) + 38
    chip_x = width - PAD - chip_w
    draw.rounded_rectangle(
        (chip_x, 34, chip_x + chip_w, 70), radius=18,
        fill=(16, 24, 28, 230), outline=_rgba_value(state_color, 160), width=1,
    )
    draw.ellipse((chip_x + 13, 46, chip_x + 21, 54), fill=state_color)
    draw.text((chip_x + 27, 41), status_text, font=chip_font, fill=state_color)
    draw.text(
        (PAD, 82),
        f"插件 {view.get('version', '?')}  ·  Python {view.get('python', '?')}  ·  {view.get('system', '?')}",
        font=body_font, fill="#C7D5E4",
    )
    draw.text(
        (width - PAD, 82),
        f"{view.get('region', '?')} · {view.get('env', '?')} · {view.get('now', '?')} UTC+8",
        font=small_font, fill=MUTED, anchor="ra",
    )
    draw.line((PAD, 112, width - PAD, 112), fill=(90, 110, 130, 80), width=1)

    # Health strip
    health_items = list(view.get("health") or [])
    if health_items:
        gap = 8
        cell_w = (width - 2 * PAD - gap * (len(health_items) - 1)) // len(health_items)
        for index, (label, state, detail) in enumerate(health_items):
            hx = PAD + index * (cell_w + gap)
            color = {"ok": "#69F0B0", "warn": "#FFD166", "bad": "#FF7A7A"}.get(state, "#A9B8C8")
            text = _fit_text(draw, f"{label} {detail}", small_font, cell_w - 32)
            draw.rounded_rectangle(
                (hx, 128, hx + cell_w, 156), radius=14,
                fill=(15, 24, 33, 220), outline=_rgba_value(color, 90), width=1,
            )
            draw.ellipse((hx + 10, 138, hx + 16, 144), fill=color)
            draw.text((hx + 23, 133), text, font=small_font, fill=color)

    # Top metrics
    metrics = [m for m in (view.get("metrics") or []) if isinstance(m, dict)][:4]
    tile_gap = 12
    tile_w = (width - 2 * PAD - tile_gap * max(0, len(metrics) - 1)) // max(1, len(metrics))
    for index, metric in enumerate(metrics):
        x = PAD + index * (tile_w + tile_gap)
        y = 176
        draw.rounded_rectangle(
            (x, y, x + tile_w, y + 94), radius=12,
            fill=(11, 20, 30, 220), outline=(70, 96, 118, 75), width=1,
        )
        draw.text((x + 16, y + 12), str(metric.get("label") or ""), font=label_font, fill=MUTED)
        draw.text((x + 15, y + 38), str(metric.get("value") or "—"), font=metric_font, fill=accent)
        unit = str(metric.get("unit") or "")
        if unit:
            draw.text((x + 17, y + 76), unit, font=small_font, fill="#7E93A8")

    def draw_group(group: dict[str, Any], x: int, y: int, w: int) -> int:
        title = str(group.get("title") or "")
        subtitle = str(group.get("subtitle") or "")
        _draw_section_heading(draw, x, y, title, section_font, accent)
        if subtitle:
            draw.text(
                (x + w, y + 6),
                subtitle, font=mono_font, fill="#56758B", anchor="ra",
            )
        draw.line((x, y + 34, x + w, y + 34), fill=(80, 105, 125, 70), width=1)
        yy = y + 44
        for key, value in group.get("rows") or []:
            draw.text((x, yy), str(key), font=label_font, fill=MUTED)
            value_text = _fit_text(draw, str(value), small_font, w - 150)
            draw.text((x + w, yy), value_text, font=small_font, fill=TEXT, anchor="ra")
            yy += 29
        return y + group_height(group)

    for index, group in enumerate(left):
        y = body_top + sum(group_height(g) for g in left[:index])
        draw_group(group, col_x[0], y, col_w[0])
    for index, group in enumerate(right):
        y = body_top + sum(group_height(g) for g in right[:index])
        draw_group(group, col_x[1], y, col_w[1])

    # Conclusion panel fills the lower-left rail and summarizes the raw data.
    summary_y = body_top + left_groups_h + 12
    panel_h = min(summary_h, max(120, body_top + body_h - summary_y - 8))
    draw.rounded_rectangle(
        (PAD, summary_y, PAD + col_w[0], summary_y + panel_h),
        radius=12, fill=(10, 20, 29, 220),
        outline=(75, 105, 125, 85), width=1,
    )
    draw.text((PAD + 16, summary_y + 12), "诊断结论 / SUMMARY", font=label_font, fill=accent)
    status_text = str(view.get("status") or "未知")
    status_w = text_width(status_text, small_font) + 30
    status_x = PAD + col_w[0] - 16 - status_w
    draw.rounded_rectangle(
        (status_x, summary_y + 8, status_x + status_w, summary_y + 32),
        radius=12, fill=(15, 24, 28, 230),
        outline=_rgba_value(state_color, 110), width=1,
    )
    draw.ellipse((status_x + 10, summary_y + 17, status_x + 16, summary_y + 23), fill=state_color)
    draw.text((status_x + 22, summary_y + 12), status_text, font=small_font, fill=state_color)
    sy = summary_y + 46
    for line in (view.get("summary_lines") or [])[:4]:
        draw.text(
            (PAD + 16, sy),
            _fit_text(draw, str(line), small_font, col_w[0] - 32),
            font=small_font, fill="#B8C9D8",
        )
        sy += 20
    footer_y = height - 82
    draw.line((PAD, footer_y, width - PAD, footer_y), fill=(80, 105, 125, 65), width=1)
    note = str(view.get("footer_note") or "诊断不包含凭证或玩家数据")
    note_lines = _wrap(note, small_font, width - 2 * PAD - 430)[:2]
    for line in note_lines:
        draw.text((PAD, footer_y + 12), line, font=small_font, fill=MUTED)
        footer_y += 18
    _draw_signature(
        draw, width, height - 64, path, small_font, max_bottom=height,
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_diag_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def render_pass_card(
    view: dict[str, Any] | None,
    *,
    font_path: str | None = None,
) -> Path | None:
    """Render the season-pass forecast with the prediction as the hero."""
    if (
        Image is None
        or ImageDraw is None
        or ImageFont is None
        or not isinstance(view, dict)
    ):
        return None
    path = find_cjk_font(font_path)
    if path is None:
        return None
    display_path = _find_display_font(font_path) or path
    mono_path = find_mono_font(path)
    try:
        title_font = ImageFont.truetype(str(display_path), 34)
        section_font = ImageFont.truetype(str(path), 21)
        body_font = ImageFont.truetype(str(path), 16)
        label_font = ImageFont.truetype(str(path), 13)
        small_font = ImageFont.truetype(str(path), 12)
        hero_label = ImageFont.truetype(str(path), 15)
        hero_heading = ImageFont.truetype(str(path), 18)
        note_font = ImageFont.truetype(str(path), 14)
        hero_from = ImageFont.truetype(str(path), 36)
        hero_to = ImageFont.truetype(str(display_path), 48)
        hero_secondary = ImageFont.truetype(str(display_path), 30)
        secondary_font = ImageFont.truetype(str(path), 24)
        chip_font = ImageFont.truetype(str(path), 13)
        mono_font = ImageFont.truetype(str(mono_path or path), 12)
    except Exception:
        return None

    def width_of(value: Any, fnt: Any) -> int:
        return int(draw.textlength(str(value), font=fnt))

    W, PAD = 1200, 46
    has_overload = bool(view.get("has_overload"))
    level = int(view.get("level") or 0)
    final = int(view.get("final_level") or level)
    final_without = int(view.get("final_without") or level)
    final_with = int(view.get("final_with") or final_without)
    gain = int(view.get("gain") or 0)
    gain_with = int(view.get("gain_with") or 0)
    gain_without = int(view.get("gain_without") or 0)

    left_x, left_w = PAD, 540
    right_x, right_w = 610, W - 610 - PAD
    hero_y = 122
    hero_h = 240 if has_overload else 160
    sections_y = hero_y + hero_h + 78
    groups = [
        ("每日任务", "DAILY", list(view.get("daily_rows") or [])),
        ("每周任务", "WEEKLY", list(view.get("weekly_rows") or [])),
        ("赛季汇总", "SEASON", list(view.get("season_rows") or [])),
    ]
    left_groups = groups[:2]
    right_groups = groups[2:]

    def group_h(rows: list[tuple[Any, Any]]) -> int:
        return 38 + len(rows) * 29 + 12

    left_end = sections_y + sum(group_h(rows) for _, _, rows in left_groups)
    right_end = sections_y + sum(group_h(rows) for _, _, rows in right_groups)
    height = max(820, max(left_end, right_end) + 92)
    canvas = _card_canvas(W, height, alpha=234)
    if canvas is None:
        return None
    draw = ImageDraw.Draw(canvas)

    green = "#69F0B0"
    cyan = "#7FC4FF"
    gain_color = green if gain > 0 else ("#FF7A7A" if gain < 0 else MUTED)
    draw.text((PAD, 32), "STALZONE · 通行证预测", font=title_font, fill=TEXT)
    draw.text(
        (W - PAD, 36),
        "SEASON PASS / FORECAST",
        font=mono_font, fill=(115, 150, 168), anchor="ra",
    )
    input_chips = list(view.get("input_chips") or [])
    daily_text = str(input_chips[1][1]) if len(input_chips) > 1 else "—"
    remaining_text = next(
        (str(value) for key, value in input_chips if key == "剩余天数"), "—"
    )
    weekly_text = next(
        (str(value) for key, value in input_chips if key == "每周计划"), "—"
    )
    draw.text(
        (PAD, 80),
        f"当前 Lv {level}  ·  每日 {daily_text}  ·  剩余 {remaining_text}  ·  每周 {weekly_text}",
        font=body_font, fill="#C7D5E4",
    )
    draw.line((PAD, 110, W - PAD, 110), fill=(80, 120, 115, 80), width=1)

    draw.rounded_rectangle(
        (PAD, hero_y, W - PAD, hero_y + hero_h), radius=18,
        fill=(8, 18, 22, 230), outline=(70, 150, 120, 100), width=1,
    )
    draw.rounded_rectangle(
        (PAD + 1, hero_y + 22, PAD + 5, hero_y + hero_h - 22),
        radius=2, fill=green,
    )
    draw.text((PAD + 24, hero_y + 14), "预测结果 / FORECAST", font=hero_heading, fill=green)
    def draw_levels(
        base_y: int,
        current_size: int,
        final_size: int,
        final_value: int,
        final_color: str,
        left_label: str,
        final_label: str = "",
        label_color: str = MUTED,
    ) -> int:
        current_font = ImageFont.truetype(str(path), current_size)
        final_font = ImageFont.truetype(str(display_path), final_size)
        start_x = PAD + 58
        x = start_x
        draw.text((x, base_y), f"Lv {level}", font=current_font, fill=MUTED, anchor="ls")
        x += width_of(f"Lv {level}", current_font) + 18
        draw.text((x, base_y), "→", font=current_font, fill=MUTED, anchor="ls")
        x += width_of("→", current_font) + 18
        draw.text((x, base_y), f"Lv {final_value}", font=final_font, fill=final_color, anchor="ls")
        draw.text((start_x, base_y - 46), left_label, font=label_font, fill=label_color, anchor="ls")
        if final_label:
            draw.text((x, base_y - 46), final_label, font=label_font, fill=label_color, anchor="ls")
        return x + width_of(f"Lv {final_value}", final_font)

    if has_overload:
        end_x = draw_levels(
            hero_y + 120, 34, 40, final_with, green, "使用超载", label_color=green
        )
        draw.text(
            (end_x + 8, hero_y + 122), f"+{gain_with} 级",
            font=small_font, fill="#A7DCC4", anchor="ls",
        )
        end_x = draw_levels(
            hero_y + 195, 34, 40, final_without, cyan, "不使用超载", label_color=MUTED
        )
        draw.text(
            (end_x + 8, hero_y + 197), f"+{gain_without} 级",
            font=small_font, fill="#A6D3EE", anchor="ls",
        )
    else:
        base_y = hero_y + 110
        end_x = draw_levels(
            base_y, 34, 40, final, gain_color, "当前", "预测等级", gain_color
        )
        delta_text = f"+{gain} 级" if gain > 0 else "等级不变"
        draw.text(
            (end_x + 8, base_y + 2), delta_text,
            font=small_font, fill="#A7DCC4" if gain > 0 else "#9AA8B4", anchor="ls",
        )

    # Methodology note: a centered panel in the free right side of the hero.
    note = str(view.get("note") or "")
    note_left = 688
    note_right = W - PAD - 22
    note_top = hero_y + 34
    note_bottom = hero_y + hero_h - 24
    draw.rounded_rectangle(
        (note_left, note_top, note_right, note_bottom), radius=12,
        fill=(9, 20, 25, 185), outline=(70, 120, 115, 75), width=1,
    )
    note_inner_w = note_right - note_left - 32
    note_lines = _wrap(note, note_font, note_inner_w)[:3]
    block_h = 22 + len(note_lines) * 20
    note_y = note_top + max(12, (note_bottom - note_top - block_h) // 2)
    note_center = (note_left + note_right) // 2
    draw.text((note_center, note_y), "预测说明 / NOTE", font=hero_label, fill=cyan, anchor="ma")
    note_y += 24
    for line in note_lines:
        draw.text((note_center, note_y), line, font=note_font, fill="#AFC3D1", anchor="ma")
        note_y += 20

    chip_y = hero_y + hero_h + 20
    cx = PAD
    for key, value in input_chips:
        text = f"{key} {value}"
        cw = width_of(text, chip_font) + 28
        draw.rounded_rectangle(
            (cx, chip_y, cx + cw, chip_y + 32), radius=16,
            fill=(14, 25, 32, 225), outline=(74, 110, 125, 90), width=1,
        )
        draw.text((cx + 14, chip_y + 8), text, font=chip_font, fill="#B9CDD9")
        cx += cw + 8

    def draw_group(title: str, subtitle: str, rows: list[tuple[Any, Any]], x: int, y: int, w: int) -> None:
        _draw_section_heading(draw, x, y, title, section_font, green)
        draw.text((x + w, y + 6), subtitle, font=mono_font, fill=(80, 120, 130), anchor="ra")
        draw.line((x, y + 34, x + w, y + 34), fill=(70, 110, 105, 75), width=1)
        yy = y + 44
        for key, value in rows:
            draw.text((x, yy), str(key), font=label_font, fill=MUTED)
            draw.text(
                (x + w, yy), _fit_text(draw, str(value), small_font, w - 150),
                font=small_font, fill=TEXT, anchor="ra",
            )
            yy += 29

    y = sections_y
    for title, subtitle, rows in left_groups:
        draw_group(title, subtitle, rows, left_x, y, left_w)
        y += group_h(rows)
    y = sections_y
    for title, subtitle, rows in right_groups:
        draw_group(title, subtitle, rows, right_x, y, right_w)
        y += group_h(rows)

    footer_y = height - 74
    draw.line((PAD, footer_y, W - PAD, footer_y), fill=(75, 110, 105, 65), width=1)
    draw.text(
        (PAD, footer_y + 12), str(view.get("footer") or ""),
        font=small_font, fill=MUTED,
    )
    _draw_signature(
        draw, W, height - 58, path, small_font, max_bottom=height, tip_x=PAD
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_pass_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def _rgba_value(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = str(color or "").lstrip("#")
    if len(value) == 8:
        try:
            red, green, blue, existing = (
                int(value[index : index + 2], 16) for index in (0, 2, 4, 6)
            )
            return (red, green, blue, min(alpha, existing))
        except ValueError:
            pass
    if len(value) != 6:
        return (231, 237, 245, alpha)
    try:
        red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return (231, 237, 245, alpha)
    return (red, green, blue, alpha)


def render_candidate_card(
    view: dict[str, Any] | None,
    *,
    font_path: str | None = None,
    width: int = 1200,
) -> Path | None:
    """Render item/clan candidates as a two-column grid of framed cards."""
    if (
        Image is None
        or ImageDraw is None
        or ImageFont is None
        or not isinstance(view, dict)
    ):
        return None
    entries = [entry for entry in (view.get("entries") or []) if isinstance(entry, dict)]
    if not entries:
        return None

    title_path = _find_display_font(font_path)
    body_path = find_cjk_font(font_path) or title_path
    if title_path is None or body_path is None:
        return None

    pad = 46
    column_gap = 18
    card_h = 132
    row_gap = 16
    header_h = 160
    footer_h = 90
    rows = (len(entries) + 1) // 2
    height = header_h + rows * card_h + max(0, rows - 1) * row_gap + footer_h
    canvas = _card_canvas(width, height, alpha=228)
    if canvas is None:
        return None
    draw = ImageDraw.Draw(canvas)

    try:
        title_font = ImageFont.truetype(str(title_path), 36)
        subtitle_font = ImageFont.truetype(str(body_path), 19)
        hint_font = ImageFont.truetype(str(body_path), 17)
        chip_font = ImageFont.truetype(str(body_path), 16)
        index_font = ImageFont.truetype(str(title_path), 54)
        index_font_small = ImageFont.truetype(str(title_path), 44)
        name_font = ImageFont.truetype(str(title_path), 26)
        detail_font = ImageFont.truetype(str(body_path), 16)
        meta_font = ImageFont.truetype(str(body_path), 14)
        footer_font = ImageFont.truetype(str(body_path), 15)
        placeholder_font = ImageFont.truetype(str(body_path), 15)
    except Exception:
        return None

    accent = ACCENT
    draw.rounded_rectangle((pad, 40, pad + 7, 84), radius=3, fill=accent)
    draw.text(
        (pad + 24, 32),
        str(view.get("title") or "STALZONE · 候选"),
        font=title_font,
        fill=TEXT,
    )
    count_text = f"{len(entries)} 个候选"
    chip_width = int(draw.textlength(count_text, font=chip_font)) + 28
    chip_x = width - pad - chip_width
    draw.rounded_rectangle(
        (chip_x, 38, chip_x + chip_width, 72),
        radius=17,
        fill=(28, 42, 58, 210),
        outline=(110, 135, 160, 90),
        width=1,
    )
    draw.text(
        (chip_x + 14, 46),
        count_text,
        font=chip_font,
        fill="#DCE8F5",
    )
    draw.text(
        (pad, 92),
        str(view.get("subtitle") or ""),
        font=subtitle_font,
        fill=MUTED,
    )
    draw.text(
        (pad, 122),
        str(view.get("hint") or ""),
        font=hint_font,
        fill=accent,
    )
    draw.line((pad, 150, width - pad, 150), fill=BORDER, width=1)

    frame_w = (width - 2 * pad - column_gap) // 2
    icon_size = 92
    icon_pad = 16
    text_x_offset = 102

    for position, entry in enumerate(entries):
        row, column = divmod(position, 2)
        x = pad + column * (frame_w + column_gap)
        y = header_h + row * (card_h + row_gap)
        color = str(entry.get("color") or TEXT)
        border = _rgba_value(color, 120)
        draw.rounded_rectangle(
            (x, y, x + frame_w, y + card_h),
            radius=15,
            fill=(13, 21, 31, 238),
            outline=border,
            width=2,
        )
        draw.line(
            (
                x + 90,
                y + 18,
                x + 90,
                y + card_h - 18,
            ),
            fill=(80, 100, 120, 80),
            width=1,
        )
        index = int(entry.get("index") or position + 1)
        index_font_value = index_font if index < 10 else index_font_small
        draw.text(
            (x + 45, y + card_h / 2 - 2),
            str(index),
            font=index_font_value,
            fill=color,
            anchor="mm",
        )

        icon_left = x + frame_w - icon_pad - icon_size
        icon_top = y + (card_h - icon_size) // 2
        _draw_candidate_icon_frame(canvas, draw, icon_left, icon_top, icon_size)

        icon_source = str(entry.get("icon_path") or "").strip()
        if not icon_source and entry.get("faction"):
            faction_path = faction_icon_path(str(entry.get("faction")))
            icon_source = str(faction_path) if faction_path else ""
        icon_rendered = False
        if icon_source:
            inner = icon_size - 16
            icon_rendered = _draw_candidate_icon(
                canvas,
                icon_source,
                icon_left + (icon_size - inner) // 2,
                icon_top + (icon_size - inner) // 2,
                inner,
            )
        if not icon_rendered:
            draw.text(
                (icon_left + icon_size / 2, icon_top + icon_size / 2),
                "暂无图标",
                font=placeholder_font,
                fill=MUTED,
                anchor="mm",
            )

        text_width = icon_left - (x + text_x_offset) - 12
        title = str(entry.get("title") or "未命名")
        draw.text(
            (x + text_x_offset, y + 22),
            _fit_text(draw, title, name_font, text_width),
            font=name_font,
            fill=color,
        )
        subtitle = str(entry.get("subtitle") or "").strip()
        if subtitle:
            draw.text(
                (x + text_x_offset, y + 60),
                _fit_text(draw, subtitle, detail_font, text_width),
                font=detail_font,
                fill="#A9BCD0",
            )
        meta = str(entry.get("meta") or "").strip()
        if meta:
            draw.text(
                (x + text_x_offset, y + 88),
                _fit_text(draw, meta, meta_font, text_width),
                font=meta_font,
                fill=MUTED,
            )

    footer_y = height - 66
    draw.line((pad, footer_y - 18, width - pad, footer_y - 18), fill=BORDER, width=1)
    draw.text(
        (pad + 8, footer_y),
        _fit_text(
            draw,
            str(view.get("footer") or ""),
            footer_font,
            width - 2 * pad - 280,
        ),
        font=footer_font,
        fill=MUTED,
    )
    _draw_signature(
        draw,
        width,
        height - 58,
        body_path,
        footer_font,
        right_margin=58,
        max_bottom=height,
        tip_x=pad,
    )

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_candidates_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        canvas.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output


def render_auction_card(
    view: dict[str, Any],
    *,
    font_path: str | None = None,
    icon_path: str | Path | None = None,
) -> Path | None:
    """Draw the compact, colored auction table described by the user.

    The generic text renderer colors a whole line; this renderer colors only
    item names, keeps numeric columns aligned and puts recent trades below a
    divider.
    """
    if Image is None or ImageDraw is None or ImageFont is None:
        return None
    path = find_cjk_font(font_path)
    if path is None:
        return None
    try:
        title_font = ImageFont.truetype(str(path), 34)
        subtitle_font = ImageFont.truetype(str(path), 19)
        head_font = ImageFont.truetype(str(path), 19)
        body_font = ImageFont.truetype(str(path), 19)
        small_font = ImageFont.truetype(str(path), 16)
        group_font = ImageFont.truetype(str(path), 21)
    except Exception:
        return None

    active = view.get("active") or []
    groups = view.get("recent_groups") or []
    if view.get("empty"):
        width = 760
        try:
            empty_font = ImageFont.truetype(str(path), 28)
        except Exception:
            empty_font = body_font
        y = 190
        if view.get("before"):
            y += 36
        note = str(view.get("empty_note") or "")
        note_lines = _wrap(note, small_font, width - 2 * PAD)[:3] if note else []
        content_bottom = (
            y + 60 + len(note_lines) * 22 if note_lines else y + 42
        )
        height = max(300, content_bottom + 6 + SIGNATURE_HEIGHT + 18)
        image = _card_canvas(width, height, alpha=228)
        if image is None:
            return None
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((PAD, PAD + 4, PAD + 7, PAD + 44), radius=3, fill=ACCENT)
        draw.text((PAD + 26, PAD), "STALZONE · 拍卖行", font=title_font, fill=TEXT)
        _paste_corner_icon(image, icon_path, width, 124)
        draw.text(
            (PAD, PAD + 48),
            _fit_text(draw, str(view.get("title", "")), subtitle_font, width - PAD - 174),
            font=subtitle_font,
            fill=MUTED,
        )
        draw.text(
            (PAD, PAD + 74),
            f"{view.get('region', '')}｜查询时间：{view.get('now', '')} UTC+8",
            font=subtitle_font,
            fill=MUTED,
        )
        draw.line((PAD, 165, width - PAD, 165), fill=BORDER, width=1)
        y = 190
        if view.get("before"):
            draw.text(
                (PAD, y),
                f"截至 {view['before']}",
                font=small_font,
                fill=MUTED,
            )
            y += 36
        if view.get("unsupported"):
            notice = "该物品暂不支持拍卖查询"
            draw.text(
                ((width - draw.textlength(notice, font=empty_font)) / 2, y),
                notice, font=empty_font, fill=TEXT,
            )
        else:
            prefix = "未查到关于「"
            suffix = "」的成交记录"
            name = str(view.get("empty_name") or view.get("short") or "物品")
            prefix_w = draw.textlength(prefix, font=empty_font)
            suffix_w = draw.textlength(suffix, font=empty_font)
            name = _fit_text(
                draw,
                name,
                empty_font,
                width - 2 * PAD - prefix_w - suffix_w - 16,
            )
            total_w = prefix_w + draw.textlength(name, font=empty_font) + suffix_w
            x = max(PAD, int((width - total_w) / 2))
            draw.text((x, y), prefix, font=empty_font, fill=TEXT)
            x += prefix_w
            draw.text(
                (x, y),
                name,
                font=empty_font,
                fill=str(view.get("empty_color") or TEXT),
            )
            x += draw.textlength(name, font=empty_font)
            draw.text((x, y), suffix, font=empty_font, fill=TEXT)
        note_y = y + 60
        for line in note_lines:
            draw.text((PAD, note_y), line, font=small_font, fill=MUTED)
            note_y += 22
        _draw_signature(
            draw, width, content_bottom + 6, path, small_font, max_bottom=height
        )
        out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
        out_dir.mkdir(parents=True, exist_ok=True)
        _remove_old_files(out_dir)
        output = out_dir / f"sz_auction_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
        try:
            image.convert("RGB").save(output, "PNG", compress_level=1)
        except OSError:
            return None
        return output

    left = PAD + 10
    gap = 26

    def _text_width(value: Any, font: Any) -> float:
        try:
            return float(font.getlength(str(value)))
        except Exception:
            return float(len(str(value)) * 19)

    active_rows = [
        row
        for row in active
        if isinstance(row, dict)
        and not row.get("quality_header")
        and not row.get("ellipsis")
    ]
    recent_rows = [
        row
        for group in groups
        if isinstance(group, dict)
        for row in (group.get("rows") or [])
        if isinstance(row, dict)
    ]

    # The name column only needs to be as wide as this result's longest name.
    # That keeps short names close to the prices instead of stranded at the
    # left edge of a fixed 960px table.
    non_artifact = bool(view.get("non_artifact"))
    show_unit = bool(view.get("quantity_mode"))
    badge_extra = (
        58.0
        if non_artifact
        and any(row.get("lowest") for row in active_rows + recent_rows)
        else 0.0
    )
    # Active rows start at `left` with 12px of right padding, while recent
    # rows are indented 16px under their quality group and use the same
    # endpoint. Budget each table separately; otherwise a five-character name
    # loses a character in the recent list simply because of that indent.
    active_name_w = max(
        (_text_width(row.get("name", ""), body_font) for row in active_rows),
        default=38.0,
    )
    recent_name_w = max(
        (
            _text_width(row.get("name", ""), body_font)
            for group in groups
            if isinstance(group, dict)
            for row in (group.get("rows") or [])
            if isinstance(row, dict)
        ),
        default=38.0,
    )
    name_w = _auction_name_column_width(
        active_name_w,
        recent_name_w,
        badge_extra,
        380.0 if non_artifact else 360.0,
    )

    def _row_price(row: dict[str, Any]) -> str:
        price = str(row.get("price", ""))
        amount = row.get("amount")
        if not non_artifact and isinstance(amount, int) and amount > 1:
            price += f" ×{amount}"
        return price

    time_w = max(
        (_text_width(row.get("time", ""), body_font) for row in recent_rows),
        default=0.0,
    )
    history_only = bool(view.get("history_only"))

    if non_artifact:
        start_w = max(
            56.0,
            _text_width("起拍", head_font),
            _text_width("—", body_font),
        ) + 18
        buyout_w = max(
            56.0,
            _text_width("买断", head_font),
            max((_text_width(row.get("buyout", ""), body_font) for row in active_rows), default=0.0),
        ) + 18
        unit_w = max(
            56.0,
            _text_width("单价", head_font),
            max(
                (_text_width(row.get("unit_price", ""), body_font) for row in active_rows + recent_rows),
                default=0.0,
            ),
        ) + 18
        remaining_w = max(
            56.0,
            _text_width("剩余时间", head_font),
            max((_text_width(row.get("remaining", ""), body_font) for row in active_rows), default=0.0),
        ) + 10
        price_w = max(
            56.0,
            _text_width("成交价", head_font),
            max((_text_width(_row_price(row), body_font) for row in recent_rows), default=0.0),
        ) + 18

        def _layout_active(
            name_width: float, include_unit: bool
        ) -> tuple[int, int, int, int, int, float]:
            nr = int(left + name_width)
            sr = int(nr + gap + start_w)
            br = int(sr + gap + buyout_w)
            if include_unit:
                ur = int(br + gap + unit_w)
                rx = int(ur + gap)
            else:
                ur = br
                rx = int(br + gap)
            end = max(rx + remaining_w, (ur if include_unit else br) + gap + time_w)
            return nr, sr, br, ur, rx, end

        def _layout_history(name_width: float) -> tuple[int, int, int, int, float]:
            nr = int(left + name_width)
            pr = int(nr + gap + price_w)
            ur = int(pr + gap + unit_w)
            tx = int(ur + gap)
            return nr, pr, ur, tx, tx + time_w

        name_right, start_right, buyout_right, unit_right, remaining_x, active_end = _layout_active(name_w, show_unit)
        _, price_right, history_unit_right, time_x, history_end = _layout_history(name_w)
        desired = max(active_end if not history_only else 0.0, history_end) + PAD + 10
        if desired > WIDTH:
            name_w = max(160.0, name_w - (desired - WIDTH))
            name_right, start_right, buyout_right, unit_right, remaining_x, active_end = _layout_active(name_w, show_unit)
            _, price_right, history_unit_right, time_x, history_end = _layout_history(name_w)
            desired = max(active_end if not history_only else 0.0, history_end) + PAD + 10
        width = int(max(700, min(WIDTH, desired)))
    elif history_only:
        price_w = max(
            56.0,
            max((_text_width(_row_price(row), body_font) for row in recent_rows), default=0.0),
        ) + 18

        def _layout_history(name_width: float) -> tuple[int, int, int, float]:
            nr = int(left + name_width)
            pr = int(nr + gap + price_w)
            tx = int(pr + gap)
            return nr, pr, tx, tx + time_w

        name_right, price_right, time_x, content_end = _layout_history(name_w)
        desired = content_end + PAD + 10
        if desired > WIDTH:
            name_w = max(160.0, name_w - (desired - WIDTH))
            name_right, price_right, time_x, content_end = _layout_history(name_w)
            desired = content_end + PAD + 10
        width = int(max(620, min(WIDTH, desired)))
        start_right = buyout_right = unit_right = remaining_x = price_right
        history_unit_right = price_right
    else:
        start_w = max(
            56.0,
            _text_width("起拍", head_font),
            max(
                (_text_width(row.get("start", ""), body_font) for row in active_rows),
                default=0.0,
            ),
        ) + 18
        buyout_w = max(
            56.0,
            _text_width("买断", head_font),
            max((_text_width(row.get("buyout", ""), body_font) for row in active_rows), default=0.0),
        ) + 18
        remaining_w = max(
            56.0,
            _text_width("剩余时间", head_font),
            max((_text_width(row.get("remaining", ""), body_font) for row in active_rows), default=0.0),
        ) + 10

        def _layout(name_width: float) -> tuple[int, int, int, int, float]:
            nr = int(left + name_width)
            sr = int(nr + gap + start_w)
            br = int(sr + gap + buyout_w)
            rx = int(br + gap)
            end = max(rx + remaining_w, br + gap + time_w)
            return nr, sr, br, rx, end

        name_right, start_right, buyout_right, remaining_x, content_end = _layout(name_w)
        if non_artifact:
            remaining_x = buyout_right + gap
        desired = content_end + PAD + 10
        if desired > WIDTH:
            name_w = max(160.0, name_w - (desired - WIDTH))
            name_right, start_right, buyout_right, remaining_x, content_end = _layout(name_w)
            if non_artifact:
                remaining_x = buyout_right + gap
            desired = content_end + PAD + 10
        width = int(max(700, min(WIDTH, desired)))
        price_right = buyout_right
        time_x = buyout_right + gap
        unit_right = history_unit_right = buyout_right
    line_h = 34
    group_h = 34
    header_h = 170
    groups_h = sum(
        group_h + max(1, len(group.get("rows") or [])) * 32
        for group in groups
        if isinstance(group, dict)
    )
    if not groups:
        # The renderer prints a 32px "暂无成交记录" placeholder.
        groups_h = 32
    history_header_h = 28 if non_artifact else 0
    # Keep the footer tight: the old 84px tail left a visible empty strip
    # below the signature.
    tail_h = SIGNATURE_HEIGHT + (92 if history_only else 71)
    if history_only:
        height = header_h + 32 + history_header_h + groups_h + tail_h
    else:
        note_lines = [
            line
            for line in str(view.get("active_note") or "").split("\n")
            if line
        ]
        active_h = 30 + sum(
            group_h if row.get("quality_header") else line_h
            for row in active
        )
        if note_lines:
            active_h += 24 * len(note_lines)
        recent_h = 32 + history_header_h + groups_h
        height = header_h + active_h + 35 + recent_h + tail_h
    max_height = (
        12000
        if view.get("quantity_mode")
        else (8000 if history_only else 6000)
    )
    height = max(460, min(height, max_height))

    image = _card_canvas(width, height, alpha=228)
    if image is None:
        return None
    draw = ImageDraw.Draw(image)
    try:
        badge_font = ImageFont.truetype(str(path), 14)
    except Exception:
        badge_font = small_font

    def _draw_lowest_badge(x: int, y: int, text: str) -> None:
        badge_w = int(draw.textlength(text, font=badge_font)) + 12
        badge_h = 18
        badge_y = y + 4
        draw.rounded_rectangle(
            (x, badge_y, x + badge_w, badge_y + badge_h),
            radius=4,
            fill="#0E2B21",
            outline="#54D6A1",
            width=1,
        )
        draw.text(
            (x + badge_w / 2, badge_y + badge_h / 2),
            text,
            font=badge_font,
            fill="#7FE3B0",
            anchor="mm",
        )

    def _draw_history_header(row_y: int) -> None:
        draw.text((left, row_y), "名称", font=head_font, fill="#7F93A8")
        for label, x in (("成交价", price_right), ("单价", history_unit_right)):
            draw.text(
                (x - draw.textlength(label, font=head_font), row_y),
                label,
                font=head_font,
                fill=MUTED,
            )
        draw.text((time_x, row_y), "时间", font=head_font, fill=MUTED)

    draw.rounded_rectangle((PAD, PAD + 4, PAD + 7, PAD + 44), radius=3, fill=ACCENT)
    draw.text((PAD + 26, PAD), "STALZONE · 拍卖行", font=title_font, fill=TEXT)
    _paste_corner_icon(image, icon_path, width, 124)
    subtitle_width = max(120, width - PAD - 30 - (138 if icon_path else 0))
    subtitle = _fit_text(draw, str(view.get("title", "")), subtitle_font, subtitle_width)
    draw.text((PAD, PAD + 48), subtitle, font=subtitle_font, fill=MUTED)
    draw.text(
        (PAD, PAD + 74),
        f"{view.get('region', '')}｜查询时间：{view.get('now', '')} UTC+8",
        font=subtitle_font,
        fill=MUTED,
    )
    y = header_h
    draw.line((PAD, y - 18, width - PAD, y - 18), fill=BORDER, width=1)
    if history_only:
        if view.get("recent_per_quality"):
            history_heading = (
                f"历史成交（每品质最多 {view.get('recent_limit', 3)} 条，"
                "按时间倒序）"
            )
        elif view.get("recent_grouped_quality"):
            history_heading = "历史成交（按品质分组，组内时间倒序）"
        else:
            history_heading = "历史成交（按时间倒序）"
        draw.text((left, y), history_heading, font=head_font, fill=ACCENT)
        y += 28
        note = str(view.get("history_note") or "")
        if note:
            draw.text((left, y), note, font=small_font, fill=MUTED)
        y += 26
        if non_artifact:
            _draw_history_header(y)
            y += history_header_h
    else:
        draw.text((left, y), "名称", font=head_font, fill="#7F93A8")
        active_headers = [("起拍", start_right), ("买断", buyout_right)]
        if show_unit:
            active_headers.append(("单价", unit_right))
        for label, x in active_headers:
            draw.text((x - draw.textlength(label, font=head_font), y), label, font=head_font, fill=MUTED)
        draw.text((remaining_x, y), "剩余时间", font=head_font, fill=MUTED)
        y += 30

        if active:
            for row in active:
                if row.get("quality_header"):
                    header = _fit_text(
                        draw,
                        str(row.get("name", "")),
                        group_font,
                        width - 2 * PAD,
                    )
                    draw.text(
                        (left, y),
                        header,
                        font=group_font,
                        fill=str(row.get("color") or ACCENT),
                    )
                    y += group_h
                    continue
                if row.get("ellipsis"):
                    draw.text(
                        (width / 2, y),
                        str(row.get("name", "")),
                        font=small_font,
                        fill=MUTED,
                        anchor="ma",
                    )
                    y += line_h
                    continue
                name = _fit_auction_name(
                    draw,
                    str(row.get("name", "")),
                    body_font,
                    name_right - left - 12,
                )
                color = str(row.get("color") or TEXT)
                draw.text((left, y), name, font=body_font, fill=color)
                values = [
                    (row.get("start", "—"), start_right),
                    (row.get("buyout", "—"), buyout_right),
                ]
                if show_unit:
                    values.append((row.get("unit_price", "—"), unit_right))
                for value, x in values:
                    text = str(value)
                    draw.text((x - draw.textlength(text, font=body_font), y), text, font=body_font, fill=TEXT)
                draw.text((remaining_x, y), str(row.get("remaining", "")), font=body_font, fill=MUTED)
                y += line_h
        else:
            draw.text((left, y), "当前无在售", font=body_font, fill=MUTED)
            y += line_h
        for note_line in note_lines:
            draw.text(
                (left, y),
                _fit_text(
                    draw,
                    note_line,
                    small_font,
                    width - 2 * PAD,
                ),
                font=small_font,
                fill=MUTED,
            )
            y += 24
        y += 18
        draw.line((PAD, y, width - PAD, y), fill=BORDER, width=1)
        y += 18
        if view.get("recent_per_quality"):
            recent_heading = (
                f"最近成交（每品质最多 {view.get('recent_limit', 3)} 条，"
                "按时间倒序）"
            )
        elif (
            view.get("recent_grouped_quality")
            and view.get("recent_total_limit") is None
        ):
            recent_heading = (
                f"最近成交（每品质最多 {view.get('recent_limit', 10)} 条，"
                "按时间倒序）"
            )
        elif view.get("recent_grouped_quality"):
            recent_heading = (
                f"最近成交（最多 {view['recent_total_limit']} 条，"
                "按品质分组，组内时间倒序）"
            )
        elif view.get("recent_total_limit") is not None:
            recent_heading = (
                f"最近成交（最多 {view['recent_total_limit']} 条，按时间倒序）"
            )
        else:
            recent_heading = (
                f"最近成交（每品质最多 {view.get('recent_limit', 3)} 条，按时间倒序）"
            )
        draw.text(
            (left, y),
            recent_heading,
            font=head_font,
            fill=ACCENT,
        )
        y += 32
        if non_artifact:
            _draw_history_header(y)
            y += history_header_h
    if groups:
        for group in groups:
            label = str(group.get("label") or "").split("（", 1)[0]
            color = str(group.get("color") or MUTED)
            if label:
                draw.text((left, y), label, font=group_font, fill=color)
                y += group_h
            else:
                y += 4
            for row in group.get("rows") or []:
                name = _fit_auction_name(
                    draw,
                    str(row.get("name", "")),
                    body_font,
                    max(60, int(name_w) - 28),
                )
                name_color = str(row.get("color") or color)
                draw.text((left + 16, y), name, font=body_font, fill=name_color)
                if row.get("lowest"):
                    _draw_lowest_badge(
                        left + 16 + int(draw.textlength(name, font=body_font)) + 6,
                        y,
                        str(
                            row.get("lowest_label")
                            or ("最低单价" if non_artifact else "最低价")
                        ),
                    )
                price = _row_price(row)
                draw.text(
                    (price_right - draw.textlength(price, font=body_font), y),
                    price,
                    font=body_font,
                    fill=TEXT,
                )
                if non_artifact:
                    unit = str(row.get("unit_price", "—"))
                    draw.text(
                        (history_unit_right - draw.textlength(unit, font=body_font), y),
                        unit,
                        font=body_font,
                        fill=TEXT,
                    )
                draw.text((time_x, y), str(row.get("time", "")), font=body_font, fill=MUTED)
                y += 32
    else:
        draw.text((left, y), "暂无成交记录", font=body_font, fill=MUTED)
        y += 32
    y += 8
    if not view.get("non_artifact"):
        if view.get("quality_filter") is None:
            draw.text(
                (left, y),
                "可按品质筛选：物品名 + 白/绿/蓝/粉/红/金",
                font=small_font,
                fill=MUTED,
            )
        else:
            draw.text(
                (left, y),
                f"仅看品质：{(view.get('quality_filter_label') or '未知').split('（', 1)[0]}",
                font=small_font,
                fill=MUTED,
            )
    y += 24
    draw.text(
        (left, y),
        str(
            view.get("data_note")
            or "数据来自官方 API｜价格随时变化｜时间为 UTC+8（北京时间）"
        ),
        font=small_font,
        fill=MUTED,
    )
    _draw_signature(draw, width, y + 26, path, small_font, max_bottom=height)

    out_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone"
    out_dir.mkdir(parents=True, exist_ok=True)
    _remove_old_files(out_dir)
    output = out_dir / f"sz_auction_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
    try:
        image.convert("RGB").save(output, "PNG", compress_level=1)
    except OSError:
        return None
    return output
