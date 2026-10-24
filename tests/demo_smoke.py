"""Manual demo smoke test. Not part of the runtime plugin.

PowerShell / bash:
    set SZ_CID / SZ_SECRET (and optionally STALZONE_API_BASE)
    python tests/demo_smoke.py

The demo server's profile endpoint may return 404 for sample characters;
auction and emission are the useful smoke checks.
"""

from __future__ import annotations

import asyncio
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if "astrbot" not in sys.modules:
    _astrbot = types.ModuleType("astrbot")
    _astrbot_api = types.ModuleType("astrbot.api")
    _astrbot_api.logger = types.SimpleNamespace(
        debug=lambda *args, **kwargs: None,
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
        exception=lambda *args, **kwargs: None,
    )
    _astrbot.api = _astrbot_api
    sys.modules["astrbot"] = _astrbot
    sys.modules["astrbot.api"] = _astrbot_api

from api_client import DEMO_BASE_URL, StalzoneAPIClient  # noqa: E402
from formatters import format_auction, format_emission  # noqa: E402


async def main() -> None:
    client_id = os.getenv("SZ_CID", "").strip()
    client_secret = os.getenv("SZ_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit("请先设置 SZ_CID 和 SZ_SECRET 环境变量。")
    base_url = os.getenv("STALZONE_API_BASE", DEMO_BASE_URL)
    region = os.getenv("STALZONE_REGION", "eu")

    async with StalzoneAPIClient(
        client_id, client_secret, region=region, base_url=base_url
    ) as api:
        lots, history = await asyncio.gather(
            api.get_auction_lots("y1q9"),
            api.get_auction_history("y1q9"),
        )
        print(format_auction("y1q9", lots, history, api.region))
        print()
        print(format_emission(await api.get_emission(), api.region))


if __name__ == "__main__":
    asyncio.run(main())
