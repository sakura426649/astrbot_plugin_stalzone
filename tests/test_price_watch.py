from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from price_watch import (
    WatchQueryError,
    build_watch_alert_view,
    format_watch_alert_text,
    format_watch_list,
    history_medians,
    parse_watch_query,
    watch_lot_rows,
)

NOW = datetime(2026, 11, 11, 6, 0, tzinfo=timezone.utc)


class WatchParserTests(unittest.TestCase):
    def test_parse_absolute_and_relative(self):
        self.assertEqual(
            parse_watch_query("原子 金 +15 8000"),
            {
                "item": "原子",
                "quality": 5,
                "level": 15,
                "mode": "absolute",
                "threshold": 8000,
                "relative_pct": None,
                "cap": None,
            },
        )
        self.assertEqual(
            parse_watch_query("原子 红 +15 -20%"),
            {
                "item": "原子",
                "quality": 4,
                "level": 15,
                "mode": "relative",
                "threshold": None,
                "relative_pct": 20,
                "cap": None,
            },
        )
        self.assertEqual(
            parse_watch_query("原子 红 +15 -20% 12000")["cap"], 12000
        )

    def test_price_units_and_separators(self):
        cases = {
            "3M": 3_000_000,
            "3m": 3_000_000,
            "3kk": 3_000_000,
            "3KK": 3_000_000,
            "3K": 3_000,
            "3k": 3_000,
            "3,000,000": 3_000_000,
            "3 000 000": 3_000_000,
            "3.5M": 3_500_000,
            "3,5M": 3_500_000,
        }
        for token, expected in cases.items():
            query = parse_watch_query(f"原子 红 +15 {token}")
            self.assertEqual(query["threshold"], expected, token)
            self.assertEqual(query["mode"], "absolute", token)
        capped = parse_watch_query("原子 红 +15 -20% 3kk")
        self.assertEqual(capped["mode"], "relative")
        self.assertEqual(capped["cap"], 3_000_000)
        with self.assertRaises(WatchQueryError):
            parse_watch_query("原子 红 +15 3X")

    def test_parse_requires_level(self):
        with self.assertRaises(WatchQueryError):
            parse_watch_query("原子 8000")
        with self.assertRaises(WatchQueryError):
            parse_watch_query("原子 +16 8000")
        with self.assertRaises(WatchQueryError):
            parse_watch_query("原子 +15")
        with self.assertRaises(WatchQueryError):
            parse_watch_query("原子 +15 8000")
        with self.assertRaises(WatchQueryError):
            parse_watch_query("+15 8000")


class WatchStatsTests(unittest.TestCase):
    def test_history_medians_by_quality_and_level(self):
        payload = {
            "prices": [
                {"amount": 1, "price": 7000, "time": "2026-11-10T00:00:00Z", "additional": {"qlt": 4, "ptn": 15}},
                {"amount": 1, "price": 8000, "time": "2026-11-09T00:00:00Z", "additional": {"qlt": 4, "ptn": 15}},
                {"amount": 1, "price": 12000, "time": "2026-11-08T00:00:00Z", "additional": {"qlt": 5, "ptn": 15}},
                {"amount": 1, "price": 4000, "time": "2026-11-07T00:00:00Z", "additional": {"qlt": 4, "ptn": 10}},
            ]
        }
        medians = history_medians(
            payload, 15, cutoff=NOW - timedelta(days=4), now=NOW
        )
        self.assertEqual(medians[4], 7000)
        self.assertEqual(medians[5], 12000)
        self.assertIn(None, medians)

    def test_lot_signature_ignores_current_price(self):
        lots = {
            "lots": [
                {
                    "amount": 1,
                    "currentPrice": 7000,
                    "startPrice": 7000,
                    "buyoutPrice": 9000,
                    "startTime": "2026-11-11T00:00:00Z",
                    "endTime": "2026-11-11T12:00:00Z",
                    "additional": {"qlt": 4, "ptn": 15},
                }
            ]
        }
        first = watch_lot_rows(lots, "wg53")[0]
        lots["lots"][0]["currentPrice"] = 7500
        second = watch_lot_rows(lots, "wg53")[0]
        self.assertEqual(first["signature"], second["signature"])
        lots["lots"][0]["buyoutPrice"] = 8500
        third = watch_lot_rows(lots, "wg53")[0]
        self.assertNotEqual(first["signature"], third["signature"])


class WatchViewTests(unittest.TestCase):
    ITEM = {"id": "wg53", "zh": "原子", "en": "Atom"}

    def test_alert_view_buyout(self):
        match = {
            "buyout": 7800,
            "current": 7500,
            "quality": 4,
            "level": 15,
            "amount": 1,
            "remaining": "剩 2 小时",
        }
        view = build_watch_alert_view(
            self.ITEM,
            {},
            match,
            region="eu",
            target=8000,
            now=NOW,
        )
        self.assertEqual(view["kind"], "buyout")
        self.assertTrue(view["auto_cancel"])
        self.assertIn("自动取消", view["hint"])
        self.assertIn("7,800", format_watch_alert_text(view))

    def test_alert_view_auction(self):
        match = {
            "buyout": 9000,
            "current": 7000,
            "quality": 4,
            "level": 15,
            "amount": 1,
            "remaining": "剩 3 小时",
        }
        view = build_watch_alert_view(
            self.ITEM, {}, match, region="eu", target=8000, now=NOW
        )
        self.assertEqual(view["kind"], "auction")
        self.assertFalse(view["auto_cancel"])
        self.assertIn("手动", view["hint"])

    def test_watch_list_groups_by_user(self):
        view = {
            "region": "EU",
            "session_items": 2,
            "session_limit": 5,
            "global_items": 3,
            "refresh_minutes": 2,
            "users": [
                {
                    "user_name": "Sakura",
                    "own": True,
                    "items": [
                        {
                            "index": 1,
                            "item_label": "原子 +15",
                            "target": "≤ 8,000",
                            "remaining": "剩 6 天",
                        }
                    ],
                },
                {
                    "user_name": "小明",
                    "own": False,
                    "items": [
                        {
                            "index": 2,
                            "item_label": "寒冰 +10",
                            "target": "-20%",
                            "remaining": "剩 5 天",
                        }
                    ],
                },
            ],
        }
        text = format_watch_list(view)
        self.assertIn("Sakura  [你]", text)
        self.assertIn("小明", text)
        self.assertIn("本群 2/5", text)
        self.assertLess(text.index("Sakura"), text.index("小明"))


if __name__ == "__main__":
    unittest.main()
