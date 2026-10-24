#!/usr/bin/env python3
"""Regenerate the Windows visual-regression signatures."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import image_renderer as renderer  # noqa: E402
from visual_cases import CASES  # noqa: E402

OUT = ROOT / "tests" / "snapshots" / "windows"
SIGNATURE_WIDTH = 360


def signature(path: Path) -> Image.Image:
    with Image.open(path) as image:
        source = image.convert("RGB")
        height = max(1, round(source.height * SIGNATURE_WIDTH / source.width))
        return source.resize((SIGNATURE_WIDTH, height), Image.LANCZOS)


def main() -> int:
    font = renderer.find_cjk_font()
    if font is None:
        print("No CJK font found; cannot generate visual signatures.")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    renderer.set_creator_watermark_hidden(False)
    manifest = {
        "font": Path(font).name,
        "platform": platform.system(),
        "signature_width": SIGNATURE_WIDTH,
    }
    written: list[str] = []
    for name, render in CASES.items():
        output = render()
        if output is None:
            print(f"skip {name}: renderer unavailable")
            continue
        try:
            signature(output).save(OUT / f"{name}.png", "PNG", optimize=True)
            written.append(name)
        finally:
            output.unlink(missing_ok=True)
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(written)} signatures to {OUT}")
    print(", ".join(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
