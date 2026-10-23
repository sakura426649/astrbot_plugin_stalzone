"""Optional SC CORE history fallback.

The official auction history endpoint normally paginates, but some
deployments return the same first page for every ``offset``.  SC CORE exposes
a public history endpoint with a ``before`` cursor, so it can fill in older
sales when the official API refuses to page back.  This is a third-party
archive and must always be labelled as such in user-facing output.
"""

from __future__ import annotations

import httpx
from typing import Any


class ScCoreError(Exception):
    """Raised when SC CORE is unavailable or returns an invalid payload."""


class ScCoreClient:
    BASE_URL = "https://sccore.ru"
    TIMEOUT = 8.0

    def __init__(self, region: str) -> None:
        self.region = str(region or "eu").lower()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ScCoreClient":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(self.TIMEOUT),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; astrbot-plugin-stalzone/1.0.10)",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            raise ScCoreError("SC CORE client is not open")
        try:
            response = await self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise ScCoreError(f"SC CORE request failed: {exc!r}") from exc
        if response.status_code != 200:
            raise ScCoreError(f"SC CORE HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ScCoreError("SC CORE returned non-JSON data") from exc
        if not isinstance(payload, dict):
            raise ScCoreError("SC CORE returned an invalid payload")
        return payload

    async def find_item_key(self, item_id: str) -> str | None:
        payload = await self._get(
            "/api/v1/auction/items/search",
            {"q": item_id, "region": self.region},
        )
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if isinstance(entry, dict) and entry.get("item_key"):
                return str(entry["item_key"])
        return None

    async def get_history(
        self,
        item_key: str,
        *,
        before: str | None = None,
        limit: int = 200,
        quality: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "region": self.region,
            "days": "365",
            "limit": str(max(1, min(limit, 200))),
            "withStats": "false",
        }
        if before:
            params["before"] = before
        if quality is not None:
            params["qlt"] = str(quality)
        return await self._get(
            f"/api/v1/auction/items/{item_key}/history", params
        )
