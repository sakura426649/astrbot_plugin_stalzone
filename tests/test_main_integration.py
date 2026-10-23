"""Smoke tests for main.py with a tiny AstrBot stub (no AstrBot install)."""

from __future__ import annotations

import re
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

# Build minimal astrbot modules before importing main.py.
astrbot = types.ModuleType("astrbot")
api = types.ModuleType("astrbot.api")
event_mod = types.ModuleType("astrbot.api.event")
star_mod = types.ModuleType("astrbot.api.star")


class _Filter:
    @staticmethod
    def command(_name):
        return lambda func: func

    @staticmethod
    def regex(_pattern):
        return lambda func: func


class AstrMessageEvent:  # minimal type for annotations
    pass


class Context:
    pass


class Star:
    def __init__(self, context):
        self.context = context


api.logger = types.SimpleNamespace(
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
    exception=lambda *args, **kwargs: None,
)
event_mod.filter = _Filter()
event_mod.AstrMessageEvent = AstrMessageEvent
star_mod.Context = Context
star_mod.Star = Star
sys.modules["astrbot"] = astrbot
sys.modules["astrbot.api"] = api
sys.modules["astrbot.api.event"] = event_mod
sys.modules["astrbot.api.star"] = star_mod
astrbot.api = api
astrbot.api.event = event_mod
astrbot.api.star = star_mod

from main import (  # noqa: E402
    PluginReply,
    SZ_BARE_RE,
    StalzonePlugin,
    _looks_like_image,
)


class FakeEvent:
    def __init__(self, text: str):
        self.message_str = text

    @staticmethod
    def plain_result(text: str):
        return ("plain", text)


async def collect(plugin: StalzonePlugin, text: str) -> str:
    results = []
    async for item in plugin.sz(FakeEvent(text)):
        results.append(item[1])
    return "\n".join(results)


class FakeClient:
    region = "eu"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get_auction_lots(self, item_id, limit=50):
        return {
            "total": 1,
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 100,
                    "buyoutPrice": 10000,
                    "endTime": "2026-10-22T15:00:00Z",
                    "additional": {},
                }
            ],
        }

    async def get_auction_history(self, item_id, limit=20, offset=0):
        return {
            "total": 1,
            "prices": [
                {
                    "amount": 1,
                    "price": 1000,
                    "time": "2026-10-22T05:00:00Z",
                    "additional": {"qlt": 3},
                }
            ],
        }

    async def get_emission(self):
        return {"previousStart": "2026-10-22T03:00:00Z", "previousEnd": "2026-10-22T03:30:00Z"}

    async def get_profile(self, name, *, region=None):
        alliance = "freedom" if (region or self.region) == "ru" else "duty"
        return {"username": name, "status": "online", "alliance": alliance, "stats": []}

    async def get_profile_by_uuid(self, uuid, *, region=None):
        alliance = "freedom" if (region or self.region) == "ru" else "duty"
        return {"username": uuid, "status": "online", "alliance": alliance, "stats": []}

    async def get_regions(self):
        return [{"id": "EU", "name": "EUROPE"}]

    async def list_clans(self, limit=100, offset=0):
        return {
            "totalClans": 1,
            "data": [
                {
                    "id": "647d6c53-b3d7-4d30-8d08-de874eb1d845",
                    "name": "Clan #1",
                    "tag": "TAG",
                    "level": 2,
                    "levelPoints": 100,
                    "alliance": "covenant",
                    "memberCount": 1,
                    "leader": "Test-1",
                }
            ],
        }

    async def get_clan(self, clan_id):
        return (await self.list_clans())["data"][0]

    async def get_operations(self, map_name=None, limit=10):
        return {
            "total": 1,
            "sessions": [
                {
                    "map": map_name or "operation_bigcleanup",
                    "difficulty": 3,
                    "sessionDurationSeconds": 1200,
                    "endTime": "2026-10-22T05:00:00Z",
                    "participants": [{"username": "A"}],
                }
            ],
        }


class EmptyClient(FakeClient):
    async def get_auction_lots(self, item_id, limit=100):
        return {"total": 0, "lots": []}

    async def get_auction_history(self, item_id, limit=100, offset=0):
        return {"total": 0, "prices": []}


class TagClient(FakeClient):
    async def list_clans(self, limit=100, offset=0):
        payload = await super().list_clans(limit=limit, offset=offset)
        payload["data"][0]["tag"] = "RSHT"
        return payload


class MainSmokeTests(unittest.IsolatedAsyncioTestCase):
    def make_plugin(self):
        return StalzonePlugin(
            Context(),
            {
                "region": "eu",
                "api_base": "https://dapi.stalzone.com",
                "render_mode": "text",
                "lunar_enrich": False,
                "sc_core_fallback": False,
                "command_cooldown": 0,
            },
        )

    async def test_help(self):
        text = await collect(self.make_plugin(), "/sz help")
        self.assertIn("STALZONE · 查询帮助", text)
        self.assertIn("/sz auction", text)

    async def test_help_image_is_cached(self):
        from PIL import Image

        plugin = self.make_plugin()
        first = await plugin._help_image()
        if first is None:
            self.skipTest("Pillow or CJK font unavailable")
        second = await plugin._help_image()
        self.assertEqual(first, second)
        self.assertTrue(first.exists())
        with Image.open(first) as image:
            self.assertEqual(image.size, (1600, 1100))

    async def test_usage_without_argument(self):
        text = await collect(self.make_plugin(), "/sz auction")
        self.assertIn("用法", text)

    async def test_missing_credentials_is_friendly(self):
        text = await collect(self.make_plugin(), "/sz emission")
        self.assertIn("未配置", text)

    async def test_bare_sz_triggers_without_slash(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        results = []
        async for item in plugin.sz_bare(FakeEvent("sz 拍卖 y1q9")):
            results.append(item[1])
        text = "\n".join(results)
        self.assertIn("在售", text)
        self.assertIn("最近成交", text)

        event = FakeEvent("SZ 拍卖 y1q9")
        first = []
        async for item in plugin.sz_bare(event):
            first.append(item[1])
        second = []
        async for item in plugin.sz(event):
            second.append(item[1])
        self.assertTrue(first)
        self.assertEqual(second, [])

    def test_bare_sz_requires_trailing_space(self):
        self.assertIsNone(re.match(SZ_BARE_RE, "sz"))
        self.assertIsNone(re.match(SZ_BARE_RE, "szabc"))
        self.assertIsNotNone(re.match(SZ_BARE_RE, "sz 拍卖 原子"))
        self.assertIsNotNone(re.match(SZ_BARE_RE, "SZ help"))
        self.assertIsNotNone(re.match(SZ_BARE_RE, "stalzone 拍卖"))

    async def test_auction_success(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz 拍卖 y1q9")
        self.assertIn("在售", text)
        self.assertIn("最近成交", text)
        self.assertIn("1,000", text)

    async def test_auction_date_history_only(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz 拍卖 原子 粉 26.10.22 20")
        self.assertIn("历史成交", text)
        self.assertNotIn("在售", text)
        self.assertIn("截至 2026/10/22", text)
        self.assertIn("最多 20 条", text)
        self.assertIn("1,000", text)

    async def test_auction_count_without_quality_is_rejected(self):
        text = await collect(self.make_plugin(), "/sz 拍卖 原子 26.10.22 20")
        self.assertIn("需要同时指定品质和时间", text)

    async def test_dated_history_walks_200_at_a_time(self):
        class PagedClient:
            region = "eu"

            def __init__(self, prices):
                self.prices = prices
                self.offsets = []

            async def get_auction_history(self, item_id, limit=20, offset=0):
                self.offsets.append(offset)
                return {
                    "total": len(self.prices),
                    "prices": self.prices[offset : offset + limit],
                }

        base = datetime(2026, 10, 22, tzinfo=timezone.utc)
        prices = [
            {
                "amount": 1,
                "price": 100000 + index,
                "time": (base - timedelta(hours=index)).isoformat().replace(
                    "+00:00", "Z"
                ),
                "additional": {"qlt": 3 if index % 2 == 0 else 0},
            }
            for index in range(1200)
        ]
        before = datetime(2026, 9, 15, 23, 59, 59, tzinfo=timezone.utc)
        client = PagedClient(prices)
        payload, errors = await self.make_plugin()._fetch_dated_history(
            client,
            "wg53",
            before=before,
            quality_filter=3,
            limit=20,
        )
        self.assertEqual(errors, [])
        matching = [
            entry
            for entry in payload["prices"]
            if entry["additional"]["qlt"] == 3
        ]
        self.assertGreaterEqual(len(matching), 20)
        for entry in payload["prices"]:
            timestamp = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
            self.assertLessEqual(timestamp, before)
        self.assertEqual(
            client.offsets,
            [200 * index for index in range(len(client.offsets))],
        )
        self.assertGreater(len(client.offsets), 1)

    async def test_normal_auction_uses_small_limits(self):
        class RecordingClient(FakeClient):
            def __init__(self):
                self.calls = []

            async def get_auction_lots(self, item_id, limit=50):
                self.calls.append(("lots", limit))
                return await super().get_auction_lots(item_id, limit=limit)

            async def get_auction_history(self, item_id, limit=20, offset=0):
                self.calls.append(("history", limit, offset))
                return await super().get_auction_history(
                    item_id, limit=limit, offset=offset
                )

        client = RecordingClient()
        plugin = self.make_plugin()
        plugin._make_client = lambda: client  # type: ignore[assignment]
        await collect(plugin, "/sz 拍卖 y1q9")
        self.assertIn(("lots", 100), client.calls)
        self.assertIn(("history", 100, 0), client.calls)

        dated = RecordingClient()
        plugin._make_client = lambda: dated  # type: ignore[assignment]
        await collect(plugin, "/sz 拍卖 原子 粉 26.10.22 20")
        self.assertIn(("history", 200, 0), dated.calls)
        self.assertNotIn(("lots", 100), dated.calls)

    async def test_season_pass_calculator(self):
        text = await collect(self.make_plugin(), "/sz 通行证 15 15+2 20")
        self.assertIn("STALZONE · 通行证计算", text)
        self.assertIn("每日经验（含超载）：6,000", text)
        self.assertIn("每周任务数：105", text)
        self.assertIn("整个赛季总经验（含超载）：168,000", text)
        self.assertIn("15 → 183", text)

        alias = await collect(
            self.make_plugin(), "/sz 通行证等级预测 15 15+2 20"
        )
        self.assertIn("STALZONE · 通行证计算", alias)

        four_params = await collect(
            self.make_plugin(), "/sz 通行证 15 15 3 20"
        )
        self.assertIn("每日 15 任务 +3 超载", four_params)
        self.assertIn("使用超载：15 → 188", four_params)

        no_overload = await collect(self.make_plugin(), "/sz 通行证 15 15 20")
        self.assertIn("不用超载：", no_overload)
        self.assertNotIn("使用超载：", no_overload)

    async def test_season_pass_usage(self):
        text = await collect(self.make_plugin(), "/sz 通行证")
        self.assertIn("用法", text)

    async def test_balance_weapon_history(self):
        text = await collect(self.make_plugin(), "/sz 调整 AK-308")
        self.assertIn("平衡调整", text)
        self.assertIn("2026-07-22", text)
        self.assertIn("39.8 → 39.1", text)

    async def test_balance_full_name_and_short_name_match_same_weapon(self):
        full = await collect(
            self.make_plugin(), "/sz 调整 FN IWI Tavor X95"
        )
        short = await collect(self.make_plugin(), "/sz 调整 x95")
        for text in (full, short):
            self.assertIn("IWI Tavor X95", text)
            self.assertIn("2026-09-02", text)
            self.assertIn("2026-03-04", text)
            self.assertIn("最低伤害", text)

    async def test_balance_missing_item_is_not_history_miss(self):
        text = await collect(
            self.make_plugin(), "/sz 调整 不存在武器xyz"
        )
        self.assertIn("不存在", text)
        self.assertIn("物品", text)
        self.assertNotIn("没有找到该物品的平衡调整记录", text)

    async def test_balance_artifact_history(self):
        text = await collect(self.make_plugin(), "/sz 调整 多面体")
        self.assertIn("Polyhedron", text)
        self.assertIn("2026-07-22", text)

    async def test_balance_artifact_historical_patchnotes(self):
        text = await collect(self.make_plugin(), "/sz 调整 螺旋")
        for date in (
            "2026-06-03",
            "2026-01-14",
            "2025-11-12",
            "2025-09-03",
            "2023-12-20",
            "2023-10-11",
        ):
            self.assertIn(date, text)
        self.assertIn("治疗效率", text)
        self.assertIn("7.2% → 6.1%", text)
        self.assertIn("移动速度", text)
        self.assertIn("稳定性", text)
        self.assertNotIn("too powerful", text)

    async def test_balance_without_history(self):
        text = await collect(self.make_plugin(), "/sz 调整 猎人套装")
        self.assertIn("STALZONE · 平衡调整", text)
        self.assertIn("没有找到该物品的平衡调整记录", text)
        self.assertIn("猎人套装", text)

    async def test_item_chinese(self):
        text = await collect(self.make_plugin(), "/sz item 寒冰")
        self.assertIn("寒冰 / Chilly", text)
        self.assertIn("ljn2", text)

    async def test_auction_premium_chinese_name(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz 拍卖 高级账户 180天")
        self.assertIn("高级账户 180天", text)
        self.assertIn("7l9d3", text)

    async def test_dated_history_stops_on_repeated_pages(self):
        class RepeatingClient:
            region = "eu"

            def __init__(self, prices):
                self.prices = prices
                self.calls = 0

            async def get_auction_history(self, item_id, limit=20, offset=0):
                self.calls += 1
                return {"total": 4000, "prices": self.prices}

        prices = [
            {
                "amount": 1,
                "price": 1000 + index,
                "time": "2026-10-22T05:00:00Z",
                "additional": {"qlt": 3},
            }
            for index in range(200)
        ]
        client = RepeatingClient(prices)
        before = datetime(2026, 1, 1, tzinfo=timezone.utc)
        payload, errors = await self.make_plugin()._fetch_dated_history(
            client,
            "wg53",
            before=before,
            quality_filter=3,
            limit=20,
        )
        self.assertEqual(errors, [])
        self.assertEqual(client.calls, 3)
        self.assertEqual(payload["scanned"], 600)
        self.assertTrue(payload["repeated_page"])
        self.assertEqual(payload["prices"], [])

    async def test_sc_core_fallback_fills_old_history(self):
        plugin = self.make_plugin()
        plugin.config["sc_core_fallback"] = True
        plugin._make_client = lambda: EmptyClient()  # type: ignore[assignment]

        async def fake_sc_history(*args, **kwargs):
            return {
                "prices": [
                    {
                        "time": "2026-06-10T10:00:00Z",
                        "price": 12345,
                        "amount": 1,
                        "additional": {"qlt": 3},
                    }
                ],
                "source": "sc_core",
                "window_exhausted": False,
            }, []

        plugin._fetch_sc_core_history = fake_sc_history  # type: ignore[assignment]
        text = await collect(plugin, "/sz 拍卖 原子 粉 6.11")
        self.assertIn("历史成交", text)
        self.assertIn("12,345", text)
        self.assertIn("SC CORE", text)

    async def test_auction_no_data_includes_item_name(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: EmptyClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz 拍卖 原子")
        self.assertIn("未查到关于「原子」的成交记录", text)
        self.assertNotIn("稀有", text)

        dated = await collect(plugin, "/sz 拍卖 原子 6.11")
        self.assertIn("截至 2026/6/11 未查到关于「原子」的成交记录", dated)

    async def test_premium_synonym_suggests_candidates(self):
        auction = await collect(self.make_plugin(), "/sz 拍卖 高级会员")
        self.assertIn("没有精确匹配「高级会员」", auction)
        self.assertIn("高级账户", auction)

        item = await collect(self.make_plugin(), "/sz 物品 高级会员")
        self.assertIn("没有精确匹配「高级会员」", item)
        self.assertIn("高级账户", item)

    async def test_short_item_query_suggests_candidates(self):
        text = await collect(self.make_plugin(), "/sz 市场 原")
        self.assertIn("没有精确匹配「原」", text)
        self.assertIn("原子", text)
        self.assertIn("sz 候选", text)

    async def test_candidate_list_builds_image_view(self):
        plugin = self.make_plugin()
        result = await plugin._handle_item("AK", event=FakeEvent("/sz 物品 AK"))
        self.assertIsInstance(result, PluginReply)
        view = result.candidate_view
        self.assertIsNotNone(view)
        self.assertGreater(len(view["entries"]), 1)
        self.assertEqual(view["entries"][0]["index"], 1)
        self.assertEqual(result.sub, "candidates")

    async def test_candidate_selection_replays_auction(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        first = await collect(plugin, "/sz 拍卖 原 粉")
        self.assertIn("没有精确匹配「原」", first)
        self.assertIn("sz 候选 <序号>", first)

        result = await collect(plugin, "/sz 候选 1")
        self.assertIn("STALZONE · 拍卖行", result)
        self.assertIn("原子", result)
        self.assertIn("仅看品质：稀有", result)

        # The pending list is consumed after a successful selection.
        again = await collect(plugin, "/sz 候选 1")
        self.assertIn("没有待选择的候选", again)

    async def test_candidate_selection_replays_item(self):
        plugin = self.make_plugin()
        first = await collect(plugin, "/sz 物品 原")
        self.assertIn("没有精确匹配「原」", first)
        result = await collect(plugin, "/sz 候选 1")
        self.assertIn("STALZONE · 物品", result)
        self.assertIn("ID：wg53", result)

    async def test_candidate_invalid_index_keeps_pending(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        await collect(plugin, "/sz 拍卖 原 粉")
        invalid = await collect(plugin, "/sz 候选 99")
        self.assertIn("序号超出范围", invalid)
        result = await collect(plugin, "/sz 候选 1")
        self.assertIn("STALZONE · 拍卖行", result)

    async def test_candidate_selection_replays_clan(self):
        class MultiClanClient(FakeClient):
            async def list_clans(self, limit=100, offset=0):
                return {
                    "totalClans": 2,
                    "data": [
                        {
                            "id": "c1",
                            "name": "Clan #1",
                            "tag": "TAG1",
                            "level": 1,
                            "levelPoints": 1,
                            "alliance": "duty",
                            "memberCount": 1,
                            "leader": "A",
                        },
                        {
                            "id": "c2",
                            "name": "Clan #2",
                            "tag": "TAG2",
                            "level": 2,
                            "levelPoints": 2,
                            "alliance": "freedom",
                            "memberCount": 2,
                            "leader": "B",
                        },
                    ],
                }

        plugin = self.make_plugin()
        plugin._make_client = lambda: MultiClanClient()  # type: ignore[assignment]
        first = await collect(plugin, "/sz 战队 Cla")
        self.assertIn("STALZONE · 战队候选", first)
        self.assertIn("sz 候选", first)
        result = await collect(plugin, "/sz 候选 2")
        self.assertIn("Clan #2 [TAG2]", result)
        self.assertIn("ID：c2", result)

    async def test_auction_bilingual_name(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz auction 寒冰")
        self.assertIn("寒冰 / Chilly", text)
        self.assertIn("ljn2", text)

    async def test_regions(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz regions")
        self.assertIn("EU — EUROPE", text)

    async def test_clans_list(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz clans")
        self.assertIn("Clan #1 [TAG]", text)

    async def test_clan_search(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz clan Clan #1")
        self.assertIn("Clan #1 [TAG]", text)
        self.assertIn("User token", text)

    async def test_clan_four_letter_tag(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: TagClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz 战队 [rsht]")
        self.assertIn("[RSHT]", text)

        # Four letters are always treated as a tag, never a name substring.
        text = await collect(plugin, "/sz 战队 clan")
        self.assertIn("没有找到标签 [clan]", text)

    async def test_operations(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz operations operation_bigcleanup")
        self.assertIn("行动记录", text)
        self.assertIn("operation_bigcleanup", text)

    async def test_player_region_override(self):
        class RegionClient(FakeClient):
            last_region = ""

            def __init__(self, region):
                self.region = region
                RegionClient.last_region = region

        plugin = self.make_plugin()
        plugin._make_client = lambda region=None: RegionClient(region or "eu")  # type: ignore[assignment]
        text = await collect(plugin, "/sz 玩家 aaa Ru")
        self.assertIn("aaa｜RU", text)
        self.assertIn("阵营：自由", text)
        self.assertEqual(RegionClient.last_region, "ru")

        text = await collect(plugin, "/sz 玩家 bbb")
        self.assertIn("bbb｜EU", text)
        self.assertIn("阵营：纪律", text)
        self.assertEqual(RegionClient.last_region, "eu")

    async def test_missing_item_returns_notice_card(self):
        plugin = self.make_plugin()
        result = await plugin._handle_item("qqqzzzxxx999")
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "notice")
        self.assertIn("未查到关于「qqqzzzxxx999」的物品信息", result.text)
        self.assertEqual(result.notice_view["kind_label"], "物品")
        self.assertEqual(result.notice_view["query"], "qqqzzzxxx999")

    def test_notice_query_casing_preserves_input(self):
        plugin = self.make_plugin()
        upper = plugin._not_found("player", "SAKURA_AKIRA")
        self.assertEqual(upper.notice_view["query"], "sakura_akira")
        mixed = plugin._not_found("player", "Sakura_Akira")
        self.assertEqual(mixed.notice_view["query"], "Sakura_Akira")
        self.assertIn("Sakura_Akira", mixed.text)

    async def test_missing_player_returns_notice_card(self):
        from api_client import NotFoundError

        class MissingProfileClient(FakeClient):
            async def get_profile(self, name, *, region=None):
                raise NotFoundError("HTTP 404", status_code=404)

        plugin = self.make_plugin()
        plugin._make_client = lambda region=None: MissingProfileClient()  # type: ignore[assignment]
        result = await plugin._handle_profile("Nobody RU")
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "notice")
        self.assertIn("未查到关于「Nobody」的玩家信息", result.text)
        self.assertEqual(result.notice_view["region"], "RU")
        self.assertIn("RU 区服", result.notice_view["note"])

    def test_icon_library_covers_catalog(self):
        icons = list((PLUGIN_ROOT / "item_icons").glob("*.png"))
        self.assertGreaterEqual(len(icons), 2600)

    def test_notice_card_renders_query(self):
        from image_renderer import find_cjk_font, render_notice_card

        if not find_cjk_font():
            self.skipTest("CJK font unavailable")
        path = render_notice_card(
            {
                "title": "STALZONE · 查询结果",
                "kind_label": "玩家",
                "query": "Nobody",
                "region": "RU",
                "now": "2026-10-23 20:00",
                "note": "请检查角色名拼写与区服。",
            }
        )
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        path.unlink(missing_ok=True)

    async def test_notice_card_routes_through_plugin(self):
        plugin = self.make_plugin()
        plugin.config["render_mode"] = "image"
        result = await plugin._handle_item("qqqzzzxxx999")
        self.assertIsInstance(result, PluginReply)
        path = await plugin._render_image(
            result.text,
            result.sub or "",
            notice_view=result.notice_view,
        )
        if path is None:
            self.skipTest("Pillow or CJK font unavailable")
        self.assertTrue(path.exists())
        path.unlink(missing_ok=True)

    async def test_shared_http_client_reused(self):
        plugin = self.make_plugin()
        plugin.config.update({"client_id": "id", "client_secret": "secret"})
        first = plugin._make_client()
        second = plugin._make_client()
        self.assertIs(first._client, second._client)
        await plugin.terminate()

    async def test_emission_region_override(self):
        class EmissionRegionClient(FakeClient):
            last_region = ""

            def __init__(self, region):
                self.region = region
                EmissionRegionClient.last_region = region

        plugin = self.make_plugin()
        plugin._make_client = lambda region=None: EmissionRegionClient(region or "eu")  # type: ignore[assignment]
        text = await collect(plugin, "/sz 风暴 RU")
        self.assertIn("RU｜", text)
        self.assertIn("距离上次风暴", text)
        self.assertEqual(EmissionRegionClient.last_region, "ru")

        await collect(plugin, "/sz 风暴")
        self.assertEqual(EmissionRegionClient.last_region, "eu")

        usage = await collect(plugin, "/sz 风暴 xx")
        self.assertIn("用法：/sz emission", usage)

    async def test_emission_cache_hits(self):
        class CountingClient(FakeClient):
            calls = 0

            async def get_emission(self):
                CountingClient.calls += 1
                return {
                    "previousStart": "2026-10-22T03:00:00Z",
                    "previousEnd": "2026-10-22T03:30:00Z",
                }

        plugin = self.make_plugin()
        plugin._make_client = lambda: CountingClient()  # type: ignore[assignment]
        first = await collect(plugin, "/sz 风暴")
        second = await collect(plugin, "/sz 风暴")
        self.assertIn("距离上次风暴", first)
        self.assertIn("距离上次风暴", second)
        self.assertEqual(CountingClient.calls, 1)
        self.assertEqual(plugin._cache_stats()[1], 1)

    async def test_group_cooldown(self):
        plugin = self.make_plugin()
        plugin.config["command_cooldown"] = 2.0
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        first = await collect(plugin, "/sz 区服")
        second = await collect(plugin, "/sz 区服")
        self.assertIn("EU", first)
        self.assertIn("查询太频繁", second)

    async def test_762_candidates_have_bundled_icons(self):
        plugin = self.make_plugin()
        result = await plugin._handle_item("7.62", event=FakeEvent("/sz 物品 7.62"))
        self.assertIsInstance(result, PluginReply)
        await plugin._attach_candidate_icons(result.candidate_view)
        entries = result.candidate_view["entries"]
        self.assertTrue(entries)
        self.assertTrue(all(entry.get("icon_path") for entry in entries))
        self.assertTrue(_looks_like_image(bytes([0x89, 80, 78, 71, 13, 10, 26, 10])))
        self.assertFalse(_looks_like_image(b"<html>not an image</html>"))

    async def test_diag_command(self):
        text = await collect(self.make_plugin(), "/sz diag")
        self.assertIn("STALZONE · 运行诊断", text)
        self.assertIn("插件 ", text)
        self.assertIn("凭证：未配置", text)
        self.assertIn("API 缓存", text)

    async def test_player_command(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz player Sakura")
        self.assertIn("Sakura", text)
        self.assertIn("角色资料", text)

    async def test_item_atom_details(self):
        text = await collect(self.make_plugin(), "/sz item 原子")
        self.assertIn("原子", text)
        self.assertIn("生命：", text)
        self.assertIn("玻尔原子模型", text)

    async def test_unknown_command(self):
        text = await collect(self.make_plugin(), "/sz nope")
        self.assertIn("未知指令", text)


if __name__ == "__main__":
    unittest.main()
