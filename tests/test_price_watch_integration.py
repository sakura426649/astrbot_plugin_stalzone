from __future__ import annotations

import asyncio
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tests.test_main_integration as integration
import image_renderer
import main as main_module
from main import StalzonePlugin


def _text(result):
    return result.text if hasattr(result, "text") else result


class WatchEvent(integration.FakeEvent):
    def __init__(
        self,
        text: str,
        *,
        user_id: str = "u1",
        name: str = "Alice",
        group: str = "123",
        private: bool = False,
        admin: bool = False,
    ):
        super().__init__(text)
        kind = "FriendMessage" if private else "GroupMessage"
        self.unified_msg_origin = f"aiocqhttp:{kind}:{group}"
        self._user_id = user_id
        self._name = name
        self._private = private
        self._admin = admin

    def get_sender_id(self):
        return self._user_id

    def get_sender_name(self):
        return self._name

    def is_private_chat(self):
        return self._private

    def is_admin(self):
        return self._admin


class WatchClient(integration.FakeClient):
    region = "eu"
    lots: list[dict] = []
    history: list[dict] = []
    lots_calls = 0

    async def get_auction_lots(self, item_id, limit=50):
        type(self).lots_calls += 1
        return {"lots": self.lots}

    async def get_auction_history(self, item_id, limit=20, offset=0):
        return {"prices": self.history}


class PriceWatchIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def make_plugin(self, client: WatchClient | None = None):
        plugin = integration.MainSmokeTests.make_plugin(
            integration.MainSmokeTests()
        )
        plugin.config.update(
            {
                "client_id": "x",
                "client_secret": "y",
                "render_mode": "text",
                "price_watch_interval": 120,
                "price_watch_per_user": 2,
                "price_watch_session_items": 5,
            }
        )
        plugin._watch_state = {"version": 1, "cursor": 0, "subscriptions": {}}
        plugin._watch_path = Path(tempfile.mkdtemp()) / "price_watch.json"
        plugin._watch_median_cache = {}
        client = client or WatchClient()
        WatchClient.lots = []
        WatchClient.history = []
        WatchClient.lots_calls = 0
        plugin._make_client = lambda region=None: client  # type: ignore[assignment]
        return plugin

    async def test_watch_usage_and_list_dispatch(self):
        plugin = self.make_plugin()
        usage = await integration.collect(plugin, "/sz 关注")
        self.assertIn("用法：/sz 关注", usage)
        listing = await integration.collect(plugin, "/sz 关注列表")
        self.assertIn("神器价格关注", listing)
        cancel_usage = await integration.collect(plugin, "/sz 取消关注")
        self.assertIn("用法：/sz 取消关注", cancel_usage)

    def test_watch_render_syncs_live_background_config(self):
        plugin = self.make_plugin()
        plugin.config["card_background"] = "官方壁纸 01"
        plugin.config["card_panel_opacity"] = 0.5
        with patch.object(
            main_module, "set_card_background", return_value=Path("x")
        ) as mocked:
            plugin._sync_render_config()
        mocked.assert_called_once_with("官方壁纸 01", "", 0.5)

    async def test_watch_list_uses_subscription_regions(self):
        plugin = self.make_plugin()
        plugin.config["region"] = "eu"
        await plugin._handle_watch(WatchEvent("/sz", user_id="u1"), "wg53 红 +15 8000")
        plugin.config["region"] = "ru"
        await plugin._handle_watch(WatchEvent("/sz", user_id="u2"), "wg53 红 +15 7000")
        view = plugin._watch_list_view(WatchEvent("/sz", user_id="u1"))
        self.assertEqual(view["regions"], ["EU", "RU"])
        self.assertEqual(view["region"], "EU/RU")
        self.assertIn("EU/RU", _text(await plugin._handle_watch_list(WatchEvent("/sz"))))

    async def test_watch_alert_honors_text_render_mode(self):
        plugin = self.make_plugin()
        plugin.config["render_mode"] = "text"
        captured = []

        async def fake_message(sub, text, image_path=None):
            captured.append((text, image_path))
            return True

        plugin._watch_send_message = fake_message  # type: ignore[assignment]
        sub = {"quality": 4, "level": 15, "region": "eu", "session": "s"}
        item = {"id": "wg53", "zh": "原子", "en": "Atom"}
        match = {
            "kind": "auction",
            "current": 7000,
            "buyout": 9000,
            "quality": 4,
            "level": 15,
            "amount": 1,
            "remaining": "剩 2 小时",
            "signature": "lot-1",
        }
        ok = await plugin._watch_send_alert(
            sub, item, match, extra=1, now=datetime.now(timezone.utc)
        )
        self.assertTrue(ok)
        self.assertEqual(len(captured), 1)
        self.assertIsNone(captured[0][1])
        self.assertIn("原子", captured[0][0])
        self.assertIn("同轮另有 1 条", captured[0][0])

    def test_watch_cards_sync_live_watermark_config(self):
        plugin = self.make_plugin()
        plugin.config["hide_creator_watermark"] = True
        plugin._sync_render_config()
        self.assertTrue(image_renderer.CREATOR_WATERMARK_HIDDEN)
        image_renderer.set_creator_watermark_hidden(False)

    async def test_concurrent_creates_cannot_bypass_per_user_cap(self):
        plugin = self.make_plugin()
        plugin.config["price_watch_per_user"] = 1

        class SlowClient(WatchClient):
            async def get_auction_lots(self, item_id, limit=50):
                await asyncio.sleep(0.01)
                return {"lots": []}

            async def get_auction_history(self, item_id, limit=20, offset=0):
                return {"prices": []}

        plugin._make_client = lambda region=None: SlowClient()  # type: ignore[assignment]
        event = WatchEvent("/sz")
        results = await asyncio.gather(
            plugin._handle_watch(event, "wg53 红 +15 8000"),
            plugin._handle_watch(event, "ljn2 红 +15 8000"),
        )
        texts = [getattr(result, "text", result) for result in results]
        self.assertEqual(sum("已创建关注" in text for text in texts), 1)
        self.assertEqual(sum("最多关注 1 种" in text for text in texts), 1)
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_ambiguous_watch_can_continue_with_candidate(self):
        plugin = self.make_plugin()
        original = plugin._resolve_item

        def resolve(query):
            if query == "ambiguous":
                return None, [
                    {"id": "wg53", "zh": "原子", "en": "Atom", "cat": "artefact"},
                    {"id": "ljn2", "zh": "寒冰", "en": "Ice", "cat": "artefact"},
                ]
            return original(query)

        plugin._resolve_item = resolve  # type: ignore[assignment]
        event = WatchEvent("/sz")
        first = await plugin._handle_watch(event, "ambiguous 红 +15 8000")
        self.assertTrue(hasattr(first, "candidate_view"))
        result = await plugin._handle_candidate("1", event)
        self.assertEqual(result.sub, "watch")
        self.assertIn("已创建关注", getattr(result, "text", result))
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_per_user_total_subscription_cap(self):
        plugin = self.make_plugin()
        plugin.config["price_watch_per_user"] = 5
        plugin.config["price_watch_user_total"] = 2
        first = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +15 8000"
        )
        second = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +14 8000"
        )
        third = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +13 8000"
        )
        self.assertIn("已创建关注", _text(first))
        self.assertIn("已创建关注", _text(second))
        self.assertIn("最多同时保留 2 条", _text(third))
        self.assertEqual(len(plugin._watch_subs()), 2)

    async def test_watch_list_paginates_by_user(self):
        plugin = self.make_plugin()
        plugin.WATCH_LIST_ROWS_PER_PAGE = 2
        for index in range(3):
            await plugin._handle_watch(
                WatchEvent("/sz", user_id=f"u{index}", name=f"User{index}"),
                "wg53 红 +15 8000",
            )
        reply = await plugin._handle_watch_list(WatchEvent("/sz", user_id="u0"))
        self.assertEqual(reply.watch_list_view["page"], 1)
        self.assertEqual(reply.watch_list_view["pages"], 2)
        self.assertEqual(len(reply.watch_list_view["users"]), 2)
        self.assertIn("第 1/2 页", reply.text)
        self.assertIn("原子", reply.text)
        second = await plugin._handle_watch_list(
            WatchEvent("/sz", user_id="u0"), 2
        )
        self.assertIn("第 2/2 页", second.text)
        self.assertEqual(len(second.watch_list_view["users"]), 1)
        too_far = await plugin._handle_watch_list(
            WatchEvent("/sz", user_id="u0"), 3
        )
        self.assertIn("只有 2 页", too_far)
        async def dispatch(text):
            return chr(10).join(
                [
                    item[1]
                    async for item in plugin.sz(
                        WatchEvent(text, user_id="u0")
                    )
                ]
            )

        self.assertIn("第 2/2 页", await dispatch("/sz 关注列表 2"))
        self.assertIn("第 2/2 页", await dispatch("/sz 关注 列表 2"))

    async def test_watch_list_repeats_user_when_items_are_split(self):
        plugin = self.make_plugin()
        plugin.WATCH_LIST_ROWS_PER_PAGE = 1
        event = WatchEvent("/sz", user_id="u1", name="Alice")
        await plugin._handle_watch(event, "wg53 红 +15 8000")
        await plugin._handle_watch(event, "wg53 红 +14 7000")
        first = await plugin._handle_watch_list(event, 1)
        second = await plugin._handle_watch_list(event, 2)
        self.assertEqual(first.watch_list_view["page"], 1)
        self.assertEqual(second.watch_list_view["page"], 2)
        self.assertTrue(second.watch_list_view["users"][0]["continued"])
        self.assertIn("Alice（续）", second.text)

    async def test_cap_rejection_does_not_hit_auction_api(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        await plugin._handle_watch(WatchEvent("/sz"), "ljn2 红 +15 8000")
        before = WatchClient.lots_calls
        result = await plugin._handle_watch(WatchEvent("/sz"), "9nd0 红 +15 8000")
        self.assertIn("最多关注 2 种", _text(result))
        self.assertEqual(WatchClient.lots_calls, before)

    async def test_auction_alerts_can_be_disabled(self):
        plugin = self.make_plugin()
        plugin.config["price_watch_auction_alerts"] = False
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7000,
                "buyoutPrice": 9000,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        result = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +15 8000"
        )
        self.assertIn("关闭", _text(result))
        calls = []

        async def fake_alert(sub, item, match, *, extra, now):
            calls.append(match)
            return True

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(calls, [])
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_expiry_race_keeps_renewed_subscription(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        key = next(iter(plugin._watch_subs()))
        sub = plugin._watch_subs()[key]
        now = datetime.now(timezone.utc)
        sub["expires_at"] = (now - timedelta(seconds=1)).isoformat()

        async def renewing_send(target, text, image_path=None):
            sub["expires_at"] = (now + timedelta(hours=1)).isoformat()
            return True

        plugin._watch_send_message = renewing_send  # type: ignore[assignment]
        changed = await plugin._watch_expire(plugin._watch_subs(), now)
        self.assertFalse(changed)
        self.assertIn(key, plugin._watch_subs())

    async def test_one_bad_subscription_does_not_abort_tick(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u1"), "wg53 红 +15 8000"
        )
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u2"), "wg53 红 +15 8000"
        )
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7500,
                "buyoutPrice": 7800,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        called = []

        async def flaky_alert(sub, item, match, *, extra, now):
            if sub.get("user_id") == "u1":
                raise RuntimeError("render failed")
            called.append(sub.get("user_id"))
            return True

        plugin._watch_send_alert = flaky_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(called, ["u2"])
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_target_above_current_buyout_is_rejected(self):
        plugin = self.make_plugin()
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7500,
                "buyoutPrice": 7800,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        result = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +15 8000"
        )
        self.assertIn("无需创建关注", _text(result))
        self.assertEqual(plugin._watch_subs(), {})

    async def test_target_above_current_auction_creates_with_notice(self):
        plugin = self.make_plugin()
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7000,
                "buyoutPrice": 9000,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        result = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +15 8000"
        )
        self.assertIn("已创建关注", _text(result))
        self.assertIn("当前竞拍价", _text(result))
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_create_update_and_per_user_cap(self):
        plugin = self.make_plugin()
        created = await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        self.assertIn("已创建关注", _text(created))
        second = await plugin._handle_watch(WatchEvent("/sz"), "ljn2 红 +15 8000")
        self.assertIn("已创建关注", _text(second))
        third = await plugin._handle_watch(WatchEvent("/sz"), "9nd0 红 +15 8000")
        self.assertIn("最多关注 2 种", _text(third))
        updated = await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 7000")
        self.assertIn("已更新关注", _text(updated))
        self.assertEqual(len(plugin._watch_subs()), 2)

    async def test_session_cap_and_shared_item_slot(self):
        plugin = self.make_plugin()
        ids = ["wg53", "ljn2", "9nd0", "gyq5", "jkj4"]
        for index, item_id in enumerate(ids):
            user = f"u{index // 2 + 1}"
            result = await plugin._handle_watch(
                WatchEvent("/sz", user_id=user), f"{item_id} 红 +15 8000"
            )
            self.assertIn("已创建关注", _text(result))
        sixth = await plugin._handle_watch(
            WatchEvent("/sz", user_id="u9"), "zy7y 红 +15 8000"
        )
        self.assertIn("本会话最多", _text(sixth))
        # Another user can still watch one of the five existing items.
        shared = await plugin._handle_watch(
            WatchEvent("/sz", user_id="u9"), "wg53 红 +15 7000"
        )
        self.assertIn("已创建关注", _text(shared))

    async def test_list_pins_own_and_cancel_permissions(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u1", name="Alice"), "wg53 红 +15 8000"
        )
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u2", name="Bob"), "ljn2 红 +15 8000"
        )
        reply = await plugin._handle_watch_list(
            WatchEvent("/sz", user_id="u2", name="Bob")
        )
        text = reply.text
        self.assertIn("Bob  [你]", text)
        self.assertIn("Alice", text)
        self.assertLess(text.index("Bob"), text.index("Alice"))
        denied = await plugin._handle_watch_cancel(
            WatchEvent("/sz", user_id="u2", name="Bob"), "2"
        )
        self.assertIn("只能取消自己的关注", _text(denied))
        allowed = await plugin._handle_watch_cancel(
            WatchEvent("/sz", user_id="admin", admin=True), "2"
        )
        self.assertIn("已取消关注", _text(allowed))
        self.assertEqual(allowed.watch_action_view["title"], "已取消关注")
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_buyout_alert_removes_subscription(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7500,
                "buyoutPrice": 7800,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        calls = []

        async def fake_alert(sub, item, match, *, extra, now):
            calls.append((match["kind"], match["price"], extra))
            return True

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(calls, [("buyout", 7800, 0)])
        self.assertEqual(plugin._watch_subs(), {})

    async def test_failed_buyout_alert_keeps_subscription(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7500,
                "buyoutPrice": 7800,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]

        async def fake_alert(sub, item, match, *, extra, now):
            return False

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_auction_alert_keeps_and_new_lot_alerts_again(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7000,
                "buyoutPrice": 9000,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        calls = []

        async def fake_alert(sub, item, match, *, extra, now):
            calls.append((match["kind"], match["price"], extra))
            return True

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(calls, [("auction", 7000, 0)])
        self.assertEqual(len(plugin._watch_subs()), 1)
        await plugin._watch_tick(force=True)
        self.assertEqual(len(calls), 1)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 6800,
                "buyoutPrice": 9000,
                "startTime": "2026-11-11T01:00:00Z",
                "endTime": (now + timedelta(hours=4)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        await plugin._watch_tick(force=True)
        self.assertEqual(calls[-1][:2], ("auction", 6800))
        self.assertEqual(len(calls), 2)

    async def test_each_qualifying_auction_lot_gets_its_own_alert(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7000,
                "buyoutPrice": 9000,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            },
            {
                "amount": 1,
                "currentPrice": 6800,
                "buyoutPrice": 9000,
                "startTime": "2026-11-11T01:00:00Z",
                "endTime": (now + timedelta(hours=3)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            },
        ]
        calls = []

        async def fake_alert(sub, item, match, *, extra, now):
            calls.append((match["price"], extra))
            return True

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(calls, [(6800, 1)])
        await plugin._watch_tick(force=True)
        self.assertEqual(calls, [(6800, 1), (7000, 0)])

    async def test_group_notification_mentions_subscriber(self):
        class FakeAt:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeChain:
            def __init__(self):
                self.components = []

            def at(self, name, qq):
                self.components.append(FakeAt(name=name, qq=qq))
                return self

            def message(self, text):
                self.components.append(text)
                return self

            def file_image(self, path):
                self.components.append(("image", path))
                return self

        class RecordingContext:
            def __init__(self):
                self.sent = []

            async def send_message(self, target, chain):
                self.sent.append((target, chain))
                return True

        plugin = self.make_plugin()
        context = RecordingContext()
        plugin.context = context
        sub = {
            "session": "aiocqhttp:GroupMessage:123",
            "user_id": "u1",
            "user_name": "Alice",
            "private": False,
        }
        with patch.object(main_module, "MessageChain", FakeChain), patch.object(
            main_module, "AstrAt", FakeAt
        ):
            ok = await plugin._watch_send_message(sub, "神器低价提醒")
        self.assertTrue(ok)
        self.assertEqual(len(context.sent), 1)
        chain = context.sent[0][1]
        self.assertIsInstance(chain.components[0], FakeAt)
        self.assertEqual(chain.components[0].kwargs["qq"], "u1")

    async def test_relative_threshold_uses_history_median(self):
        plugin = self.make_plugin()
        now = datetime.now(timezone.utc)
        WatchClient.history = [
            {
                "amount": 1,
                "price": 10000,
                "time": (now - timedelta(days=1)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            },
            {
                "amount": 1,
                "price": 10000,
                "time": (now - timedelta(days=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            },
        ]
        created = await plugin._handle_watch(
            WatchEvent("/sz"), "wg53 红 +15 -20%"
        )
        self.assertIn("已创建关注", _text(created))
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7900,
                "buyoutPrice": 7900,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        calls = []

        async def fake_alert(sub, item, match, *, extra, now):
            calls.append((match["kind"], match["price"], match["target"]))
            return True

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(calls, [("buyout", 7900, 8000)])

    async def test_expired_subscription_is_removed_after_notice(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 红 +15 8000")
        key = next(iter(plugin._watch_subs()))
        plugin._watch_subs()[key]["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        notices = []

        async def fake_message(sub, text, image_path=None):
            notices.append(text)
            return True

        plugin._watch_send_message = fake_message  # type: ignore[assignment]
        await plugin._watch_tick(force=True)
        self.assertEqual(plugin._watch_subs(), {})
        self.assertTrue(any("已到期" in text for text in notices))

    async def test_shared_query_per_subscription_thresholds(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u1", name="Alice"), "wg53 红 +15 8000"
        )
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u2", name="Bob"), "wg53 红 +15 7000"
        )
        now = datetime.now(timezone.utc)
        WatchClient.lots = [
            {
                "amount": 1,
                "currentPrice": 7600,
                "buyoutPrice": 7500,
                "startTime": "2026-11-11T00:00:00Z",
                "endTime": (now + timedelta(hours=2)).isoformat(),
                "additional": {"qlt": 4, "ptn": 15},
            }
        ]
        calls = []

        async def fake_alert(sub, item, match, *, extra, now):
            calls.append((sub["user_id"], match["kind"], match["price"]))
            return True

        plugin._watch_send_alert = fake_alert  # type: ignore[assignment]
        WatchClient.lots_calls = 0
        await plugin._watch_tick(force=True)
        self.assertEqual(WatchClient.lots_calls, 1)
        self.assertIn(("u1", "buyout", 7500), calls)
        self.assertNotIn(("u2", "buyout", 7500), calls)
        self.assertEqual(len(plugin._watch_subs()), 1)
        self.assertEqual(next(iter(plugin._watch_subs().values()))["user_id"], "u2")


if __name__ == "__main__":
    unittest.main()
