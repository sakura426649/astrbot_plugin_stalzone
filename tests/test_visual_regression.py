"""Windows visual signatures for the main rendered cards.

The signatures are deliberately small (360 px wide) so the test is quick and
tolerant of minor PNG encoder differences while still catching layout and
label regressions. Baselines are generated with tools/build_visual_baselines.py.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "tests"))

import image_renderer as renderer  # noqa: E402
from visual_cases import CASES  # noqa: E402

SNAPSHOT_DIR = PLUGIN_ROOT / "tests" / "snapshots" / "windows"
SIGNATURE_WIDTH = 360


@unittest.skipUnless(sys.platform == "win32", "Windows visual baseline")
@unittest.skipUnless(renderer.find_cjk_font(), "No CJK font installed")
class VisualRegressionTests(unittest.TestCase):
    def test_main_cards_match_windows_snapshots(self):
        manifest_path = SNAPSHOT_DIR / "manifest.json"
        if not manifest_path.is_file():
            self.skipTest("No visual baseline manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        current_font = Path(str(renderer.find_cjk_font())).name
        if current_font != manifest.get("font"):
            self.skipTest(
                f"Visual baseline uses {manifest.get('font')}, current font is {current_font}"
            )

        old_hidden = renderer.CREATOR_WATERMARK_HIDDEN
        try:
            renderer.set_creator_watermark_hidden(False)
            for name, render in CASES.items():
                with self.subTest(card=name):
                    baseline_path = SNAPSHOT_DIR / f"{name}.png"
                    if not baseline_path.is_file():
                        self.skipTest(f"Missing snapshot {baseline_path.name}")
                    output = render()
                    self.assertIsNotNone(output)
                    try:
                        with Image.open(output) as image:
                            source = image.convert("RGB")
                            height = max(
                                1,
                                round(
                                    source.height
                                    * SIGNATURE_WIDTH
                                    / source.width
                                ),
                            )
                            signature = source.resize(
                                (SIGNATURE_WIDTH, height), Image.LANCZOS
                            )
                        with Image.open(baseline_path) as image:
                            baseline = image.convert("RGB")
                        self.assertEqual(signature.size, baseline.size)
                        diff = ImageChops.difference(signature, baseline)
                        mean = sum(ImageStat.Stat(diff).mean) / 3
                        changed = sum(
                            1
                            for pixel in diff.getdata()
                            if max(pixel) > 24
                        ) / (diff.width * diff.height)
                        self.assertLessEqual(mean, 2.5, f"{name} mean diff {mean:.2f}")
                        self.assertLessEqual(
                            changed, 0.015, f"{name} changed {changed:.3%}"
                        )
                    finally:
                        output.unlink(missing_ok=True)
        finally:
            renderer.set_creator_watermark_hidden(old_hidden)
