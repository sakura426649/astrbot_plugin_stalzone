from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tests.test_main_integration as integration
import main as main_module
from main import StalzonePlugin


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

    async def test_create_update_and_per_user_cap(self):
        plugin = self.make_plugin()
        created = await plugin._handle_watch(WatchEvent("/sz"), "wg53 +15 8000")
        self.assertIn("已创建关注", created)
        second = await plugin._handle_watch(WatchEvent("/sz"), "ljn2 +15 8000")
        self.assertIn("已创建关注", second)
        third = await plugin._handle_watch(WatchEvent("/sz"), "9nd0 +15 8000")
        self.assertIn("最多关注 2 种", third)
        updated = await plugin._handle_watch(WatchEvent("/sz"), "wg53 +15 7000")
        self.assertIn("已更新关注", updated)
        self.assertEqual(len(plugin._watch_subs()), 2)

    async def test_session_cap_and_shared_item_slot(self):
        plugin = self.make_plugin()
        ids = ["wg53", "ljn2", "9nd0", "gyq5", "jkj4"]
        for index, item_id in enumerate(ids):
            user = f"u{index // 2 + 1}"
            result = await plugin._handle_watch(
                WatchEvent("/sz", user_id=user), f"{item_id} +15 8000"
            )
            self.assertIn("已创建关注", result)
        sixth = await plugin._handle_watch(
            WatchEvent("/sz", user_id="u9"), "zy7y +15 8000"
        )
        self.assertIn("本会话最多", sixth)
        # Another user can still watch one of the five existing items.
        shared = await plugin._handle_watch(
            WatchEvent("/sz", user_id="u9"), "wg53 +15 7000"
        )
        self.assertIn("已创建关注", shared)

    async def test_list_pins_own_and_cancel_permissions(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u1", name="Alice"), "wg53 +15 8000"
        )
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u2", name="Bob"), "ljn2 +15 8000"
        )
        text = await plugin._handle_watch_list(
            WatchEvent("/sz", user_id="u2", name="Bob")
        )
        self.assertIn("我的关注", text)
        self.assertIn("本群其他关注", text)
        self.assertLess(text.index("我的关注"), text.index("本群其他关注"))
        denied = await plugin._handle_watch_cancel(
            WatchEvent("/sz", user_id="u2", name="Bob"), "2"
        )
        self.assertIn("只能取消自己的关注", denied)
        allowed = await plugin._handle_watch_cancel(
            WatchEvent("/sz", user_id="admin", admin=True), "2"
        )
        self.assertIn("已取消关注", allowed)
        self.assertEqual(len(plugin._watch_subs()), 1)

    async def test_buyout_alert_removes_subscription(self):
        plugin = self.make_plugin()
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 +15 8000")
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
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 +15 8000")
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
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 +15 8000")
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
            WatchEvent("/sz"), "wg53 +15 -20%"
        )
        self.assertIn("已创建关注", created)
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
        await plugin._handle_watch(WatchEvent("/sz"), "wg53 +15 8000")
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
            WatchEvent("/sz", user_id="u1", name="Alice"), "wg53 +15 8000"
        )
        await plugin._handle_watch(
            WatchEvent("/sz", user_id="u2", name="Bob"), "wg53 +15 7000"
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
