"""STALZONE PDA text formatting helpers.

PDA descriptions use Minecraft-style section-sign colour codes:
  §0-§F   preset colours (see PDA_COLORS)
  §R      reset to white
  §#RRGGBB  custom colour (the # is part of the code)

The gradient editor used by the community simply inserts a custom-colour code
before every character, so parsing those codes is enough to render gradients.
"""

from __future__ import annotations

import re
from typing import Iterable

PDA_COLORS: dict[str, str] = {
    "0": "#000000",
    "1": "#0000AA",
    "2": "#00AA00",
    "3": "#00AAAA",
    "4": "#AA0000",
    "5": "#AA00AA",
    "6": "#FFAA00",
    "7": "#AAAAAA",
    "8": "#555555",
    "9": "#5555FF",
    "A": "#55FF55",
    "B": "#55FFFF",
    "C": "#FF5555",
    "D": "#FF55FF",
    "E": "#FFFF55",
    "F": "#FFFFFF",
}
DEFAULT_PDA_COLOR = PDA_COLORS["F"]
_HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")


def parse_pda_segments(
    text: str, default_color: str = DEFAULT_PDA_COLOR
) -> list[tuple[str, str]]:
    """Split formatted PDA text into ``(text, #RRGGBB)`` runs."""
    value = str(text or "")
    current = default_color if _HEX_RE.fullmatch(default_color) else DEFAULT_PDA_COLOR
    out: list[tuple[str, str]] = []
    buffer: list[str] = []
    index = 0

    def flush() -> None:
        if buffer:
            out.append(("".join(buffer), current))
            buffer.clear()

    while index < len(value):
        char = value[index]
        if char == "§" and index + 1 < len(value):
            code = value[index + 1]
            upper = code.upper()
            if upper == "R":
                flush()
                current = default_color
                index += 2
                continue
            if code == "#" and index + 8 <= len(value):
                candidate = value[index + 1 : index + 8]
                if _HEX_RE.fullmatch(candidate):
                    flush()
                    current = candidate.upper()
                    index += 8
                    continue
            if upper in PDA_COLORS:
                flush()
                current = PDA_COLORS[upper]
                index += 2
                continue
        buffer.append(char)
        index += 1
    flush()
    return out


def strip_pda_formatting(text: str) -> str:
    """Return plain text with all recognised PDA codes removed."""
    return "".join(run for run, _color in parse_pda_segments(text))


def pda_color_name(color: str) -> str:
    for code, value in PDA_COLORS.items():
        if value.upper() == str(color).upper():
            return f"§{code}"
    return str(color)


def pda_has_formatting(text: str) -> bool:
    return "§" in str(text or "")
