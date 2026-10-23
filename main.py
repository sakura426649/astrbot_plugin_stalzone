"""AstrBot plugin entry point for STALZONE public-data queries.

Only command parsing, API orchestration and response delivery live here.
HTTP details are in ``api_client.py``, bilingual item resolution in
``item_index.py`` and plain-text rendering in ``formatters.py``.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
import httpx
from astrbot.api.star import Context, Star

try:
    from astrbot.api.message_components import Image as AstrImage
except ImportError:  # older/newer layout fallback
    AstrImage = None  # type: ignore[assignment]

try:  # Package import (normal AstrBot plugin loading).
    from .api_client import (
        DEMO_BASE_URL,
        PRODUCTION_BASE_URL,
        VALID_REGIONS,
        StalzoneAPIClient,
        StalzoneAPIError,
        normalize_base_url,
    )
    from .balance_history import BalanceHistory
    from .command_parser import parse_command
    from .season_pass import SeasonPassError, calculate, parse_arguments
    from .formatters import (
        build_auction_view,
        build_clan_candidate_view,
        build_emission_view,
        build_empty_auction_view,
        build_item_candidate_view,
        build_profile_view,
        format_auction_text,
        format_balance_history,
        format_clan,
        format_clan_candidates,
        format_clans_list,
        format_emission,
        format_help,
        format_item,
        format_item_candidates,
        format_operations,
        format_profile,
        format_regions,
        format_season_pass,
        item_rank_color,
        auction_day_cutoff,
        auction_quality_of,
        parse_auction_query,
        parse_auction_time,
    )
    from .image_renderer import (
        HELP_BACKGROUND,
        render_auction_card,
        faction_icon_path,
        render_candidate_card,
        render_emission_card,
        render_help_card,
        render_profile_card,
        render_text_card,
    )
    from .item_index import (
        ItemIndex,
        category_label,
        display_english,
        display_name,
        display_translation,
    )
    from .lunar_client import LunarProfileClient
    from .sc_core_client import ScCoreClient, ScCoreError
except ImportError:  # Direct execution / flat import fallback.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from api_client import (  # type: ignore[no-redef]
        DEMO_BASE_URL,
        PRODUCTION_BASE_URL,
        VALID_REGIONS,
        StalzoneAPIClient,
        StalzoneAPIError,
        normalize_base_url,
    )
    from balance_history import BalanceHistory  # type: ignore[no-redef]
    from command_parser import parse_command  # type: ignore[no-redef]
    from season_pass import SeasonPassError, calculate, parse_arguments  # type: ignore[no-redef]
    from formatters import (  # type: ignore[no-redef]
        build_auction_view,
        build_clan_candidate_view,
        build_emission_view,
        build_empty_auction_view,
        build_item_candidate_view,
        build_profile_view,
        format_auction_text,
        format_balance_history,
        format_clan,
        format_clan_candidates,
        format_clans_list,
        format_emission,
        format_help,
        format_item,
        format_item_candidates,
        format_operations,
        format_profile,
        format_regions,
        format_season_pass,
        item_rank_color,
        auction_day_cutoff,
        auction_quality_of,
        parse_auction_query,
        parse_auction_time,
    )
    from image_renderer import (  # type: ignore[no-redef]
        HELP_BACKGROUND,
        faction_icon_path,
        render_auction_card,
        render_candidate_card,
        render_emission_card,
        render_help_card,
        render_profile_card,
        render_text_card,
    )
    from item_index import (  # type: ignore[no-redef]
        ItemIndex,
        category_label,
        display_english,
        display_name,
        display_translation,
    )
    from lunar_client import LunarProfileClient  # type: ignore[no-redef]
    from sc_core_client import ScCoreClient, ScCoreError  # type: ignore[no-redef]


UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
PLUGIN_VERSION = "0.47.1"
SZ_BARE_RE = r"(?i)^\s*(?:sz|stalzone)(?:@\S+)?\s+"
IMAGE_COMMANDS = {
    "auction",
    "player",
    "clan",
    "item",
    "emission",
    "candidates",
    "clans",
    "operations",
    "regions",
    "balance",
    "pass",
}


@dataclass
class PluginReply:
    text: str
    icon_url: str | None = None
    auction_view: dict[str, Any] | None = None
    candidate_view: dict[str, Any] | None = None
    emission_view: dict[str, Any] | None = None
    item_meta: dict[str, Any] | None = None
    profile_view: dict[str, Any] | None = None
    faction: str | None = None
    sub: str | None = None


@dataclass
class PendingChoice:
    kind: str
    query: str
    candidates: list[dict[str, Any]]
    created: float
    quality: int | None = None
    before: Any = None
    count: int | None = None

USAGE = {
    "auction": (
        "用法：/sz auction <item_id 或 中文/英文物品名> [品质] [日期] [数量]\n"
        "示例：/sz 拍卖 寒冰；/sz 拍卖 原子 粉；/sz 拍卖 原子 粉 6.11 20\n"
        "日期支持 6.11、6/11、25.6.11、25/6/11；数量需同时有品质和日期，最多 200"
    ),
    "emission": (
        "用法：/sz emission [EU/RU/NA/SEA/NEA]\n"
        "中文：/sz 风暴 [区服]\n"
        "示例：/sz 风暴；/sz 风暴 ru"
    ),
    "item": "用法：/sz item <中文名/英文名/ID>\n示例：/sz item 寒冰 或 /sz item Spectral Crystal",
    "player": "用法：/sz player <角色名 或 UUID>\n中文：/sz 玩家 <角色名 或 UUID>",
    "clan": "用法：/sz clan <战队名/标签/ID>",
    "clans": "用法：/sz clans [页码]",
    "operations": "用法：/sz operations [地图ID]",
    "balance": "用法：/sz 调整 <武器/神器/装备名或ID>\n示例：/sz 调整 AK-308 或 /sz 调整 多面体",
    "pass": (
        "用法：/sz 通行证计算 <当前等级> <每日任务>[+超载] <剩余天数> [每周天数=7]\n"
        "也可：/sz 通行证计算 15 15 2 20 7（等级 每日任务 超载 剩余天数 每周天数，超载可为0）\n"
        "每周天数只在“+号且四参数”或“五参数”时取最后一个参数；三参数/无+四参数默认7天\n"
        "示例：/sz 通行证计算 15 15+2 20 7 或 /sz 通行证计算 15 15 2 20"
    ),
}


class StalzonePlugin(Star):
    """STALZONE auction / emission / profile / clan / item query plugin."""

    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config = config
        self._help_lock: asyncio.Lock | None = None
        self._help_cache_dir: Path | None = None
        self._sc_item_keys: dict[tuple[str, str], str] = {}
        self._pending_choices: dict[str, PendingChoice] = {}
        self._http_client: httpx.AsyncClient | None = None
        self._http_base = ""
        self._icons_pruned_at = 0.0
        self.item_index = ItemIndex(
            overrides_path=self._cache_dir() / "item_name_overrides.json"
        )
        self.balance_history = BalanceHistory()

    # ------------------------------------------------------------------ config
    def _cfg(self, key: str, default: Any = "") -> Any:
        try:
            return self.config.get(key, default)
        except AttributeError:
            return default

    def _region(self) -> str:
        return str(self._cfg("region", "ru") or "ru").strip().lower()

    def _api_base(self) -> str:
        configured = self._cfg("api_base", "")
        return str(configured or os.getenv("STALZONE_API_BASE") or PRODUCTION_BASE_URL).strip()

    def _is_demo(self) -> bool:
        try:
            return normalize_base_url(self._api_base()).rstrip("/") == DEMO_BASE_URL
        except StalzoneAPIError:
            return False

    def _shared_http_client(self) -> httpx.AsyncClient:
        """Reuse one connection pool across commands instead of re-handshaking."""
        base = normalize_base_url(self._api_base())
        if self._http_client is None or self._http_base != base:
            previous = self._http_client
            self._http_client = httpx.AsyncClient(
                base_url=base,
                timeout=httpx.Timeout(10.0),
                follow_redirects=True,
            )
            self._http_base = base
            if previous is not None:
                try:
                    asyncio.get_running_loop().create_task(previous.aclose())
                except RuntimeError:
                    pass
        return self._http_client

    async def terminate(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _make_client(self, region: str | None = None) -> StalzoneAPIClient:
        return StalzoneAPIClient(
            client_id=str(self._cfg("client_id", "") or ""),
            client_secret=str(self._cfg("client_secret", "") or ""),
            region=region or self._region(),
            base_url=self._api_base(),
            client=self._shared_http_client(),
        )

    def _render_mode(self) -> str:
        mode = str(self._cfg("render_mode", "auto") or "auto").strip().lower()
        return mode if mode in {"auto", "text", "image"} else "auto"

    def _cache_dir(self) -> Path:
        """Return the plugin data directory, falling back to temp in tests."""
        if self._help_cache_dir is not None:
            return self._help_cache_dir
        candidates: list[Path] = []
        try:
            from astrbot.api.star import StarTools

            getter = getattr(StarTools, "get_data_dir", None)
            if getter is not None:
                try:
                    base = getter("astrbot_plugin_stalzone")
                except TypeError:
                    base = getter()
                if base:
                    candidates.append(Path(base))
        except Exception:
            pass
        try:
            getter = getattr(self.context, "get_data_dir", None)
            if getter is not None:
                try:
                    base = getter("astrbot_plugin_stalzone")
                except TypeError:
                    base = getter()
                if base:
                    candidates.append(Path(base))
        except Exception:
            pass
        env_dir = os.getenv("ASTRBOT_DATA_DIR", "").strip()
        if env_dir:
            candidates.append(Path(env_dir))
        for base in candidates:
            path = base if base.name == "astrbot_plugin_stalzone" else base / "astrbot_plugin_stalzone"
            try:
                path.mkdir(parents=True, exist_ok=True)
                self._help_cache_dir = path
                return path
            except OSError:
                continue
        path = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone" / "data"
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self._help_cache_dir = path
        return path

    def _help_cache_path(self) -> Path:
        try:
            background_stamp = str(HELP_BACKGROUND.stat().st_mtime_ns)
        except OSError:
            background_stamp = "missing"
        key = hashlib.sha1(
            "|".join(
                [
                    PLUGIN_VERSION,
                    self._region(),
                    str(self._is_demo()),
                    str(self._cfg("font_path", "") or ""),
                    background_stamp,
                ]
            ).encode("utf-8")
        ).hexdigest()[:10]
        env = "demo" if self._is_demo() else "prod"
        return self._cache_dir() / "help" / f"help_{self._region()}_{env}_{key}.png"

    async def _help_image(self) -> Path | None:
        cache = self._help_cache_path()
        try:
            if cache.is_file() and cache.stat().st_size > 1024:
                return cache
        except OSError:
            pass
        if self._help_lock is None:
            self._help_lock = asyncio.Lock()
        async with self._help_lock:
            try:
                if cache.is_file() and cache.stat().st_size > 1024:
                    return cache
            except OSError:
                pass
            cache.parent.mkdir(parents=True, exist_ok=True)
            result = await asyncio.to_thread(
                render_help_card,
                region=self._region(),
                demo=self._is_demo(),
                version=PLUGIN_VERSION,
                font_path=str(self._cfg("font_path", "") or "").strip() or None,
                output=cache,
            )
            if result:
                # Version/region changes must not leave old help images behind.
                try:
                    for old in cache.parent.glob("help_*.png"):
                        if old != cache:
                            old.unlink(missing_ok=True)
                except OSError:
                    pass
            return result

    def _prune_icon_cache(self) -> None:
        now = time.time()
        if now - self._icons_pruned_at < 86400:
            return
        self._icons_pruned_at = now
        cache_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone" / "icons"
        cutoff = now - 30 * 86400
        try:
            for old in cache_dir.glob("*.png"):
                try:
                    if old.stat().st_mtime < cutoff:
                        old.unlink(missing_ok=True)
                except OSError:
                    continue
        except OSError:
            pass

    async def _fetch_icon(self, url: str | None) -> Path | None:
        if not url:
            return None
        await asyncio.to_thread(self._prune_icon_cache)
        item_id = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        local = Path(__file__).with_name("item_icons") / f"{item_id}.png"
        if local.is_file():
            return local
        cache_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone" / "icons"
        cached = cache_dir / f"{item_id}.png"
        if cached.is_file():
            return cached
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; astrbot-plugin-stalzone/0.5)"},
                )
                if response.status_code != 200 or not response.content:
                    return None
                cache_dir.mkdir(parents=True, exist_ok=True)
                await asyncio.to_thread(cached.write_bytes, response.content)
                return cached
        except Exception:
            return None

    async def _attach_candidate_icons(self, view: dict[str, Any]) -> None:
        """Resolve bundled/cached icons first, then batch-download the rest."""
        await asyncio.to_thread(self._prune_icon_cache)
        entries = [x for x in (view.get("entries") or []) if isinstance(x, dict)]
        cache_dir = Path(tempfile.gettempdir()) / "astrbot_plugin_stalzone" / "icons"
        pending: list[tuple[dict[str, Any], str, str]] = []

        for entry in entries:
            url = str(entry.get("icon_url") or "").strip()
            if not url:
                continue
            item_id = url.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            local = Path(__file__).with_name("item_icons") / f"{item_id}.png"
            cached = cache_dir / f"{item_id}.png"
            if local.is_file():
                entry["icon_path"] = str(local)
            elif cached.is_file():
                entry["icon_path"] = str(cached)
            else:
                pending.append((entry, url, item_id))

        if not pending:
            return
        semaphore = asyncio.Semaphore(16)

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(5.0),
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; astrbot-plugin-stalzone/0.5)"},
            ) as client:
                async def fetch(entry: dict[str, Any], url: str, item_id: str) -> None:
                    async with semaphore:
                        try:
                            response = await client.get(url)
                            if response.status_code != 200 or not response.content:
                                return
                            cache_dir.mkdir(parents=True, exist_ok=True)
                            path = cache_dir / f"{item_id}.png"
                            await asyncio.to_thread(path.write_bytes, response.content)
                            entry["icon_path"] = str(path)
                        except Exception:
                            return

                await asyncio.wait_for(
                    asyncio.gather(
                        *(fetch(entry, url, item_id) for entry, url, item_id in pending)
                    ),
                    timeout=10.0,
                )
        except (asyncio.TimeoutError, httpx.HTTPError):
            # Whatever finished stays attached; the rest render as placeholders.
            pass

    async def _render_image(
        self,
        text: str,
        sub: str,
        icon_url: str | None = None,
        auction_view: dict[str, Any] | None = None,
        candidate_view: dict[str, Any] | None = None,
        emission_view: dict[str, Any] | None = None,
        item_meta: dict[str, Any] | None = None,
        profile_view: dict[str, Any] | None = None,
        faction: str | None = None,
    ) -> Path | None:
        if self._render_mode() == "text" or sub not in IMAGE_COMMANDS:
            return None
        try:
            icon_path = await self._fetch_icon(icon_url)
            if icon_path is None and faction:
                icon_path = faction_icon_path(faction)
            font_path = str(self._cfg("font_path", "") or "").strip() or None
            if sub == "auction" and auction_view:
                path = await asyncio.to_thread(
                    render_auction_card,
                    auction_view,
                    font_path=font_path,
                    icon_path=icon_path,
                )
            elif sub == "candidates" and candidate_view:
                await self._attach_candidate_icons(candidate_view)
                path = await asyncio.to_thread(
                    render_candidate_card,
                    candidate_view,
                    font_path=font_path,
                )
            elif sub == "emission" and emission_view:
                path = await asyncio.to_thread(
                    render_emission_card,
                    emission_view,
                    font_path=font_path,
                )
            elif sub == "player" and profile_view:
                path = await asyncio.to_thread(
                    render_profile_card,
                    profile_view,
                    font_path=font_path,
                )
            else:
                path = await asyncio.to_thread(
                    render_text_card,
                    text,
                    font_path=font_path,
                    icon_path=icon_path,
                    item_meta=item_meta,
                )
        except Exception:
            logger.exception("STALZONE image render failed")
            return None
        if path is None and self._render_mode() == "image":
            logger.warning(
                "STALZONE image mode requested but Pillow/CJK font is unavailable; "
                "falling back to text"
            )
        return path

    @staticmethod
    def _image_base64(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode("ascii")

    @staticmethod
    def _decorate(item: dict[str, Any]) -> dict[str, Any]:
        value = dict(item)
        value["cat_label"] = category_label(value.get("cat"))
        value["display"] = display_name(value)
        return value

    def _resolve_item(self, query: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        if not self.item_index.ready:
            return None, []
        return self.item_index.resolve(query)

    # ------------------------------------------------------------- candidates
    CHOICE_TTL_SECONDS = 600
    MAX_PENDING_CHOICES = 200

    @staticmethod
    def _choice_scope(event: Any) -> str:
        """Return a group/session key so any member can answer ``sz 候选 1``."""
        for attr in ("unified_msg_origin", "session_id", "group_id", "chat_id"):
            value = getattr(event, attr, None)
            if value not in (None, ""):
                return str(value)
        for method_name in ("get_group_id", "get_session_id", "get_chat_id"):
            method = getattr(event, method_name, None)
            if callable(method):
                try:
                    value = method()
                except Exception:
                    continue
                if value not in (None, ""):
                    return str(value)
        return "default"

    def _remember_choice(
        self,
        event: Any,
        kind: str,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        quality: int | None = None,
        before: Any = None,
        count: int | None = None,
    ) -> None:
        if event is None or len(candidates) <= 1:
            return
        now = time.monotonic()
        for key, pending in list(self._pending_choices.items()):
            if now - pending.created > self.CHOICE_TTL_SECONDS:
                self._pending_choices.pop(key, None)
        scope = self._choice_scope(event)
        if scope not in self._pending_choices and len(self._pending_choices) >= self.MAX_PENDING_CHOICES:
            oldest = min(
                self._pending_choices.items(),
                key=lambda pair: pair[1].created,
                default=(None, None),
            )[0]
            if oldest is not None:
                self._pending_choices.pop(oldest, None)
        self._pending_choices[scope] = PendingChoice(
            kind=kind,
            query=query,
            candidates=[dict(candidate) for candidate in candidates],
            created=now,
            quality=quality,
            before=before,
            count=count,
        )

    @staticmethod
    def _with_render_sub(result: str | PluginReply, sub: str) -> str | PluginReply:
        if isinstance(result, PluginReply):
            result.sub = sub
        return result

    async def _handle_candidate(self, argument: str, event: Any) -> str | PluginReply:
        match = re.fullmatch(r"\s*#?(\d{1,2})\s*", str(argument or ""))
        if not match:
            return "用法：sz 候选 <序号>\n例如：sz 候选 1"
        scope = self._choice_scope(event)
        pending = self._pending_choices.get(scope)
        if pending is None or time.monotonic() - pending.created > self.CHOICE_TTL_SECONDS:
            self._pending_choices.pop(scope, None)
            return (
                "没有待选择的候选，或候选列表已过期。\n"
                "请先发送 /sz 物品 <名称>、/sz 拍卖 <名称> 等指令，"
                "再根据候选列表回复 sz 候选 <序号>。"
            )
        index = int(match.group(1))
        total = len(pending.candidates)
        if index < 1 or index > total:
            return f"序号超出范围，请在 1–{total} 中选择。"
        candidate = pending.candidates[index - 1]
        self._pending_choices.pop(scope, None)
        if pending.kind == "clan":
            return PluginReply(
                format_clan(candidate, self._region()),
                faction=str(candidate.get("alliance") or ""),
                sub="clan",
            )
        selected = str(candidate.get("id") or "").strip()
        if not selected:
            return "该候选缺少物品 ID，无法自动查询。"
        if pending.kind == "item":
            result = await self._handle_item(selected, event=event)
            return self._with_render_sub(result, "item")
        if pending.kind == "balance":
            result = await self._handle_balance(selected, event=event)
            return self._with_render_sub(result, "balance")
        if pending.kind == "auction":
            result = await self._handle_auction(
                selected,
                event=event,
                parsed=(selected, pending.quality, pending.before, pending.count),
            )
            return self._with_render_sub(result, "auction")
        return "候选类型无效，请重新发起查询。"

    # --------------------------------------------------------------- commands
    @filter.command("sz")
    async def sz(self, event: AstrMessageEvent):
        """Slash form: /sz ..."""
        async for result in self._dispatch_sz(event):
            yield result

    @filter.regex(SZ_BARE_RE)
    async def sz_bare(self, event: AstrMessageEvent):
        """Prefixless form: sz ... / stalzone ..."""
        async for result in self._dispatch_sz(event):
            yield result

    async def _dispatch_sz(self, event: AstrMessageEvent):
        """查询 STALZONE 拍卖、辐射爆发、角色、战队与物品数据。"""
        if getattr(event, "_stalzone_sz_seen", False):
            return
        try:
            event._stalzone_sz_seen = True
        except Exception:
            pass
        sub, arg = parse_command(event.message_str)
        if sub and sub != "candidate":
            self._pending_choices.pop(self._choice_scope(event), None)
        if not sub or sub == "help":
            try:
                image = await self._help_image()
            except Exception:
                logger.exception("STALZONE help image generation failed")
                image = None
            if image is not None:
                try:
                    if AstrImage is not None:
                        encoded = await asyncio.to_thread(self._image_base64, image)
                        yield event.chain_result([AstrImage.fromBase64(encoded)])
                    else:
                        yield event.image_result(str(image))
                    return
                except Exception:
                    logger.exception(
                        "STALZONE help image send failed; falling back to text"
                    )
            yield event.plain_result(format_help(self._region(), demo=self._is_demo()))
            return

        if sub == "auction":
            if not arg:
                yield event.plain_result(USAGE["auction"])
                return
            coro = self._handle_auction(arg, event=event)
        elif sub == "candidate":
            coro = self._handle_candidate(arg, event)
        elif sub == "emission":
            coro = self._handle_emission(arg)
        elif sub == "player":
            if not arg:
                yield event.plain_result(USAGE["player"])
                return
            coro = self._handle_profile(arg)
        elif sub == "item":
            if not arg:
                yield event.plain_result(USAGE["item"])
                return
            coro = self._handle_item(arg, event=event)
        elif sub == "balance":
            if not arg:
                yield event.plain_result(USAGE["balance"])
                return
            coro = self._handle_balance(arg, event=event)
        elif sub == "pass":
            if not arg:
                yield event.plain_result(USAGE["pass"])
                return
            coro = self._handle_pass(arg)
        elif sub == "clan":
            if not arg:
                yield event.plain_result(USAGE["clan"])
                return
            coro = self._handle_clan(arg, event=event)
        elif sub == "clans":
            coro = self._handle_clans(arg)
        elif sub == "operations":
            coro = self._handle_operations(arg)
        elif sub == "regions":
            coro = self._handle_regions()
        else:
            yield event.plain_result(f"未知指令：{sub}\n使用 /sz help 查看可用指令。")
            return

        icon_url = None
        auction_view = None
        candidate_view = None
        emission_view = None
        item_meta = None
        profile_view = None
        faction = None
        render_sub = sub
        try:
            result = await coro
            if isinstance(result, PluginReply):
                text = result.text
                icon_url = result.icon_url
                auction_view = result.auction_view
                candidate_view = result.candidate_view
                emission_view = result.emission_view
                item_meta = result.item_meta
                profile_view = result.profile_view
                faction = result.faction
                if result.sub:
                    render_sub = result.sub
            else:
                text = result
                icon_url = None
        except StalzoneAPIError as exc:
            # Technical detail goes to the log; QQ gets a safe message.
            logger.warning("STALZONE query failed (%s): %s", exc.__class__.__name__, exc)
            text = exc.user_message
        except Exception:
            logger.exception("Unexpected STALZONE plugin error")
            text = "查询失败，请稍后再试。"

        if not text:
            return
        image = await self._render_image(
            text,
            render_sub,
            icon_url,
            auction_view,
            candidate_view,
            emission_view,
            item_meta,
            profile_view,
            faction,
        )
        if image is not None:
            try:
                # Sending base64 avoids Docker/NapCat file-path sharing issues.
                if AstrImage is not None:
                    encoded = await asyncio.to_thread(self._image_base64, image)
                    yield event.chain_result([AstrImage.fromBase64(encoded)])
                else:
                    yield event.image_result(str(image))
                return
            except Exception:
                logger.exception("STALZONE image send failed; trying image_result")
                try:
                    yield event.image_result(str(image))
                    return
                except Exception:
                    logger.exception("STALZONE image_result failed; falling back to text")
        yield event.plain_result(text)

    # --------------------------------------------------------------- handlers
    async def _handle_auction(
        self,
        item_query: str,
        *,
        event: Any = None,
        parsed: tuple[str, int | None, Any, int | None] | None = None,
    ) -> str | PluginReply:
        if parsed is None:
            try:
                item_query, quality_filter, before_date, history_count = (
                    parse_auction_query(item_query)
                )
            except ValueError as exc:
                return str(exc)
        else:
            item_query, quality_filter, before_date, history_count = parsed
        before = auction_day_cutoff(before_date) if before_date is not None else None
        item, matches = await asyncio.to_thread(self._resolve_item, item_query)
        icon_url = None
        non_artifact = False
        item_color = None
        if item:
            item_id = item["id"]
            label = display_name(item)
            icon_url = item.get("icon")
            item_color = item.get("color")
            non_artifact = not str(item.get("cat") or "").startswith("artefact")
        elif matches:
            candidates = [self._decorate(candidate) for candidate in matches]
            self._remember_choice(
                event,
                "auction",
                item_query,
                candidates,
                quality=quality_filter,
                before=before_date,
                count=history_count,
            )
            text = format_item_candidates(item_query, candidates)
            if len(candidates) <= 1:
                return text
            return PluginReply(
                text,
                candidate_view=build_item_candidate_view(item_query, candidates),
                sub="candidates",
            )
        else:
            raw = item_query.strip()
            if not ITEM_ID_RE.match(raw):
                return "未找到相关数据，请先 /sz item <中文名/英文名> 确认物品 ID。"
            item_id = raw
            raw_item = self.item_index.get(raw) if self.item_index.ready else None
            label = display_name(raw_item) if raw_item else None
            icon_url = raw_item.get("icon") if raw_item else None
            if raw_item:
                item_color = raw_item.get("color")
                non_artifact = not str(raw_item.get("cat") or "").startswith("artefact")
        item_name_color = (
            item_rank_color(item_color) if non_artifact else None
        )
        if non_artifact:
            quality_filter = None
        short_label = (label or item_id).split(" / ", 1)[0].strip()

        async with self._make_client() as client:
            errors: list[Exception] = []
            if before is not None:
                # A dated query is historical only; current lots would be noise.
                if history_count is not None:
                    fetch_limit = history_count
                elif non_artifact:
                    fetch_limit = 10
                elif quality_filter is not None:
                    fetch_limit = 20
                else:
                    fetch_limit = 5
                history_payload, page_errors = await self._fetch_dated_history(
                    client,
                    item_id,
                    before=before,
                    quality_filter=quality_filter,
                    limit=fetch_limit,
                    non_artifact=non_artifact,
                )
                errors.extend(page_errors)
                official_prices = (
                    history_payload.get("prices")
                    if isinstance(history_payload.get("prices"), list)
                    else []
                )
                if (
                    self._cfg("sc_core_fallback", True)
                    and (history_payload.get("window_exhausted") or not official_prices)
                ):
                    sc_payload, sc_errors = await self._fetch_sc_core_history(
                        item_id,
                        client.region,
                        before=before,
                        quality_filter=quality_filter,
                        limit=fetch_limit,
                        non_artifact=non_artifact,
                    )
                    if sc_payload and sc_payload.get("prices"):
                        merged = list(official_prices)
                        seen = {
                            (entry.get("time"), entry.get("price"), entry.get("amount"))
                            for entry in merged
                            if isinstance(entry, dict)
                        }
                        for entry in sc_payload["prices"]:
                            key = (
                                entry.get("time"),
                                entry.get("price"),
                                entry.get("amount"),
                            )
                            if key in seen:
                                continue
                            seen.add(key)
                            merged.append(entry)
                        history_payload = {
                            "total": len(merged),
                            "prices": merged,
                            "source": "official+sc_core" if official_prices else "sc_core",
                            "window_exhausted": sc_payload.get("window_exhausted", False),
                        }
                        errors = []
                    elif sc_payload and sc_payload.get("coverage_from"):
                        history_payload["sc_coverage_from"] = sc_payload["coverage_from"]
                        history_payload["sc_coverage_to"] = sc_payload.get("coverage_to")
                    elif sc_errors:
                        errors.extend(sc_errors)
                lots_payload: dict[str, Any] = {}
            else:
                # Fetch concurrently; one failed side should not hide the other.
                results = await asyncio.gather(
                    client.get_auction_lots(item_id, limit=100),
                    client.get_auction_history(item_id, limit=100),
                    return_exceptions=True,
                )
                lots, history = results
                errors = [value for value in results if isinstance(value, Exception)]
                if len(errors) == 2:
                    raise errors[0]
                if errors:
                    logger.warning(
                        "STALZONE auction partial failure for %s: %s",
                        item_id,
                        errors[0],
                    )
                lots_payload = lots if isinstance(lots, dict) else {}
                history_payload = history if isinstance(history, dict) else {}
            view = build_auction_view(
                item_id,
                lots_payload,
                history_payload,
                client.region,
                item_label=label,
                quality_filter=quality_filter,
                before=before,
                history_limit=history_count,
                non_artifact=non_artifact,
                item_color=item_name_color,
            )
            text = format_auction_text(view)
            empty_view = None
            if view is None:
                note = ""
                if before_date is not None:
                    text = (
                        f"截至 {before_date.year}/{before_date.month}/{before_date.day} "
                        f"没有找到{short_label}成交记录。"
                    )
                    if history_payload.get("window_exhausted"):
                        coverage = str(history_payload.get("sc_coverage_from") or "")
                        if history_payload.get("repeated_page"):
                            note = (
                                "官方成交历史接口只返回最近一页（约 200 条），无法继续翻页。"
                            )
                            if coverage:
                                note += (
                                    f" SC CORE 存档覆盖自 {coverage[:10]}，"
                                    "该日期之前没有可用数据。"
                                )
                        else:
                            note = (
                                f"已检查最近 {history_payload.get('scanned', 0)} 条成交，"
                                "仍未到达该日期；官方可查历史范围可能更短。"
                            )
                            if coverage:
                                note += f"；SC CORE 存档覆盖自 {coverage[:10]}"
                        text += "\n" + note
                else:
                    text = f"没有找到{short_label}成交记录。"
                empty_view = build_empty_auction_view(
                    item_id,
                    label,
                    client.region,
                    quality_filter=quality_filter,
                    before=before,
                    note=note,
                )
            if errors:
                text += "\n（注：在售或成交的部分数据获取失败，以上为可用部分。）"
            return PluginReply(
                text,
                icon_url=icon_url,
                auction_view=view or empty_view,
            )

    async def _fetch_dated_history(
        self,
        client: StalzoneAPIClient,
        item_id: str,
        *,
        before: datetime,
        quality_filter: int | None,
        limit: int,
        non_artifact: bool = False,
    ) -> tuple[dict[str, Any], list[Exception]]:
        """Walk history in 200-entry pages until the date and count are met.

        The endpoint is newest-first.  Walking sequentially avoids relying on
        large offsets and stops as soon as enough records on/before the cutoff
        are collected, so recent dates usually need only one or two pages.
        """
        page_size = 200
        max_pages = 40
        max_records = 4000
        fallback_used = False
        errors: list[Exception] = []
        entries: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        matching = 0
        valid = 0
        scanned = 0
        target = max(1, min(limit, 200))
        offset = 0
        previous_signature: tuple[Any, ...] | None = None
        reached_cutoff = False
        repeated_page = False

        for _page in range(max_pages):
            try:
                payload = await client.get_auction_history(
                    item_id, limit=page_size, offset=offset
                )
            except Exception as exc:
                if page_size == 200 and not fallback_used:
                    fallback_used = True
                    page_size = 100
                    continue
                errors.append(exc)
                break
            prices = (
                [
                    entry
                    for entry in (payload.get("prices") or [])
                    if isinstance(entry, dict)
                ]
                if isinstance(payload, dict)
                else []
            )
            if not prices:
                break
            scanned += len(prices)
            signature = tuple(
                (entry.get("time"), entry.get("price"), entry.get("amount"))
                for entry in prices
            )
            if signature == previous_signature:
                if page_size == 200 and not fallback_used:
                    # A few deployments mishandle 200-item history pages;
                    # retry the same offset with a 100-item page.
                    fallback_used = True
                    page_size = 100
                    continue
                repeated_page = True
                logger.warning(
                    "STALZONE dated auction repeated page for %s at offset %s",
                    item_id,
                    offset,
                )
                break
            previous_signature = signature

            for entry in prices:
                timestamp = parse_auction_time(entry.get("time"))
                if timestamp is None:
                    continue
                if timestamp <= before:
                    reached_cutoff = True
                else:
                    continue
                key = (entry.get("time"), entry.get("price"), entry.get("amount"))
                if key in seen:
                    continue
                seen.add(key)
                entries.append(entry)
                valid += 1
                if (
                    quality_filter is None
                    or auction_quality_of(entry) == quality_filter
                ):
                    matching += 1

            if quality_filter is not None:
                if matching >= target:
                    break
            elif non_artifact:
                if valid >= target:
                    break
            elif valid >= 30:
                break
            if scanned >= max_records:
                break
            offset += len(prices)

        exhausted = bool(scanned) and not reached_cutoff
        if errors:
            logger.warning(
                "STALZONE dated auction page failure for %s: %s",
                item_id,
                errors[0],
            )
        return {
            "total": len(entries),
            "prices": entries,
            "scanned": scanned,
            "window_exhausted": exhausted,
            "repeated_page": repeated_page,
        }, errors

    async def _fetch_sc_core_history(
        self,
        item_id: str,
        region: str,
        *,
        before: datetime,
        quality_filter: int | None,
        limit: int,
        non_artifact: bool,
    ) -> tuple[dict[str, Any] | None, list[Exception]]:
        """Fill older sales from SC CORE when official pagination stalls."""
        if not self._cfg("sc_core_fallback", True):
            return None, []
        region = str(region or "").lower()
        cache_key = (region, item_id)
        target = max(1, min(limit, 200))
        entries: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        valid = 0
        matching = 0
        scanned = 0
        reached_cutoff = False
        cursor: str | None = None
        coverage_from: str | None = None
        coverage_to: str | None = None
        try:
            async with ScCoreClient(region) as client:
                item_key = self._sc_item_keys.get(cache_key)
                if not item_key:
                    item_key = await client.find_item_key(item_id)
                    if not item_key:
                        return None, []
                    self._sc_item_keys[cache_key] = item_key
                    if len(self._sc_item_keys) > 4096:
                        self._sc_item_keys.pop(next(iter(self._sc_item_keys)), None)
                for _page in range(20):
                    page = await client.get_history(
                        item_key,
                        before=cursor,
                        limit=200,
                        quality=quality_filter,
                    )
                    status = page.get("history_status")
                    if isinstance(status, dict):
                        coverage_from = coverage_from or status.get("first_event_ts")
                        coverage_to = coverage_to or status.get("last_event_ts")
                    events = page.get("events")
                    events = (
                        [event for event in events if isinstance(event, dict)]
                        if isinstance(events, list)
                        else []
                    )
                    if not events:
                        break
                    scanned += len(events)
                    page_oldest: datetime | None = None
                    for event in events:
                        timestamp = parse_auction_time(event.get("event_time"))
                        if timestamp is None:
                            continue
                        if page_oldest is None or timestamp < page_oldest:
                            page_oldest = timestamp
                        if timestamp > before:
                            continue
                        reached_cutoff = True
                        entry = {
                            "time": event.get("event_time"),
                            "price": event.get("price"),
                            "amount": event.get("amount"),
                            "additional": event.get("additional") or {},
                        }
                        key = (entry["time"], entry["price"], entry["amount"])
                        if key in seen:
                            continue
                        seen.add(key)
                        entries.append(entry)
                        valid += 1
                        matching += 1
                    if quality_filter is not None:
                        if matching >= target:
                            break
                    elif non_artifact:
                        if valid >= target:
                            break
                    elif valid >= 30:
                        break
                    if page_oldest is None or scanned >= 4000:
                        break
                    next_cursor = page_oldest.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if next_cursor == cursor:
                        break
                    cursor = next_cursor
        except Exception as exc:
            logger.warning(
                "STALZONE SC CORE fallback failed for %s: %s",
                item_id,
                exc,
            )
            return None, [exc]
        if not entries and not coverage_from:
            return None, []
        return {
            "total": len(entries),
            "prices": entries,
            "scanned": scanned,
            "window_exhausted": not reached_cutoff,
            "source": "sc_core" if entries else "",
            "coverage_from": coverage_from,
            "coverage_to": coverage_to,
        }, []

    async def _handle_emission(self, argument: str = "") -> str | PluginReply:
        token = str(argument or "").strip().lower()
        if token:
            if token not in VALID_REGIONS:
                return USAGE["emission"]
            region = token
        else:
            region = None
        client_factory = self._make_client
        client = client_factory(region=region) if region else client_factory()
        async with client as client:
            if region:
                client.region = region
            payload = await client.get_emission()
            view = build_emission_view(payload, client.region)
            return PluginReply(
                format_emission(payload, client.region, view=view),
                emission_view=view,
                sub="emission",
            )

    async def _handle_profile(self, name_or_uuid: str) -> str:
        value = name_or_uuid.strip()
        parts = value.rsplit(maxsplit=1)
        region = None
        if len(parts) == 2 and parts[1].upper() in {"EU", "RU", "NA", "SEA"}:
            value = parts[0].strip()
            region = parts[1].lower()
        if not value:
            return USAGE["player"]
        client_factory = self._make_client
        client = client_factory(region=region) if region else client_factory()
        async with client as client:
            target_region = region or client.region
            # Keep the rendered region, Lunar/HQ links and the request path on
            # the same value even if a cached client instance had another default.
            client.region = target_region
            logger.info(
                "STALZONE profile request: region=%s character=%r",
                target_region,
                value,
            )
            if UUID_RE.match(value):
                payload = await client.get_profile_by_uuid(
                    value, region=target_region
                )
            else:
                payload = await client.get_profile(value, region=target_region)

            player_name = str(payload.get("username") or value)
            lunar = None
            lunar_url = None
            if self._cfg("lunar_enrich", True):
                lunar_url = (
                    f"https://lunar-zone.com/players/"
                    f"{quote(client.region, safe='')}/{quote(player_name, safe='')}"
                )
                lunar = await LunarProfileClient().get_player_profile(
                    client.region, player_name
                )
            hq_url = (
                f"https://stalzonehq.com/characters/{quote(client.region.upper(), safe='')}/"
                f"{quote(player_name, safe='')}"
            )
            view = build_profile_view(
                payload,
                client.region,
                lunar=lunar,
                lunar_url=lunar_url,
                hq_url=hq_url,
            )
            return PluginReply(
                format_profile(
                    payload,
                    client.region,
                    lunar=lunar,
                    lunar_url=lunar_url,
                    hq_url=hq_url,
                    view=view,
                ),
                profile_view=view,
                sub="player",
            )

    async def _handle_item(
        self, query: str, *, event: Any = None
    ) -> str | PluginReply:
        if not self.item_index.ready:
            return "物品索引未加载，请联系管理员更新 item_index.json。"
        item, matches = await asyncio.to_thread(self._resolve_item, query)
        if item:
            details = self.item_index.get_details(item["id"])
            return PluginReply(
                format_item(self._decorate(item), details),
                icon_url=item.get("icon"),
                item_meta={
                    "en": display_english(item),
                    "zh": display_translation(item),
                    "color": str(item.get("color") or ""),
                    "rank": str(details.get("rank") or ""),
                    "cat": str(item.get("cat") or ""),
                },
            )
        if matches:
            candidates = [self._decorate(candidate) for candidate in matches]
            self._remember_choice(event, "item", query, candidates)
            text = format_item_candidates(query, candidates)
            if len(candidates) <= 1:
                return text
            return PluginReply(
                text,
                candidate_view=build_item_candidate_view(query, candidates),
                sub="candidates",
            )
        return "未找到相关数据，请检查物品 ID / 物品名是否正确。"

    async def _handle_pass(self, argument: str) -> str | PluginReply:
        try:
            level, daily_tasks, overloads, remaining_days, weekly_days = (
                parse_arguments(argument)
            )
            result = calculate(
                level,
                daily_tasks,
                overloads,
                remaining_days,
                weekly_days,
            )
        except SeasonPassError as exc:
            return str(exc)
        return PluginReply(format_season_pass(result))

    async def _handle_balance(
        self, query: str, *, event: Any = None
    ) -> str | PluginReply:
        if not self.balance_history.ready:
            return "平衡调整历史索引未加载，请联系管理员更新 balance_history.json。"
        item, matches = await asyncio.to_thread(self._resolve_item, query)
        if not item:
            if matches:
                candidates = [self._decorate(candidate) for candidate in matches]
                self._remember_choice(event, "balance", query, candidates)
                text = format_item_candidates(query, candidates)
                if len(candidates) <= 1:
                    return text
                return PluginReply(
                    text,
                    candidate_view=build_item_candidate_view(query, candidates),
                    sub="candidates",
                )
            return (
                f"物品「{query}」不存在，无法查询平衡调整。\n"
                "请用 /sz item <中文名/英文名/ID> 确认物品名，"
                "或直接提供物品 ID。"
            )
        names = [
            str(item.get("en") or ""),
            display_translation(item),
            str(item.get("ru") or ""),
            str(item.get("id") or ""),
        ]
        def search_and_format() -> str:
            result = self.balance_history.search(names)
            return format_balance_history(display_name(item), result)

        text = await asyncio.to_thread(search_and_format)
        return PluginReply(text, icon_url=item.get("icon"))

    async def _handle_clan(
        self, query: str, *, event: Any = None
    ) -> str | PluginReply:
        value = query.strip()
        async with self._make_client() as client:
            if UUID_RE.match(value):
                clan = await client.get_clan(value)
                return PluginReply(
                    format_clan(clan, client.region),
                    faction=str(clan.get("alliance") or ""),
                    sub="clan",
                )

            q = value.casefold()
            q_tag = q.strip("[]# ")
            tag_only = bool(re.fullmatch(r"[a-z]{4}", q_tag))
            exact: list[dict[str, Any]] = []
            partial: list[dict[str, Any]] = []
            seen: set[str] = set()
            offset = 0
            total: int | None = None
            # /clans only supports pagination, not name search. Scan a bounded
            # number of pages to keep latency predictable (max 600 clans).
            for _ in range(3):
                payload = await client.list_clans(limit=200, offset=offset)
                data = payload.get("data")
                page = [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []
                if total is None:
                    raw_total = payload.get("totalClans")
                    total = raw_total if isinstance(raw_total, int) else None
                for clan in page:
                    clan_id = str(clan.get("id") or "")
                    if clan_id and clan_id in seen:
                        continue
                    if clan_id:
                        seen.add(clan_id)
                    name = str(clan.get("name") or "").casefold()
                    tag = str(clan.get("tag") or "").casefold()
                    if tag_only:
                        if tag == q_tag:
                            exact.append(clan)
                        continue
                    if q == name or q_tag == tag or q == f"{name} [{tag}]".casefold():
                        exact.append(clan)
                    elif q in name or (q_tag and q_tag in tag):
                        partial.append(clan)
                if total is not None and offset + len(page) >= total:
                    break
                if len(page) < 200:
                    break
                offset += 200

            matches = exact if tag_only else (exact or partial)
            if not matches:
                if tag_only:
                    return f"没有找到标签 [{q_tag.upper()}] 的战队。"
                return "未找到相关数据，请检查战队名/标签/ID 是否正确。"
            if len(matches) == 1:
                clan = matches[0]
                return PluginReply(
                    format_clan(clan, client.region),
                    faction=str(clan.get("alliance") or ""),
                    sub="clan",
                )
            candidates = matches[:20]
            self._remember_choice(event, "clan", query, candidates)
            text = format_clan_candidates(query, candidates)
            if len(candidates) <= 1:
                return text
            return PluginReply(
                text,
                candidate_view=build_clan_candidate_view(query, candidates),
                sub="candidates",
            )

    async def _handle_clans(self, page_arg: str) -> str:
        try:
            page = int(page_arg) if page_arg.strip() else 1
        except ValueError:
            return USAGE["clans"]
        if page < 1:
            return USAGE["clans"]
        async with self._make_client() as client:
            payload = await client.list_clans(limit=10, offset=(page - 1) * 10)
            return format_clans_list(payload, page)

    async def _handle_regions(self) -> str:
        async with self._make_client() as client:
            return format_regions(await client.get_regions())

    async def _handle_operations(self, map_arg: str) -> str:
        map_name = map_arg.strip() or None
        async with self._make_client() as client:
            payload = await client.get_operations(map_name=map_name, limit=10)
            return format_operations(payload, map_name)

    async def terminate(self):
        """Plugin unload hook; per-request clients close themselves."""
