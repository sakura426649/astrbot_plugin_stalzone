"""Optional third-party enrichment: Lunar clan-war player stats.

Lunar exposes a public JSON endpoint used by its player profile page.  It is
NOT the official STALZONE API; the plugin labels it clearly and falls back
silently when Lunar does not have the player or is unavailable.
"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import httpx

LUNAR_BASE_URL = "https://lunar-zone.com"
LUNAR_TIMEOUT_SECONDS = 3.0


class LunarProfileClient:
    async def get_player_profile(self, region: str, name: str) -> dict[str, Any] | None:
        url = (
            f"{LUNAR_BASE_URL}/web-api/clans/player-profile.php"
            f"?region={quote(str(region).lower(), safe='')}&name={quote(name, safe='')}"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; astrbot-plugin-stalzone/1.0.10)",
            "Referer": f"{LUNAR_BASE_URL}/players/{quote(str(region).lower(), safe='')}/{quote(name, safe='')}",
            "Accept": "application/json",
        }
        data: Any = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(LUNAR_TIMEOUT_SECONDS),
            follow_redirects=True,
        ) as client:
            for attempt in range(3):
                try:
                    response = await client.get(url, headers=headers)
                except (httpx.RequestError, asyncio.TimeoutError):
                    if attempt < 2:
                        await asyncio.sleep(0.4 * (attempt + 1))
                        continue
                    return None
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        return None
                    break
                if response.status_code not in {429, 500, 502, 503, 504}:
                    return None
                if attempt < 2:
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                return None
        if not isinstance(data, dict) or not data.get("success"):
            return None
        if not isinstance(data.get("player"), dict):
            return None
        return data
