"""Smoke tests for main.py with a tiny AstrBot stub (no AstrBot install)."""

from __future__ import annotations

import os
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
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
    debug=lambda *args, **kwargs: None,
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
    error=lambda *args, **kwargs: None,
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

import main as main_module  # noqa: E402
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


class ParenthesizedClanClient(FakeClient):
    async def list_clans(self, limit=100, offset=0):
        return {
            "totalClans": 2,
            "data": [
                {
                    "id": "p1",
                    "name": "Alpha (LONG)",
                    "tag": "FIELD1",
                    "level": 1,
                    "levelPoints": 1,
                    "alliance": "duty",
                    "memberCount": 1,
                    "leader": "A",
                },
                {
                    "id": "p2",
                    "name": "Beta",
                    "tag": "LONG",
                    "level": 1,
                    "levelPoints": 1,
                    "alliance": "freedom",
                    "memberCount": 1,
                    "leader": "B",
                },
            ],
        }


class CountingClanClient(FakeClient):
    def __init__(self):
        self.calls = []
        self.clans = [
            {
                "id": f"c{index}",
                "name": f"Clan {index}",
                "tag": f"T{index:03d}",
                "level": 1,
                "levelPoints": 1,
                "alliance": "duty",
                "memberCount": 1,
                "leader": "A",
            }
            for index in range(401)
        ]

    async def list_clans(self, limit=100, offset=0):
        self.calls.append((limit, offset))
        page = self.clans[offset : offset + limit]
        return {"totalClans": len(self.clans), "data": page}


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
        async for item in plugin.sz_bare(FakeEvent("sz 拍卖 wg53")):
            results.append(item[1])
        text = "\n".join(results)
        self.assertIn("在售", text)
        self.assertIn("最近成交", text)

        event = FakeEvent("SZ 拍卖 wg53")
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
        text = await collect(plugin, "/sz 拍卖 wg53")
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
        await collect(plugin, "/sz 拍卖 wg53")
        self.assertIn(("lots", 100), client.calls)
        self.assertIn(("history", 100, 0), client.calls)

        dated = RecordingClient()
        plugin._make_client = lambda: dated  # type: ignore[assignment]
        await collect(plugin, "/sz 拍卖 原子 粉 26.10.22 20")
        self.assertIn(("history", 200, 0), dated.calls)
        self.assertNotIn(("lots", 100), dated.calls)

    async def test_update_command_dispatches_to_updater(self):
        plugin = self.make_plugin()
        called = []

        async def fake_update(event):
            called.append(event)
            return "updater-called"

        plugin._handle_self_update = fake_update  # type: ignore[assignment]
        text = await collect(plugin, "/sz 更新")
        self.assertIn("updater-called", text)
        self.assertEqual(len(called), 1)

    async def test_alert_whitelist_commands_share_config(self):
        class AdminEvent(FakeEvent):
            role = "admin"

            def is_admin(self):
                return True

        plugin = self.make_plugin()
        plugin.config["emission_group_blacklist"] = ["111"]
        added = await plugin._handle_alert_setting("白名单 111", AdminEvent(""))
        self.assertIn("已加入", added)
        self.assertEqual(plugin.config["emission_group_whitelist"], ["111"])
        self.assertEqual(plugin.config["emission_group_blacklist"], [])
        removed = await plugin._handle_alert_setting("黑名单 111", AdminEvent(""))
        self.assertIn("移除", removed)
        self.assertEqual(plugin.config["emission_group_whitelist"], [])
        readded = await plugin._handle_alert_setting("白名单 111", AdminEvent(""))
        self.assertIn("已加入", readded)
        self.assertEqual(plugin.config["emission_group_whitelist"], ["111"])

    async def test_region_and_auction_mode_commands(self):
        plugin = self.make_plugin()
        self.assertIn("EU", plugin._handle_set_region("eu"))
        self.assertEqual(plugin.config["region"], "eu")
        self.assertIn("全部显示", plugin._handle_auction_mode("1"))
        self.assertEqual(plugin.config["auction_display_mode"], "full")
        self.assertIn("聚合显示", plugin._handle_auction_mode("聚合"))
        self.assertEqual(plugin.config["auction_display_mode"], "aggregate")
        self.assertIn("只能", plugin._handle_set_region("地心"))

    def test_group_owner_and_admin_are_privileged(self):
        class RawEvent:
            role = "member"

            def is_admin(self):
                return False

            def __init__(self, role):
                self.message_obj = types.SimpleNamespace(
                    raw_message={"sender": {"role": role}},
                    sender=types.SimpleNamespace(user_id="1"),
                    group=None,
                )

        self.assertTrue(
            StalzonePlugin._event_is_admin(RawEvent("owner"))
        )
        self.assertTrue(
            StalzonePlugin._event_is_admin(RawEvent("admin"))
        )
        self.assertFalse(
            StalzonePlugin._event_is_admin(RawEvent("member"))
        )

    async def test_diag_requires_privilege_and_sz_stops_event(self):
        class MemberEvent(FakeEvent):
            role = "member"

            def is_admin(self):
                return False

            def stop_event(self):
                self.stopped = True

        plugin = self.make_plugin()
        event = MemberEvent("/sz diag")
        results = [item[1] async for item in plugin.sz(event)]
        self.assertIn("仅 AstrBot 管理员", "\n".join(results))
        self.assertTrue(event._has_send_oper)
        self.assertTrue(event.stopped)

    async def test_missing_argument_usage_blocks(self):
        class AdminEvent(FakeEvent):
            role = "admin"

            def is_admin(self):
                return True

        plugin = self.make_plugin()
        for command in (
            "/sz 拍卖",
            "/sz 物品",
            "/sz 玩家",
            "/sz 调整",
            "/sz 通行证计算",
            "/sz 战队",
            "/sz 候选",
        ):
            text = await collect(plugin, command)
            self.assertIn("用法：", text, command)
            self.assertIn("示例：", text, command)
        for command in (
            "/sz 风暴提醒",
            "/sz 默认区服",
            "/sz 拍卖显示模式",
        ):
            results = []
            async for item in plugin.sz(AdminEvent(command)):
                results.append(item[1])
            text = "\n".join(results)
            self.assertIn("用法：", text, command)
            self.assertIn("参数：", text, command)

    async def test_version_check_does_not_update(self):
        plugin = self.make_plugin()

        async def latest():
            return {"tag_name": "v9.9.9", "assets": []}

        plugin._fetch_latest_release = latest  # type: ignore[assignment]
        text = await plugin._handle_version_check()
        self.assertIn(f"v{main_module.PLUGIN_VERSION}", text)
        self.assertIn("v9.9.9", text)
        self.assertIn("可使用 /sz 更新", text)

    async def test_self_update_latest_and_admin_guard(self):
        class AdminEvent(FakeEvent):
            role = "admin"

            def is_admin(self):
                return True

            async def send(self, chain):
                return None

        class MemberEvent(FakeEvent):
            role = "member"

            def is_admin(self):
                return False

        plugin = self.make_plugin()

        async def latest():
            return {"tag_name": f"v{main_module.PLUGIN_VERSION}", "assets": []}

        plugin._fetch_latest_release = latest  # type: ignore[assignment]
        latest_text = await plugin._handle_self_update(AdminEvent("/sz 更新"))
        self.assertIn("已是最新版本", latest_text)
        denied = await plugin._handle_self_update(MemberEvent("/sz 更新"))
        self.assertIn("管理员", denied)

    async def test_self_update_flow_uses_light_package_and_backs_up(self):
        class AdminEvent(FakeEvent):
            role = "admin"

            def is_admin(self):
                return True

            async def send(self, chain):
                return None

        plugin = self.make_plugin()
        calls = []

        async def latest():
            return {
                "tag_name": "v9.9.9",
                "assets": [
                    {
                        "name": main_module.UPDATE_LIGHT_ASSET_NAME,
                        "browser_download_url": "https://example.invalid/light.zip",
                    },
                    {
                        "name": main_module.UPDATE_ASSET_NAME,
                        "browser_download_url": "https://example.invalid/full.zip",
                    },
                ],
            }

        async def index(_tag):
            return {"items": []}

        async def download(_url, destination):
            destination.write_bytes(b"x" * 2048)

        plugin._fetch_latest_release = latest  # type: ignore[assignment]
        plugin._fetch_release_item_index = index  # type: ignore[assignment]
        plugin._download_update_asset = download  # type: ignore[assignment]
        plugin._backup_plugin_dir = lambda root, backup: calls.append(
            ("backup", root, backup)
        )  # type: ignore[assignment]
        plugin._apply_update_zip = lambda *args: calls.append(
            ("apply", *args)
        )  # type: ignore[assignment]
        scheduled = []
        plugin._schedule_plugin_reload = lambda **kwargs: scheduled.append(
            kwargs
        ) or False  # type: ignore[assignment]
        event = AdminEvent("/sz 更新")
        text = await plugin._handle_self_update(event)
        self.assertIn("更新已安装", text)
        self.assertIn("轻量包", text)
        self.assertTrue(any(call[0] == "backup" for call in calls))
        self.assertTrue(any(call[0] == "apply" for call in calls))
        self.assertIs(scheduled[0]["event"], event)
        self.assertIn("热重载完成", scheduled[0]["notify_text"])

    async def test_self_update_package_choice(self):
        plugin = self.make_plugin()
        light, missing, _reason = plugin._choose_update_asset(
            {
                "items": [
                    {"id": "g4v2p", "cat": "weapon/melee"},
                ]
            }
        )
        self.assertFalse(light)
        self.assertEqual(missing, 0)
        known_iconless, known_missing, _reason = plugin._choose_update_asset(
            {
                "items": [
                    {"id": "1rk6g", "cat": "armor/clothes"},
                    {"id": "5lrg1", "cat": "armor/combined"},
                    {"id": "96jyz", "cat": "attachment/accessory"},
                    {"id": "3gp95", "cat": "attachment/mag"},
                ]
            }
        )
        self.assertFalse(known_iconless)
        self.assertEqual(known_missing, 0)
        full, missing, reason = plugin._choose_update_asset(
            {
                "items": [
                    {"id": "not-an-icon", "cat": "weapon/rifle"},
                ]
            }
        )
        self.assertTrue(full)
        self.assertEqual(missing, 1)
        self.assertIn("完整包", reason)
        self.assertEqual(main_module._version_key("v1.5.2"), (1, 5, 2))

    def test_github_proxy_url_candidates(self):
        url = "https://github.com/x/y/releases/download/v1/a.zip"
        self.assertEqual(
            main_module._github_url_candidates(url),
            [
                url,
                "https://gh-proxy.com/" + url,
                "https://v4.gh-proxy.org/" + url,
            ],
        )
        self.assertEqual(
            main_module._github_url_candidates("https://example.com/a.zip"),
            ["https://example.com/a.zip"],
        )

    def test_prune_update_backups_keeps_latest_three(self):
        data_dir = Path(tempfile.mkdtemp())
        root = data_dir / "update_backups"
        root.mkdir()
        for index in range(5):
            path = root / f"1.0.{index}"
            path.mkdir()
            os.utime(path, (index + 1, index + 1))
        StalzonePlugin._prune_update_backups(data_dir)
        self.assertEqual(
            sorted(path.name for path in root.iterdir()),
            ["1.0.2", "1.0.3", "1.0.4"],
        )

    def test_apply_update_zip_installs_and_rolls_back(self):
        import zipfile

        plugin_root = Path(tempfile.mkdtemp()) / "plugin"
        plugin_root.mkdir()
        (plugin_root / "main.py").write_text("OLD", encoding="utf-8")
        (plugin_root / "metadata.yaml").write_text("version: 1.0.0\n", encoding="utf-8")
        backup_root = plugin_root.parent / "backup"
        backup_root.mkdir()
        (backup_root / "main.py").write_text("OLD", encoding="utf-8")
        (backup_root / "metadata.yaml").write_text("version: 1.0.0\n", encoding="utf-8")

        archive_path = plugin_root.parent / "update.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(
                "astrbot_plugin_stalzone/main.py", "NEW"
            )
            archive.writestr(
                "astrbot_plugin_stalzone/metadata.yaml",
                "version: 9.9.9\n",
            )
        StalzonePlugin._apply_update_zip(
            archive_path, plugin_root, backup_root, "v9.9.9"
        )
        self.assertEqual((plugin_root / "main.py").read_text(), "NEW")

        bad_archive = plugin_root.parent / "bad.zip"
        with zipfile.ZipFile(bad_archive, "w") as archive:
            archive.writestr("astrbot_plugin_stalzone/main.py", "BROKEN")
            archive.writestr(
                "astrbot_plugin_stalzone/metadata.yaml", "version: 9.9.9\n"
            )
        with self.assertRaises(main_module.PluginUpdateError):
            StalzonePlugin._apply_update_zip(
                bad_archive, plugin_root, backup_root, "v1.0.0"
            )
        self.assertEqual((plugin_root / "main.py").read_text(), "OLD")

    async def test_auction_full_display_config_wires_through(self):
        plugin = self.make_plugin()
        plugin.config["auction_display_mode"] = "full"
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        result = await plugin._handle_auction("wg53")
        self.assertIsInstance(result, PluginReply)
        self.assertTrue(result.auction_view["full_display"])

    async def test_module_core_recent_uses_per_quality_limit(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        result = await plugin._handle_auction("模块核心")
        self.assertIsInstance(result, PluginReply)
        self.assertTrue(result.auction_view["recent_per_quality"])
        self.assertIsNone(result.auction_view["recent_total_limit"])

    async def test_module_core_quality_filter_shows_ten_history_rows(self):
        class CoreClient(FakeClient):
            async def get_auction_lots(self, item_id, limit=50):
                return {
                    "total": 2,
                    "lots": [
                        {
                            "amount": 1,
                            "startPrice": 100,
                            "buyoutPrice": 1000,
                            "endTime": "2026-10-29T06:00:00Z",
                            "additional": {"qlt": 2},
                        },
                        {
                            "amount": 5,
                            "startPrice": 100,
                            "buyoutPrice": 5000,
                            "endTime": "2026-10-29T06:00:00Z",
                            "additional": {"qlt": 3},
                        },
                    ],
                }

            async def get_auction_history(self, item_id, limit=20, offset=0):
                return {
                    "total": 15,
                    "prices": [
                        {
                            "amount": 1,
                            "price": 1000 + index,
                            "time": f"2026-10-28T{index:02d}:00:00Z",
                            "additional": {"qlt": 2 if index < 12 else 3},
                        }
                        for index in range(15)
                    ],
                }

        plugin = self.make_plugin()
        plugin._make_client = lambda: CoreClient()  # type: ignore[assignment]
        result = await plugin._handle_auction("模块核心 蓝")
        self.assertIsInstance(result, PluginReply)
        view = result.auction_view
        self.assertFalse(view["recent_per_quality"])
        self.assertEqual(view["quality_filter"], 2)
        self.assertIsNone(view["recent_total_limit"])
        self.assertEqual(view["recent_limit"], 10)
        self.assertEqual(len(view["recent_groups"]), 1)
        self.assertEqual(view["recent_groups"][0]["label"], "特殊（蓝）")
        self.assertEqual(len(view["recent_groups"][0]["rows"]), 10)

    async def test_weapon_module_filters_quality_and_affix(self):
        class ModuleClient(FakeClient):
            def __init__(self):
                self.calls = []

            async def get_auction_lots(self, item_id, limit=50):
                self.calls.append(("lots", item_id, limit))
                return {
                    "total": 2,
                    "lots": [
                        {
                            "amount": 1,
                            "startPrice": 100,
                            "buyoutPrice": 900,
                            "endTime": "2026-10-29T06:00:00Z",
                            "additional": {
                                "qlt": 3,
                                "attributes": [
                                    {"definitionId": "hip_spread_pre"},
                                    {"definitionId": "aim_switch_time_suf"},
                                    {"definitionId": "shoot_factor_decrement_aff"},
                                ],
                            },
                        },
                        {
                            "amount": 1,
                            "startPrice": 100,
                            "buyoutPrice": 1200,
                            "endTime": "2026-10-29T06:00:00Z",
                            "additional": {
                                "qlt": 5,
                                "attributes": [
                                    {"definitionId": "recoil_suf"},
                                    {"definitionId": "marksman"},
                                    {"definitionId": "recoil_pre"},
                                ],
                            },
                        },
                    ],
                }

            async def get_auction_history(self, item_id, limit=20, offset=0):
                self.calls.append(("history", item_id, limit, offset))
                return {"total": 0, "prices": []}

        client = ModuleClient()
        plugin = self.make_plugin()
        plugin._make_client = lambda: client  # type: ignore[assignment]
        result = await plugin._handle_auction("武器模块 粉 抑制器")
        self.assertIsInstance(result, PluginReply)
        self.assertIsNotNone(result.auction_view)
        view = result.auction_view
        self.assertTrue(view["module_mode"])
        self.assertEqual(view["quality_filter"], 3)
        self.assertEqual(view["affix_filter"], "抑制器")
        self.assertEqual(len(view["active"]), 1)
        self.assertEqual(view["active"][0]["name"], "稳定 颤抖 抑制器")
        self.assertIn(("lots", "1pyq", 200), client.calls)

    async def test_auction_uses_catalog_id_case(self):
        class RecordingClient(FakeClient):
            calls = []

            async def get_auction_lots(self, item_id, limit=100):
                RecordingClient.calls.append(item_id)
                return {"total": 0, "lots": []}

            async def get_auction_history(self, item_id, limit=100, offset=0):
                RecordingClient.calls.append(item_id)
                return {"total": 0, "prices": []}

        plugin = self.make_plugin()
        plugin._make_client = lambda: RecordingClient()  # type: ignore[assignment]
        result = await plugin._handle_auction("rz6znadw")
        self.assertIsInstance(result, PluginReply)
        self.assertTrue(RecordingClient.calls)
        self.assertTrue(all(item_id == "rz6ZNaDw" for item_id in RecordingClient.calls))

    async def test_non_marketable_auction_item_is_friendly(self):
        from api_client import BadRequestError
        from main import PendingChoice
        import time

        class RejectingAuctionClient(FakeClient):
            async def get_auction_lots(self, item_id, limit=100):
                raise BadRequestError("HTTP 400", status_code=400)

            async def get_auction_history(self, item_id, limit=100, offset=0):
                raise BadRequestError("HTTP 400", status_code=400)

        plugin = self.make_plugin()
        plugin._make_client = lambda: RejectingAuctionClient()  # type: ignore[assignment]
        direct = await plugin._handle_auction("rz6znadw")
        self.assertIsInstance(direct, PluginReply)
        self.assertIsNotNone(direct.auction_view)
        self.assertIn("暂不支持拍卖查询", direct.text)
        self.assertTrue(direct.auction_view["unsupported"])

        item = plugin.item_index.get("rz6ZNaDw")
        self.assertIsNotNone(item)
        event = FakeEvent("/sz 候选 1")
        plugin._pending_choices[plugin._choice_scope(event)] = PendingChoice(
            kind="auction",
            query="rz6znadw",
            candidates=[item],
            created=time.monotonic(),
        )
        replayed = await plugin._handle_candidate("1", event)
        self.assertIsInstance(replayed, PluginReply)
        self.assertEqual(replayed.sub, "auction")
        self.assertIsNotNone(replayed.auction_view)
        self.assertIn("暂不支持拍卖查询", replayed.text)
        self.assertTrue(replayed.auction_view["unsupported"])

    async def test_season_pass_calculator(self):
        text = await collect(self.make_plugin(), "/sz 通行证 15 15+2 20")
        self.assertIn("STALZONE · 通行证计算", text)
        self.assertIn("每日合计：6,000", text)
        self.assertIn("每周任务数：105", text)
        self.assertIn("赛季总经验（含超载）：168,000", text)
        self.assertIn("15 → 183", text)

        alias = await collect(
            self.make_plugin(), "/sz 通行证等级预测 15 15+2 20"
        )
        self.assertIn("STALZONE · 通行证计算", alias)

        four_params = await collect(
            self.make_plugin(), "/sz 通行证 15 15 3 20"
        )
        self.assertIn("超载 3（有效 3）", four_params)
        self.assertIn("使用超载：15 → 188", four_params)

        no_overload = await collect(self.make_plugin(), "/sz 通行证 15 15 20")
        self.assertIn("预测等级：15 → 173 级", no_overload)
        self.assertNotIn("使用超载", no_overload)
        self.assertNotIn("不使用超载", no_overload)
        self.assertNotIn("不用超载", no_overload)

    async def test_season_pass_image_view(self):
        plugin = self.make_plugin()
        result = await plugin._handle_pass("15 15+2 20")
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "pass")
        self.assertTrue(result.pass_view["has_overload"])
        self.assertEqual(result.pass_view["final_with"], 183)
        from image_renderer import find_cjk_font, render_pass_card

        if not find_cjk_font():
            self.skipTest("CJK font unavailable")
        path = render_pass_card(result.pass_view)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        path.unlink(missing_ok=True)

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

    async def test_clan_tag_length_and_parenthesized_priority(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: ParenthesizedClanClient()  # type: ignore[assignment]
        # "LONG" is both a tag in Alpha's name and Beta's tag field; the
        # parenthesized name tag wins.
        text = await collect(plugin, "/sz 战队 [long]")
        self.assertIn("Alpha (LONG) [FIELD1]", text)
        self.assertNotIn("Beta", text)
        # Tags are not restricted to four letters.
        text = await collect(plugin, "/sz 战队 FIELD1")
        self.assertIn("Alpha (LONG) [FIELD1]", text)
        # Without a tag match, fall back to the full name.
        text = await collect(plugin, "/sz 战队 Beta")
        self.assertIn("Beta [LONG]", text)

    async def test_clan_directory_is_cached(self):
        plugin = self.make_plugin()
        client = CountingClanClient()
        plugin._make_client = lambda: client  # type: ignore[assignment]
        await collect(plugin, "/sz 战队 does-not-exist")
        first_calls = len(client.calls)
        self.assertEqual(first_calls, 3)
        await collect(plugin, "/sz 战队 does-not-exist")
        self.assertEqual(len(client.calls), first_calls)

    async def test_clan_not_found_mentions_private_profile(self):
        plugin = self.make_plugin()
        client = CountingClanClient()
        client.clans = []
        plugin._make_client = lambda: client  # type: ignore[assignment]
        text = await collect(plugin, "/sz 战队 unknown")
        self.assertIn("战队名称错误或战队资料未公开", text)

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

        text = await collect(plugin, "/sz 玩家 ccc Nea")
        self.assertIn("ccc｜NEA", text)
        self.assertEqual(RegionClient.last_region, "nea")

    async def test_clan_region_override(self):
        class ClanRegionClient(FakeClient):
            last_region = ""

            def __init__(self, region):
                self.region = region
                ClanRegionClient.last_region = region

        plugin = self.make_plugin()
        plugin._make_client = lambda region=None: ClanRegionClient(region or "eu")  # type: ignore[assignment]
        text = await collect(plugin, "/sz 战队 TAG nea")
        self.assertIn("Clan #1 [TAG]", text)
        self.assertIn("NEA", text)
        self.assertEqual(ClanRegionClient.last_region, "nea")

    async def test_missing_item_returns_notice_card(self):
        plugin = self.make_plugin()
        result = await plugin._handle_item("qqqzzzxxx999")
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "notice")
        self.assertIn("未查到关于「qqqzzzxxx999」的物品信息", result.text)
        self.assertEqual(result.notice_view["kind_label"], "物品")
        self.assertEqual(result.notice_view["query"], "qqqzzzxxx999")
        self.assertEqual(result.notice_view["region"], "全服")

    def test_notice_query_casing_preserves_input(self):
        plugin = self.make_plugin()
        upper = plugin._not_found("player", "SAKURA_AKIRA")
        self.assertEqual(upper.notice_view["query"], "sakura_akira")
        mixed = plugin._not_found("player", "Sakura_Akira")
        self.assertEqual(mixed.notice_view["query"], "Sakura_Akira")
        self.assertIn("Sakura_Akira", mixed.text)

    async def test_missing_auction_item_uses_item_notice(self):
        plugin = self.make_plugin()
        result = await plugin._handle_auction("qqqzzzxxx999")
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "notice")
        self.assertEqual(result.notice_view["kind_label"], "物品")
        self.assertEqual(result.notice_view["region"], "全服")
        self.assertIn("物品库中不存在该物品", result.notice_view["note"])

    async def test_missing_player_returns_notice_card(self):
        from api_client import NotFoundError

        class MissingProfileClient(FakeClient):
            async def get_profile(self, name, *, region=None):
                raise NotFoundError("HTTP 404", status_code=404)

        plugin = self.make_plugin()
        plugin._make_client = lambda region=None: MissingProfileClient()  # type: ignore[assignment]
        result = await plugin._handle_profile("Nobody Nea")
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "notice")
        self.assertIn("未查到关于「Nobody」的玩家信息", result.text)
        self.assertEqual(result.notice_view["region"], "NEA")
        self.assertIn("NEA 区服", result.notice_view["note"])

    def test_base_icon_package_is_slim(self):
        icons = list((PLUGIN_ROOT / "item_icons").glob("*.png"))
        self.assertGreaterEqual(len(icons), 800)
        self.assertLessEqual(len(icons), 900)

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
        class AdminEvent(FakeEvent):
            role = "admin"

            def is_admin(self):
                return True

        plugin = self.make_plugin()
        results = []
        async for item in plugin.sz(AdminEvent("/sz diag")):
            results.append(item[1])
        text = "\n".join(results)
        self.assertIn("STALZONE · 运行诊断", text)
        self.assertIn("插件 ", text)
        self.assertIn("凭证：未配置", text)
        self.assertIn("API 缓存", text)
        alias_results = []
        async for item in plugin.sz(AdminEvent("/sz 状态")):
            alias_results.append(item[1])
        alias = "\n".join(alias_results)
        self.assertIn("STALZONE · 运行诊断", alias)

    async def test_diag_image_view(self):
        plugin = self.make_plugin()
        result = await plugin._handle_diag()
        self.assertIsInstance(result, PluginReply)
        self.assertEqual(result.sub, "diag")
        self.assertIn("groups", result.diag_view)
        self.assertIn("metrics", result.diag_view)
        from image_renderer import find_cjk_font, render_diag_card

        if not find_cjk_font():
            self.skipTest("CJK font unavailable")
        path = render_diag_card(result.diag_view)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        path.unlink(missing_ok=True)

    async def test_player_command(self):
        plugin = self.make_plugin()
        plugin._make_client = lambda: FakeClient()  # type: ignore[assignment]
        text = await collect(plugin, "/sz player Sakura")
        self.assertIn("Sakura", text)
        self.assertIn("角色资料", text)

    async def test_icon_extension_directory_is_used(self):
        from shutil import copyfile

        with tempfile.TemporaryDirectory() as temp:
            old = os.environ.get("ASTRBOT_DATA_DIR")
            os.environ["ASTRBOT_DATA_DIR"] = temp
            try:
                plugin = StalzonePlugin(Context(), {"region": "eu"})
                extension = (
                    Path(temp) / "astrbot_plugin_stalzone" / "item_icons"
                )
                extension.mkdir(parents=True, exist_ok=True)
                target = extension / "extensiontest.png"
                copyfile(PLUGIN_ROOT / "logo.png", target)
                found = await plugin._fetch_icon(
                    "https://example.test/extensiontest.png"
                )
                self.assertEqual(found, target)
            finally:
                if old is None:
                    os.environ.pop("ASTRBOT_DATA_DIR", None)
                else:
                    os.environ["ASTRBOT_DATA_DIR"] = old

    async def test_item_atom_details(self):
        text = await collect(self.make_plugin(), "/sz item 原子")
        self.assertIn("原子", text)
        self.assertIn("生命：", text)
        self.assertIn("玻尔原子模型", text)

    async def test_unknown_command(self):
        text = await collect(self.make_plugin(), "/sz nope")
        self.assertIn("未知指令", text)


class AutoEmissionTests(unittest.IsolatedAsyncioTestCase):
    GROUP_TARGET = "aiocqhttp:GroupMessage:123456"
    OTHER_GROUP_TARGET = "aiocqhttp:GroupMessage:654321"
    PRIVATE_TARGET = "aiocqhttp:FriendMessage:123456"
    OFFICIAL_TARGET = "qq_official:GroupMessage:GROUP-abc123"
    OFFICIAL_WEBHOOK_TARGET = (
        "qq_official_webhook:GroupMessage:USER-111_GROUP-xyz789"
    )
    CUSTOM_ONEBOT_TARGET = "qq:GroupMessage:123456"
    UNIQUE_ONEBOT_TARGET = "aiocqhttp:GroupMessage:111222_333444"

    class Client(FakeClient):
        def __init__(self, payload):
            self.payload = payload
            self.calls = 0

        async def get_emission(self):
            self.calls += 1
            return self.payload

    class TargetEvent(FakeEvent):
        def __init__(self, text: str, target: str):
            super().__init__(text)
            self.unified_msg_origin = target

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
                "emission_notify_target": self.GROUP_TARGET,
            },
        )

    def test_watermark_switch_applies_globally(self):
        import image_renderer as renderer

        old = renderer.CREATOR_WATERMARK_HIDDEN
        try:
            StalzonePlugin(
                Context(),
                {"region": "eu", "hide_creator_watermark": True},
            )
            self.assertTrue(renderer.CREATOR_WATERMARK_HIDDEN)
            StalzonePlugin(Context(), {"region": "eu"})
            self.assertFalse(renderer.CREATOR_WATERMARK_HIDDEN)
        finally:
            renderer.set_creator_watermark_hidden(old)

    def test_help_cache_key_tracks_watermark_setting(self):
        plugin = self.make_plugin()
        before = plugin._help_cache_path()
        plugin.config["hide_creator_watermark"] = True
        after = plugin._help_cache_path()
        self.assertNotEqual(before, after)

    def test_enabled_by_default_and_config_flag(self):
        plugin = StalzonePlugin(Context(), {})
        self.assertTrue(plugin._auto_notify_enabled())
        plugin.config["emission_auto_notify"] = False
        self.assertFalse(plugin._auto_notify_enabled())

    def test_background_config_applies_globally(self):
        import image_renderer as renderer

        try:
            StalzonePlugin(
                Context(),
                {
                    "region": "eu",
                    "card_background": "03 瞭望塔",
                    "card_panel_opacity": 0.5,
                },
            )
            stamp = renderer.card_background_stamp()
            self.assertIn("wallpaper_03.jpg", stamp)
            self.assertIn("|128", stamp)
        finally:
            StalzonePlugin(Context(), {"region": "eu"})

    async def test_empty_whitelist_skips_api_polling(self):
        plugin = self.make_plugin()
        client = self.Client({})
        plugin._make_client = lambda: client  # type: ignore[assignment]
        await plugin._emission_auto_tick(force=True)
        self.assertEqual(client.calls, 0)
        self.assertEqual(plugin._notify_targets(), [])

    async def test_outside_window_uses_slow_probe(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [self.GROUP_TARGET]
        client = self.Client({"previousEnd": "2026-10-22T03:30:00Z"})
        plugin._make_client = lambda: client  # type: ignore[assignment]
        plugin._auto_state = {
            "last_previous_end": (
                datetime.now(timezone.utc) - timedelta(hours=1)
            ).isoformat()
        }
        await plugin._emission_auto_tick()
        self.assertEqual(client.calls, 1)
        await plugin._emission_auto_tick()
        self.assertEqual(client.calls, 1)
        plugin._auto_state["last_probe_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=4)
        ).isoformat()
        await plugin._emission_auto_tick()
        self.assertEqual(client.calls, 2)

    async def test_slow_probe_catches_storm_after_old_window(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [self.GROUP_TARGET]
        now = datetime.now(timezone.utc)
        old_end = (now - timedelta(hours=6)).isoformat()
        client = self.Client(
            {
                "currentStart": (now - timedelta(minutes=5)).isoformat(),
                "previousStart": (now - timedelta(hours=6)).isoformat(),
                "previousEnd": old_end,
            }
        )
        plugin._make_client = lambda: client  # type: ignore[assignment]
        plugin._auto_state = {"last_previous_end": old_end}
        sent = []

        async def fake_send(payload, region, targets):
            sent.append(list(targets))
            return list(targets), []

        plugin._send_emission_alert = fake_send  # type: ignore[assignment]
        await plugin._emission_auto_tick()
        self.assertEqual(client.calls, 1)
        self.assertEqual(sent, [[self.GROUP_TARGET]])
        self.assertTrue(plugin._auto_state["active"])

    async def test_window_detects_once_and_deduplicates(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [self.GROUP_TARGET]
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=8)
        client = self.Client(
            {
                "currentStart": start.isoformat(),
                "previousStart": (now - timedelta(hours=4)).isoformat(),
                "previousEnd": (now - timedelta(hours=3)).isoformat(),
            }
        )
        plugin._make_client = lambda: client  # type: ignore[assignment]
        plugin._auto_state = {
            "last_previous_end": (now - timedelta(hours=2, minutes=30)).isoformat()
        }
        sent = []

        async def fake_send(payload, region, targets):
            sent.append((payload, region, list(targets)))
            return list(targets), []

        plugin._send_emission_alert = fake_send  # type: ignore[assignment]
        await plugin._emission_auto_tick()
        self.assertEqual(client.calls, 1)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][1], "eu")
        self.assertEqual(sent[0][2], [self.GROUP_TARGET])
        self.assertTrue(plugin._auto_state["active"])
        self.assertEqual(plugin._auto_state["last_notified_start"], start.isoformat())

        await plugin._emission_auto_tick()
        self.assertEqual(client.calls, 2)
        self.assertEqual(len(sent), 1)

    async def test_send_false_is_treated_as_failure(self):
        class FailingContext(Context):
            async def send_message(self, target, chain):
                return False

        class FakeChain:
            def message(self, text):
                return self

        plugin = StalzonePlugin(FailingContext(), {"region": "eu"})
        payload = {"currentStart": datetime.now(timezone.utc).isoformat()}
        with patch.object(main_module, "MessageChain", FakeChain), patch.object(
            main_module,
            "render_emission_alert_card",
            lambda view, font_path=None: None,
        ):
            sent, failed = await plugin._send_emission_alert(
                payload, "eu", [self.GROUP_TARGET]
            )
        self.assertEqual(sent, [])
        self.assertEqual(failed, [self.GROUP_TARGET])

    async def test_partial_delivery_retries_only_failed_groups(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = ["111111", "222222"]
        now = datetime.now(timezone.utc)
        client = self.Client(
            {
                "currentStart": now.isoformat(),
                "previousEnd": (now - timedelta(hours=3)).isoformat(),
            }
        )
        plugin._make_client = lambda: client  # type: ignore[assignment]
        calls = []

        async def fake_send(payload, region, targets):
            calls.append(list(targets))
            if len(calls) == 1:
                return [targets[0]], [targets[1]]
            return list(targets), []

        plugin._send_emission_alert = fake_send  # type: ignore[assignment]
        await plugin._emission_auto_tick(force=True)
        first = "aiocqhttp:GroupMessage:111111"
        second = "aiocqhttp:GroupMessage:222222"
        self.assertEqual(calls[0], [first, second])
        self.assertEqual(plugin._auto_state["notified_targets"], [first])
        await plugin._emission_auto_tick(force=True)
        self.assertEqual(calls[1], [second])
        self.assertEqual(
            plugin._auto_state["notified_targets"], [first, second]
        )

    async def test_alert_send_uses_proactive_message_chain(self):
        class RecordingContext(Context):
            def __init__(self):
                self.sent = []

            async def send_message(self, target, chain):
                self.sent.append((target, chain))

        class FakePlain:
            def __init__(self, text):
                self.text = text

        class FakeChain:
            def __init__(self, components=None):
                self.components = list(components or [])

            def message(self, text):
                self.components.append(FakePlain(text))
                return self

        context = RecordingContext()
        plugin = StalzonePlugin(
            context,
            {"region": "eu", "emission_notify_target": self.GROUP_TARGET},
        )
        payload = {
            "currentStart": datetime.now(timezone.utc).isoformat(),
            "previousEnd": (
                datetime.now(timezone.utc) - timedelta(hours=3)
            ).isoformat(),
        }
        with patch.object(main_module, "MessageChain", FakeChain), patch.object(
            main_module,
            "render_emission_alert_card",
            lambda view, font_path=None: None,
        ):
            sent, failed = await plugin._send_emission_alert(
                payload, "eu", [self.GROUP_TARGET]
            )
        self.assertEqual(sent, [self.GROUP_TARGET])
        self.assertEqual(failed, [])
        self.assertEqual(len(context.sent), 1)
        target, chain = context.sent[0]
        self.assertEqual(target, self.GROUP_TARGET)
        self.assertIn("辐射风暴已开始", chain.components[0].text)

    async def test_active_end_anchors_window_if_api_lags(self):
        from formatters import parse_auction_time

        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [self.GROUP_TARGET]
        now = datetime.now(timezone.utc)
        old_end = (now - timedelta(hours=4, minutes=40)).isoformat()
        client = self.Client({"previousEnd": old_end})
        plugin._make_client = lambda: client  # type: ignore[assignment]
        plugin._auto_state = {
            "active": True,
            "last_previous_end": old_end,
            "last_notified_start": (now - timedelta(minutes=8)).isoformat(),
        }
        await plugin._emission_auto_tick()
        self.assertFalse(plugin._auto_state["active"])
        anchored = parse_auction_time(plugin._auto_state["last_previous_end"])
        self.assertIsNotNone(anchored)
        self.assertLess(abs((anchored - now).total_seconds()), 10)

    async def test_terminate_cancels_reminder_and_closes_http(self):
        class FakeHTTP:
            closed = False

            async def aclose(self):
                self.closed = True

        plugin = self.make_plugin()
        http = FakeHTTP()
        plugin._http_client = http  # type: ignore[assignment]
        plugin._auto_task = __import__("asyncio").create_task(
            __import__("asyncio").sleep(60)
        )
        task = plugin._auto_task
        await plugin.terminate()
        self.assertTrue(task.cancelled())
        self.assertTrue(http.closed)

    async def test_alert_send_uses_image_and_cleans_temp_file(self):
        class RecordingContext(Context):
            def __init__(self):
                self.sent = []

            async def send_message(self, target, chain):
                self.sent.append((target, chain))

        class FakeChain:
            def __init__(self, components=None):
                self.components = list(components or [])
                self.image_path = None

            def file_image(self, path):
                self.image_path = path
                return self

        context = RecordingContext()
        plugin = StalzonePlugin(
            context,
            {"region": "eu", "emission_notify_target": self.GROUP_TARGET},
        )
        payload = {
            "currentStart": datetime.now(timezone.utc).isoformat(),
        }
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "alert.png"
            image.write_bytes(b"not-a-real-png")
            renders = []

            def fake_render(view, font_path=None):
                renders.append(1)
                return image

            with patch.object(main_module, "MessageChain", FakeChain), patch.object(
                main_module,
                "render_emission_alert_card",
                fake_render,
            ):
                sent, failed = await plugin._send_emission_alert(
                    payload, "eu", [self.GROUP_TARGET, self.OTHER_GROUP_TARGET]
                )
            self.assertEqual(sent, [self.GROUP_TARGET, self.OTHER_GROUP_TARGET])
            self.assertEqual(failed, [])
            self.assertEqual(len(renders), 1)
            self.assertFalse(image.exists())
            expected_path = str(image)
        self.assertEqual(len(context.sent), 2)
        self.assertEqual(context.sent[0][1].image_path, expected_path)
        self.assertEqual(context.sent[1][1].image_path, expected_path)

    def test_private_chat_is_not_remembered(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin._auto_state = {}
        plugin._remember_notify_target(
            self.TargetEvent("/sz 风暴", self.PRIVATE_TARGET)
        )
        self.assertNotIn("target", plugin._auto_state)
        self.assertEqual(plugin._notify_targets(), [])

    def test_official_group_keys_are_parsed(self):
        plugin = self.make_plugin()
        self.assertEqual(
            plugin._group_key(self.OFFICIAL_TARGET), "GROUP-abc123"
        )
        self.assertEqual(
            plugin._group_key(self.OFFICIAL_WEBHOOK_TARGET), "GROUP-xyz789"
        )
        self.assertEqual(
            plugin._group_key("aiocqhttp:GroupMessage:123456"), "123456"
        )
        self.assertEqual(plugin._group_key("GROUP-abc123"), "GROUP-abc123")

    def test_official_targets_are_not_auto_alert_targets(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = [self.OFFICIAL_TARGET]
        plugin._auto_state = {}
        self.assertFalse(plugin._auto_target_allowed(self.OFFICIAL_TARGET))
        self.assertEqual(plugin._notify_targets(), [])
        plugin._remember_notify_target(
            self.TargetEvent("/sz 风暴", self.OFFICIAL_TARGET)
        )
        self.assertNotIn("target", plugin._auto_state)
        self.assertNotIn("platform", plugin._auto_state)

    def test_mixed_whitelist_keeps_onebot_targets_only(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [
            self.OFFICIAL_TARGET,
            "123456",
        ]
        self.assertEqual(
            plugin._notify_targets(), ["aiocqhttp:GroupMessage:123456"]
        )

    async def test_official_only_whitelist_skips_api_polling(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = [self.OFFICIAL_TARGET]
        client = self.Client({})
        plugin._make_client = lambda: client  # type: ignore[assignment]
        await plugin._emission_auto_tick(force=True)
        self.assertEqual(client.calls, 0)

    async def test_official_platform_command_path(self):
        plugin = self.make_plugin()
        event = self.TargetEvent("/sz help", self.OFFICIAL_TARGET)
        results = []
        async for item in plugin.sz(event):
            results.append(item)
        self.assertTrue(results)
        self.assertNotIn("target", plugin._auto_state)

    def test_custom_onebot_platform_prefix_from_state(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = ["123456", "654321"]
        plugin._auto_state = {"platform": "qq"}
        self.assertEqual(
            plugin._notify_targets(),
            ["qq:GroupMessage:123456", "qq:GroupMessage:654321"],
        )
        self.assertTrue(plugin._auto_target_allowed(self.CUSTOM_ONEBOT_TARGET))

    def test_onebot_unique_session_normalizes_to_group(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = ["333444"]
        plugin._auto_state = {"platform": "aiocqhttp"}
        self.assertEqual(plugin._group_key(self.UNIQUE_ONEBOT_TARGET), "333444")
        self.assertTrue(
            plugin._auto_target_allowed(self.UNIQUE_ONEBOT_TARGET)
        )
        self.assertEqual(
            plugin._notify_targets(), ["aiocqhttp:GroupMessage:333444"]
        )
        plugin.config["emission_group_whitelist"] = [self.UNIQUE_ONEBOT_TARGET]
        self.assertEqual(
            plugin._notify_targets(), ["aiocqhttp:GroupMessage:333444"]
        )

    def test_non_qq_platform_is_not_auto_alert_target(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = ["123456"]
        plugin._auto_state = {"platform": "telegram"}
        self.assertEqual(plugin._notify_targets(), [])
        self.assertFalse(
            plugin._auto_target_allowed("telegram:GroupMessage:123456")
        )

    def test_custom_onebot_full_umo_whitelist(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = [
            self.CUSTOM_ONEBOT_TARGET
        ]
        self.assertEqual(
            plugin._notify_targets(), [self.CUSTOM_ONEBOT_TARGET]
        )

    def test_whitelist_broadcasts_every_allowed_group(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [
            "111111",
            "aiocqhttp:GroupMessage:222222",
            "333333",
            "222222",
        ]
        plugin.config["emission_group_blacklist"] = ["333333"]
        self.assertEqual(
            plugin._notify_targets(),
            [
                "aiocqhttp:GroupMessage:111111",
                "aiocqhttp:GroupMessage:222222",
            ],
        )

    def test_empty_whitelist_sends_nothing(self):
        plugin = self.make_plugin()
        plugin._auto_state = {"target": "aiocqhttp:GroupMessage:999999"}
        self.assertEqual(plugin._notify_targets(), [])
        plugin.config["emission_group_whitelist"] = ["999999"]
        self.assertEqual(
            plugin._notify_targets(), ["aiocqhttp:GroupMessage:999999"]
        )

    def test_remember_ignores_groups_outside_whitelist(self):
        plugin = self.make_plugin()
        plugin.config["emission_notify_target"] = ""
        plugin.config["emission_group_whitelist"] = ["123456"]
        plugin._auto_state = {}
        plugin._remember_notify_target(
            self.TargetEvent("/sz 风暴", "aiocqhttp:GroupMessage:999999")
        )
        self.assertNotIn("target", plugin._auto_state)
        plugin._remember_notify_target(
            self.TargetEvent("/sz 风暴", self.GROUP_TARGET)
        )
        self.assertEqual(plugin._auto_state["target"], self.GROUP_TARGET)
        self.assertEqual(plugin._notify_targets(), [self.GROUP_TARGET])

    async def test_force_probe_updates_window_after_restart(self):
        plugin = self.make_plugin()
        plugin.config["emission_group_whitelist"] = [self.GROUP_TARGET]
        now = datetime.now(timezone.utc)
        previous_end = now - timedelta(hours=5)
        client = self.Client({"previousEnd": previous_end.isoformat()})
        plugin._make_client = lambda: client  # type: ignore[assignment]
        plugin._auto_state = {}
        await plugin._emission_auto_tick(force=True)
        self.assertEqual(client.calls, 1)
        self.assertFalse(plugin._auto_state["active"])
        self.assertEqual(
            plugin._auto_state["last_previous_end"], previous_end.isoformat()
        )

    async def test_target_and_active_state_survive_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            old = os.environ.get("ASTRBOT_DATA_DIR")
            os.environ["ASTRBOT_DATA_DIR"] = temp
            try:
                first = StalzonePlugin(Context(), {"region": "eu"})
                first._remember_notify_target(
                    self.TargetEvent("/sz 风暴", self.GROUP_TARGET)
                )
                start = datetime.now(timezone.utc).isoformat()
                first._auto_state.update(
                    {"active": True, "last_notified_start": start}
                )
                first._save_auto_state()
                second = StalzonePlugin(Context(), {"region": "eu"})
                self.assertEqual(second._auto_state["target"], self.GROUP_TARGET)
                self.assertEqual(second._notify_targets(), [])
                self.assertTrue(second._auto_state["active"])
                self.assertEqual(second._auto_state["last_notified_start"], start)
                client = self.Client(
                    {
                        "currentStart": start,
                        "previousEnd": (
                            datetime.now(timezone.utc) - timedelta(hours=3)
                        ).isoformat(),
                    }
                )
                second._make_client = lambda: client  # type: ignore[assignment]
                second.config["emission_group_whitelist"] = [self.GROUP_TARGET]
                sent = []

                async def fake_send(payload, region, targets):
                    sent.append((payload, region, list(targets)))
                    return list(targets), []

                second._send_emission_alert = fake_send  # type: ignore[assignment]
                await second._emission_auto_tick(force=True)
                self.assertEqual(len(sent), 0)
                self.assertEqual(client.calls, 1)
            finally:
                if old is None:
                    os.environ.pop("ASTRBOT_DATA_DIR", None)
                else:
                    os.environ["ASTRBOT_DATA_DIR"] = old


if __name__ == "__main__":
    unittest.main()
