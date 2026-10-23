"""Optional third-party enrichment: Lunar clan-war player stats.

Lunar exposes a public JSON endpoint used by its player profile page.  It is
NOT the official STALZONE API; the plugin labels it clearly and falls back
silently when Lunar does not have the player or is unavailable.
"""

from __future__ import annotations

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
            "User-Agent": "Mozilla/5.0 (compatible; astrbot-plugin-stalzone/0.3)",
            "Referer": f"{LUNAR_BASE_URL}/players/{quote(str(region).lower(), safe='')}/{quote(name, safe='')}",
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(LUNAR_TIMEOUT_SECONDS),
                follow_redirects=True,
            ) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    return None
                data = response.json()
        except Exception:
            return None
        if not isinstance(data, dict) or not data.get("success"):
            return None
        if not isinstance(data.get("player"), dict):
            return None
        return data
