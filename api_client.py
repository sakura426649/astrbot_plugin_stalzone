"""Async client for the public STALZONE (STALCRAFT: X) API.

Design notes
------------
* The API supports application authentication by sending ``Client-Id`` and
  ``Client-Secret`` headers directly.  No OAuth user login is required.
* The client is intentionally thin: it returns decoded JSON and raises typed
  errors.  Command handlers decide how to present failures to QQ users.
* All calls use ``httpx.AsyncClient`` so AstrBot's event loop is never blocked.
* Responses are treated as untrusted/possibly incomplete beta data.  Parsing
  is done with ``.get()`` in the formatter layer; this module only validates
  the top-level shape.
"""

from __future__ import annotations

import asyncio
import random
import re
from typing import Any
from urllib.parse import quote

import httpx

PRODUCTION_BASE_URL = "https://eapi.stalzone.com"
DEMO_BASE_URL = "https://dapi.stalzone.com"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BASE_DELAY = 0.5
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
VALID_REGIONS = frozenset({"ru", "eu", "na", "sea", "nea"})
USER_AGENT = "astrbot-plugin-stalzone/1.0.26"

_ITEM_ID_RE = re.compile(r"^[^\x00-\x1f/\\]{1,128}$")


class StalzoneAPIError(Exception):
    """Base error with a safe message that can be shown in a group chat."""

    user_message = "查询失败，请稍后再试。"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ConfigurationError(StalzoneAPIError):
    user_message = "插件配置有误，请联系管理员检查 Client-Id、Client-Secret、region 和 api_base。"


class MissingCredentialsError(ConfigurationError):
    user_message = "插件未配置 Client-Id / Client-Secret，请联系管理员填写官方 API 应用凭证。"


class BadRequestError(StalzoneAPIError):
    user_message = "请求参数无效，请检查物品 ID、角色名或区服是否正确。"


class NotFoundError(StalzoneAPIError):
    user_message = "未找到相关数据，请检查物品 ID / 角色名是否正确。"


class AuthenticationError(StalzoneAPIError):
    user_message = "官方 API 凭证无效或应用未获批，请联系管理员检查 Client-Id / Client-Secret。"


class RateLimitError(StalzoneAPIError):
    user_message = "官方 API 请求过于频繁，请稍后再试。"


class ServerError(StalzoneAPIError):
    user_message = "官方 API 暂时不可用，请稍后再试。"


class NetworkError(StalzoneAPIError):
    user_message = "连接官方 API 超时或失败，请稍后再试。"


class ResponseError(StalzoneAPIError):
    user_message = "官方 API 返回格式异常，请稍后再试。"


def normalize_base_url(value: str | None) -> str:
    """Map the config value to a concrete API base URL.

    Accepts full URLs plus the friendly aliases ``demo``/``production`` so the
    dashboard selector stays readable.
    """
    raw = (value or "").strip().rstrip("/")
    lowered = raw.lower()
    if not raw or lowered in {"prod", "production", "eapi"}:
        return PRODUCTION_BASE_URL
    if lowered in {"demo", "dapi"}:
        return DEMO_BASE_URL
    if not lowered.startswith(("https://", "http://")):
        raise ConfigurationError(f"Invalid api_base: {raw!r}")
    return raw


def normalize_region(value: str | None) -> str:
    region = (value or "ru").strip().lower()
    if region not in VALID_REGIONS:
        raise ConfigurationError(f"Invalid region: {region!r}")
    return region


class StalzoneAPIClient:
    """Small async wrapper around the STALZONE OpenAPI endpoints."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        region: str = "ru",
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    ) -> None:
        self.client_id = str(client_id or "").strip()
        self.client_secret = str(client_secret or "").strip()
        if not self.client_id or not self.client_secret:
            raise MissingCredentialsError("Client-Id and Client-Secret are required")

        self.region = normalize_region(region)
        self.base_url = normalize_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max(0, min(int(max_retries), 5))
        self.retry_base_delay = max(0.0, float(retry_base_delay))
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    # ------------------------------------------------------------------ auth
    def _headers(self) -> dict[str, str]:
        # Secret headers are added per request and never logged by this module.
        return {
            "Client-Id": self.client_id,
            "Client-Secret": self.client_secret,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:200].replace("\n", " ")
        if isinstance(payload, dict):
            parts = []
            for key in ("title", "message", "detail"):
                value = payload.get(key)
                if value:
                    parts.append(str(value))
            return " | ".join(parts)[:300] or "HTTP error"
        return str(payload)[:300]

    async def _retry_delay(
        self, attempt: int, response: httpx.Response | None
    ) -> None:
        delay = self.retry_base_delay * (2**attempt)
        if response is not None:
            retry_after = response.headers.get("Retry-After", "").strip()
            try:
                delay = max(delay, min(float(retry_after), 2.0))
            except ValueError:
                pass
        if self.retry_base_delay > 0:
            delay += random.uniform(0, self.retry_base_delay * 0.25)
        if delay > 0:
            await asyncio.sleep(delay)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        attempts = self.max_retries + 1
        response: httpx.Response | None = None

        for attempt in range(attempts):
            try:
                response = await self._client.get(
                    path,
                    params=params,
                    headers=self._headers(),
                )
            except httpx.TimeoutException as exc:
                if attempt + 1 < attempts:
                    await self._retry_delay(attempt, None)
                    continue
                raise NetworkError(f"Request timed out: {path}") from exc
            except httpx.RequestError as exc:
                if attempt + 1 < attempts:
                    await self._retry_delay(attempt, None)
                    continue
                raise NetworkError(f"Request failed: {path}: {exc!r}") from exc

            if (
                response.status_code in RETRY_STATUS_CODES
                and attempt + 1 < attempts
            ):
                await self._retry_delay(attempt, response)
                continue
            break

        if response is None:
            raise NetworkError(f"Request failed: {path}")

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as exc:
                raise ResponseError(f"Non-JSON response from {path}") from exc

        detail = self._error_detail(response)
        status = response.status_code
        if status in (400, 422):
            raise BadRequestError(f"HTTP {status}: {detail}", status_code=status)
        if status == 401 or status == 403:
            raise AuthenticationError(f"HTTP {status}: {detail}", status_code=status)
        if status == 404:
            raise NotFoundError(f"HTTP 404: {detail}", status_code=status)
        if status == 429:
            raise RateLimitError(f"HTTP 429: {detail}", status_code=status)
        if status >= 500:
            raise ServerError(f"HTTP {status}: {detail}", status_code=status)
        raise StalzoneAPIError(f"HTTP {status}: {detail}", status_code=status)

    # ------------------------------------------------------------- validation
    @staticmethod
    def _validate_item_id(item_id: str) -> str:
        value = str(item_id or "").strip()
        if not _ITEM_ID_RE.match(value):
            raise BadRequestError(f"Invalid item id: {value!r}")
        return value

    @staticmethod
    def _validate_character(name: str) -> str:
        value = str(name or "").strip()
        if not value or len(value) > 64 or any(ord(ch) < 32 for ch in value):
            raise BadRequestError(f"Invalid character name: {name!r}")
        return value

    # --------------------------------------------------------------- endpoints
    async def get_auction_lots(self, item_id: str, *, limit: int = 50) -> dict[str, Any]:
        item_id = self._validate_item_id(item_id)
        data = await self._get(
            f"/{self.region}/auction/{quote(item_id, safe='')}/lots",
            params={
                "limit": str(max(1, min(limit, 200))),
                "offset": "0",
                "sort": "current_price",
                "order": "asc",
                "additional": "true",
            },
        )
        if not isinstance(data, dict):
            raise ResponseError("Auction lots response is not an object")
        return data

    async def get_auction_history(
        self, item_id: str, *, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        item_id = self._validate_item_id(item_id)
        data = await self._get(
            f"/{self.region}/auction/{quote(item_id, safe='')}/history",
            params={
                "limit": str(max(1, min(limit, 200))),
                "offset": str(max(0, offset)),
                "additional": "true",
            },
        )
        if not isinstance(data, dict):
            raise ResponseError("Auction history response is not an object")
        return data

    async def get_emission(self) -> dict[str, Any]:
        data = await self._get(f"/{self.region}/emission")
        if not isinstance(data, dict):
            raise ResponseError("Emission response is not an object")
        return data

    async def get_profile(
        self, character_name: str, *, region: str | None = None
    ) -> dict[str, Any]:
        name = self._validate_character(character_name)
        target = normalize_region(region or self.region)
        data = await self._get(
            f"/{target}/character/by-name/{quote(name, safe='')}/profile"
        )
        if not isinstance(data, dict):
            raise ResponseError("Profile response is not an object")
        return data

    async def get_profile_by_uuid(
        self, uuid: str, *, region: str | None = None
    ) -> dict[str, Any]:
        value = str(uuid or "").strip()
        if not value or len(value) > 64:
            raise BadRequestError("Invalid character uuid")
        target = normalize_region(region or self.region)
        data = await self._get(
            f"/{target}/character/by-uuid/{quote(value, safe='')}/profile"
        )
        if not isinstance(data, dict):
            raise ResponseError("Profile response is not an object")
        return data

    async def get_regions(self) -> list[dict[str, Any]]:
        data = await self._get("/regions")
        if not isinstance(data, list):
            raise ResponseError("Regions response is not a list")
        return [item for item in data if isinstance(item, dict)]

    async def get_clan(self, clan_id: str) -> dict[str, Any]:
        """Second-version helper: fetch a clan by UUID."""
        value = str(clan_id or "").strip()
        if not value or len(value) > 128:
            raise BadRequestError("Invalid clan id")
        data = await self._get(f"/{self.region}/clan/{quote(value, safe='')}/info")
        if not isinstance(data, dict):
            raise ResponseError("Clan response is not an object")
        return data

    async def list_clans(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """Second-version helper: list clans for name/tag search."""
        data = await self._get(
            f"/{self.region}/clans",
            params={"limit": str(max(1, min(limit, 200))), "offset": str(max(0, offset))},
        )
        if not isinstance(data, dict):
            raise ResponseError("Clan list response is not an object")
        return data

    async def get_operations(
        self,
        *,
        map_name: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "limit": str(max(1, min(limit, 100))),
            "offset": str(max(0, offset)),
            "sort": "date_finish",
            "order": "desc",
        }
        if map_name:
            params["map"] = str(map_name).strip()
        data = await self._get(f"/{self.region}/operations/sessions", params=params)
        if not isinstance(data, dict):
            raise ResponseError("Operations response is not an object")
        return data

    # ----------------------------------------------------------------- cleanup
    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "StalzoneAPIClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
