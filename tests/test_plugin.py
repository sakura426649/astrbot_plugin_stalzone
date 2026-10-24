"""Unit tests for the HTTP client and formatters (no AstrBot required)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import Mock
from pathlib import Path

import httpx

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from api_client import (  # noqa: E402
    ApiHealth,
    AuthenticationError,
    BadRequestError,
    DEMO_BASE_URL,
    MissingCredentialsError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    ServerError,
    StalzoneAPIClient,
    normalize_base_url,
)
from balance_history import BalanceHistory  # noqa: E402
from command_parser import parse_command  # noqa: E402
from season_pass import (  # noqa: E402
    calculate,
    daily_task_xp,
    parse_arguments,
    weekly_reward,
)
from formatters import (  # noqa: E402
    ARTEFACT_STAT_CN,
    ITEM_STAT_CN,
    QUALITY_COLORS,
    auction_day_cutoff,
    build_auction_view,
    build_clan_candidate_view,
    build_emission_alert_view,
    build_emission_view,
    build_empty_auction_view,
    build_item_candidate_view,
    calculate_hq_pvp_score,
    parse_auction_query,
    format_auction,
    format_auction_text,
    format_balance_history,
    format_clan,
    format_clan_candidates,
    format_clans_list,
    format_diag,
    format_elapsed_hms,
    format_emission,
    format_help,
    format_item,
    format_item_candidates,
    format_operations,
    format_profile,
    build_profile_view,
    format_regions,
    format_season_pass,
)
from image_renderer import (  # noqa: E402
    STAT_GREEN,
    STAT_RED,
    WIDTH,
    find_cjk_font,
    _artifact_label_color,
    _stat_direction,
    faction_icon_path,
    item_color,
    rank_color,
    render_auction_card,
    render_candidate_card,
    render_emission_alert_card,
    render_emission_card,
    render_profile_card,
    render_text_card,
)
from item_index import ItemIndex, category_label, display_name  # noqa: E402
from pda_format import parse_pda_segments, strip_pda_formatting  # noqa: E402


def json_response(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


class APIClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_opens_circuit_after_repeated_5xx(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return json_response({"title": "down"}, status=503)

        health = ApiHealth()
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://example.test",
        ) as raw:
            api = StalzoneAPIClient(
                "id",
                "secret",
                "eu",
                client=raw,
                max_retries=0,
                retry_base_delay=0,
                health=health,
            )
            for _ in range(3):
                with self.assertRaises(ServerError):
                    await api.get_regions()
            with self.assertRaises(ServerError):
                await api.get_regions()
        self.assertEqual(calls, 3)
        snapshot = health.snapshot()
        self.assertEqual(snapshot["total"], 3)
        self.assertEqual(snapshot["failures"], 3)
        self.assertGreater(snapshot["circuit_seconds"], 0)

    async def test_success_and_auth_headers(self):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            path = request.url.path
            if path.endswith("/lots"):
                return json_response({"total": 1, "lots": [{"itemId": "y1q9"}]})
            if path.endswith("/history"):
                return json_response({"total": 1, "prices": [{"price": 1000}]})
            if path.endswith("/emission"):
                return json_response({"currentStart": "2026-10-22T05:00:00Z"})
            if "/profile" in path:
                return json_response({"username": "Test-1"})
            return json_response({}, 500)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.test"
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            await api.get_auction_lots("y1q9")
            await api.get_auction_history("y1q9")
            await api.get_emission()
            await api.get_profile("Test 1")

        self.assertEqual(seen[0].headers["Client-Id"], "cid")
        self.assertEqual(seen[0].headers["Client-Secret"], "secret")
        self.assertEqual(seen[0].url.path, "/eu/auction/y1q9/lots")
        self.assertEqual(seen[0].url.params["additional"], "true")
        self.assertEqual(seen[0].url.params["sort"], "current_price")
        self.assertEqual(seen[1].url.params["offset"], "0")
        self.assertEqual(seen[2].url.path, "/eu/emission")
        self.assertEqual(seen[3].url.path, "/eu/character/by-name/Test 1/profile")

    async def test_history_offset_is_forwarded(self):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return json_response({"total": 0, "prices": []})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.test"
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            await api.get_auction_history("y1q9", limit=50, offset=200)

        self.assertEqual(seen[0].url.params["limit"], "50")
        self.assertEqual(seen[0].url.params["offset"], "200")

    async def test_missing_credentials(self):
        with self.assertRaises(MissingCredentialsError):
            StalzoneAPIClient("", "", region="eu")

    async def test_404_maps_to_not_found(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: json_response({"title": "Not Found", "status": 404}, 404)
            ),
            base_url="https://api.test",
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            with self.assertRaises(NotFoundError):
                await api.get_profile("missing")

    async def test_401_maps_to_auth_error(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: json_response({"title": "Unauthorized", "status": 401}, 401)
            ),
            base_url="https://api.test",
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            with self.assertRaises(AuthenticationError):
                await api.get_emission()

    async def test_400_maps_to_bad_request(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: json_response({"title": "Bad Request", "status": 400}, 400)
            ),
            base_url="https://api.test",
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            with self.assertRaises(BadRequestError):
                await api.get_auction_lots("bad-id")

    async def test_429_maps_to_rate_limit(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: json_response({"title": "Too Many Requests", "status": 429}, 429)
            ),
            base_url="https://api.test",
        ) as http:
            api = StalzoneAPIClient(
                "cid", "secret", region="eu", client=http, max_retries=0
            )
            with self.assertRaises(RateLimitError):
                await api.get_emission()

    async def test_retry_429_then_success(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return json_response({"title": "Too Many Requests"}, 429)
            return json_response({"previousStart": "2026-10-22T03:00:00Z"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.test"
        ) as http:
            api = StalzoneAPIClient(
                "cid",
                "secret",
                region="eu",
                client=http,
                retry_base_delay=0.0,
            )
            payload = await api.get_emission()
        self.assertEqual(calls, 2)
        self.assertIn("previousStart", payload)

    async def test_timeout_maps_to_network_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.test"
        ) as http:
            api = StalzoneAPIClient(
                "cid", "secret", region="eu", client=http, max_retries=0
            )
            with self.assertRaises(NetworkError):
                await api.get_emission()

    async def test_non_json_response(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="oops")),
            base_url="https://api.test",
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            with self.assertRaises(ResponseError):
                await api.get_emission()

    async def test_empty_item_id_rejected(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: json_response({})),
            base_url="https://api.test",
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            with self.assertRaises(BadRequestError):
                await api.get_auction_lots("   ")

    def test_base_url_aliases(self):
        self.assertEqual(normalize_base_url("demo"), DEMO_BASE_URL)
        self.assertEqual(normalize_base_url("production"), "https://eapi.stalzone.com")
        self.assertEqual(normalize_base_url("https://example.test/"), "https://example.test")


class FormatterTests(unittest.TestCase):
    NOW = __import__("datetime").datetime(
        2026, 10, 22, 6, 0, tzinfo=__import__("datetime").timezone.utc
    )

    def test_auction_sorts_lots_by_effective_price(self):
        lots = {
            "total": 2,
            "lots": [
                {"amount": 1, "startPrice": 500, "buyoutPrice": 800, "endTime": "2026-10-22T15:00:00Z", "additional": {"ptn": 1}},
                {"amount": 2, "startPrice": 100, "buyoutPrice": 10000, "endTime": "2026-10-22T14:00:00Z", "additional": {"ptn": 15}},
            ],
        }
        history = {
            "total": 2,
            "prices": [
                {"amount": 1, "price": 1000, "time": "2026-10-22T05:00:00Z"},
                {"amount": 2, "price": 2400, "time": "2026-10-22T05:30:00Z"},
            ],
        }
        text = format_auction("y1q9", lots, history, "eu", now=self.NOW)
        self.assertIn("y1q9", text)
        self.assertIn("在售", text)
        self.assertIn("最近成交", text)
        self.assertIn("按买断价", text)
        self.assertLess(
            text.index("1. y1q9＋15  100"),
            text.index("2. y1q9＋1  500"),
        )
        self.assertLess(text.index("2,400 ×2"), text.index("  1,000"))

    def test_auction_quality_groups_and_levels(self):
        lots = {
            "total": 3,
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 1000,
                    "buyoutPrice": 1000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 5, "ptn": 15},
                },
                {
                    "amount": 1,
                    "startPrice": 1200,
                    "buyoutPrice": 1200,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 5, "ptn": 0},
                },
                {
                    "amount": 1,
                    "startPrice": 500,
                    "buyoutPrice": 500,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 3, "ptn": 1},
                },
            ],
        }
        history = {
            "total": 2,
            "prices": [
                {"amount": 1, "price": 900, "time": "2026-10-22T05:00:00Z", "additional": {"qlt": 5, "ptn": 15}},
                {"amount": 1, "price": 400, "time": "2026-10-22T04:00:00Z", "additional": {"qlt": 3, "ptn": 1}},
            ],
        }
        text = format_auction("wg53", lots, history, "eu", item_label="原子 / Atom", now=self.NOW)
        self.assertIn("【传奇】", text)
        self.assertIn("【稀有】", text)
        self.assertIn("原子＋15", text)
        self.assertIn("原子＋1", text)
        self.assertNotIn("原子＋0", text)
        self.assertIn("可按品质筛选", text)
        view = build_auction_view(
            "wg53", lots, history, "eu", item_label="原子 / Atom", now=self.NOW
        )
        self.assertEqual(
            [group["quality"] for group in view["recent_groups"]], [5, 3]
        )

    def test_common_quality_uses_title_white_not_fallback_grey(self):
        lots = {
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 1000,
                    "buyoutPrice": 1000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 0},
                }
            ]
        }
        view = build_auction_view(
            "wg53", lots, {}, "eu", item_label="原子 / Atom", now=self.NOW
        )
        self.assertEqual(QUALITY_COLORS[0], "#E7EDF5")
        rows = [
            row for row in view["active"] if not row.get("quality_header")
        ]
        self.assertEqual(rows[0]["quality"], 0)
        self.assertEqual(rows[0]["color"], "#E7EDF5")

    def test_item_rank_color(self):
        from formatters import item_rank_color

        self.assertEqual(item_rank_color("DEFAULT"), "#E7EDF5")
        self.assertEqual(item_rank_color("RANK_NEWBIE"), "#53C353")
        self.assertEqual(item_rank_color("RANK_STALKER"), "#4EA8FF")
        self.assertEqual(item_rank_color("RANK_VETERAN"), "#FF6FB5")
        self.assertEqual(item_rank_color("RANK_MASTER"), "#FF5C5C")
        self.assertEqual(item_rank_color("RANK_LEGEND"), "#FFD166")

    def test_non_artifact_history_flat_ten(self):
        lots = {
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 100,
                    "buyoutPrice": 200,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 0},
                },
                {
                    "amount": 1,
                    "startPrice": 300,
                    "buyoutPrice": 300,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 0},
                },
            ]
        }
        history = {
            "prices": [
                {
                    "amount": 1,
                    "price": 1000 + index,
                    "time": f"2026-10-22T{index:02d}:00:00Z",
                    "additional": {"qlt": 0 if index % 2 else 3},
                }
                for index in range(10)
            ]
        }
        view = build_auction_view(
            "7l9d3",
            lots,
            history,
            "eu",
            now=self.NOW,
            item_label="高级账户 180天",
            non_artifact=True,
            item_color="#E7EDF5",
        )
        self.assertEqual(view["recent_total_limit"], 10)
        self.assertEqual(len(view["recent_groups"]), 1)
        self.assertEqual(view["recent_groups"][0]["label"], "")
        self.assertEqual(view["recent_groups"][0]["quality"], None)
        self.assertEqual(len(view["recent_groups"][0]["rows"]), 10)
        self.assertEqual(view["recent_groups"][0]["rows"][0]["color"], "#E7EDF5")
        marked = [
            row for row in view["recent_groups"][0]["rows"] if row.get("lowest")
        ]
        self.assertEqual(len(marked), 1)
        self.assertEqual(marked[0]["price"], "1,000")
        self.assertEqual(view["active"][0]["color"], "#E7EDF5")
        self.assertEqual(view["active"][0]["buyout"], "300")
        self.assertEqual(view["active"][0]["start"], "300")
        text = format_auction_text(view)
        self.assertIn("最近成交（最多 10 条，按时间倒序）", text)
        self.assertIn("高级账户 180天", text)
        self.assertIn("名称  起拍  买断  剩余时间", text)
        self.assertNotIn("名称  起拍  买断  单价", text)

    def test_non_artifact_stacked_unit_price(self):
        lots = {
            "lots": [
                {
                    "amount": 10,
                    "startPrice": 5000,
                    "buyoutPrice": 6000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {},
                },
                {
                    "amount": 5,
                    "startPrice": 3000,
                    "buyoutPrice": 4000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {},
                },
                {
                    "amount": 20,
                    "startPrice": 9000,
                    "buyoutPrice": 10000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {},
                },
            ]
        }
        history = {
            "prices": [
                {"amount": 10, "price": 5500, "time": "2026-10-22T03:00:00Z"},
                {"amount": 5, "price": 4000, "time": "2026-10-22T04:00:00Z"},
                {"amount": 2, "price": 2400, "time": "2026-10-22T05:00:00Z"},
            ]
        }
        view = build_auction_view(
            "cig",
            lots,
            history,
            "eu",
            now=self.NOW,
            item_label="香烟",
            non_artifact=True,
            item_color="#E7EDF5",
        )
        active = view["active"]
        self.assertTrue(view["quantity_mode"])
        self.assertEqual(len(active), 6)
        self.assertEqual(
            [row["offer_label"] for row in active],
            ["竞拍", "竞拍", "买断", "竞拍", "买断", "买断"],
        )
        self.assertEqual(
            [row["unit_price"] for row in active],
            ["450", "500", "500", "600", "600", "800"],
        )
        self.assertEqual(active[0]["name"], "香烟×20")
        self.assertNotIn("lowest", active[0])
        rows = view["recent_groups"][0]["rows"]
        self.assertEqual([row["unit_price"] for row in rows], ["1,200", "800", "550"])
        self.assertTrue(rows[-1]["lowest"])
        self.assertEqual(rows[-1]["name"], "香烟×10")
        text = format_auction_text(view)
        self.assertIn("香烟×20", text)
        self.assertIn("[最低单价]", text)

    def test_auction_quality_filter(self):
        lots = {
            "total": 1,
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 1000,
                    "buyoutPrice": 1000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 5, "ptn": 15},
                }
            ],
        }
        text = format_auction(
            "wg53", lots, {}, "eu", item_label="原子 / Atom", quality_filter=5, now=self.NOW
        )
        self.assertIn("仅看品质：传奇", text)
        self.assertIn("原子＋15", text)
        self.assertNotIn("可按品质筛选", text)

    def test_parse_quality_query(self):
        from formatters import parse_quality_query

        self.assertEqual(parse_quality_query("原子 粉"), ("原子", 3))
        self.assertEqual(parse_quality_query("原子 稀有"), ("原子", 3))
        self.assertEqual(parse_quality_query("原子 legendary"), ("原子", 5))
        self.assertEqual(parse_quality_query("原子"), ("原子", None))

    def test_parse_auction_query_date_and_count(self):
        from datetime import date, datetime, timezone

        now = datetime(2026, 10, 22, 6, 0, tzinfo=timezone.utc)
        self.assertEqual(
            parse_auction_query("原子 粉 6.11 20", now=now),
            ("原子", 3, date(2026, 6, 11), 20),
        )
        self.assertEqual(
            parse_auction_query("原子 6/11", now=now),
            ("原子", None, date(2026, 6, 11), None),
        )
        self.assertEqual(
            parse_auction_query("原子 粉 25.6.11", now=now),
            ("原子", 3, date(2025, 6, 11), None),
        )
        self.assertEqual(
            parse_auction_query("寒冰 / Chilly 粉 2025/6/11 7", now=now),
            ("寒冰 / Chilly", 3, date(2025, 6, 11), 7),
        )
        self.assertEqual(
            parse_auction_query("原子 粉", now=now),
            ("原子", 3, None, None),
        )
        with self.assertRaises(ValueError):
            parse_auction_query("原子 6.11 20", now=now)
        with self.assertRaises(ValueError):
            parse_auction_query("原子 粉 6.11 201", now=now)

    def test_auction_date_filters_history_and_limits(self):
        from datetime import date, datetime, timedelta, timezone

        base = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
        history = {
            "prices": [
                {
                    "amount": 1,
                    "price": 1000 + index,
                    "time": (base + timedelta(hours=index)).isoformat().replace("+00:00", "Z"),
                    "additional": {"qlt": 3},
                }
                for index in range(25)
            ]
        }
        history["prices"].append(
            {
                "amount": 1,
                "price": 9999,
                "time": "2026-06-11T16:00:00Z",  # 6/12 00:00 UTC+8
                "additional": {"qlt": 3},
            }
        )
        history["prices"].extend(
            {
                "amount": 1,
                "price": 800 + index,
                "time": (base + timedelta(hours=index)).isoformat().replace("+00:00", "Z"),
                "additional": {"qlt": 0},
            }
            for index in range(8)
        )
        lots = {
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 500,
                    "buyoutPrice": 600,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {"qlt": 3},
                }
            ]
        }
        cutoff = auction_day_cutoff(date(2026, 6, 11))

        view = build_auction_view(
            "wg53",
            lots,
            history,
            "eu",
            now=self.NOW,
            item_label="原子 / Atom",
            quality_filter=3,
            before=cutoff,
            history_limit=20,
        )
        self.assertTrue(view["history_only"])
        self.assertEqual(view["active"], [])
        self.assertEqual(view["before"], "2026/6/11")
        self.assertEqual(len(view["recent_groups"]), 1)
        self.assertEqual(len(view["recent_groups"][0]["rows"]), 20)
        self.assertNotIn(
            "2026/6/12",
            [row["time"] for row in view["recent_groups"][0]["rows"]],
        )

        all_qualities = build_auction_view(
            "wg53",
            lots,
            history,
            "eu",
            now=self.NOW,
            item_label="原子 / Atom",
            before=cutoff,
        )
        self.assertEqual(
            [len(group["rows"]) for group in all_qualities["recent_groups"]],
            [5, 5],
        )

        text = format_auction(
            "wg53",
            lots,
            history,
            "eu",
            now=self.NOW,
            item_label="原子 / Atom",
            quality_filter=3,
            before=cutoff,
            history_limit=20,
        )
        self.assertIn("历史成交", text)
        self.assertIn("截至 2026/6/11", text)
        self.assertIn("最多 20 条", text)
        self.assertNotIn("在售", text)
        self.assertNotIn("最近成交", text)

    def test_auction_caps_high_volume_rows(self):
        lots = {
            "total": 40,
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 1000 + i,
                    "buyoutPrice": 2000 + i,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {"qlt": 4},
                }
                for i in range(40)
            ],
        }
        history = {
            "total": 1,
            "prices": [
                {
                    "amount": 1,
                    "price": 2000,
                    "time": "2026-10-24T05:00:00Z",
                    "additional": {"qlt": 4},
                }
            ],
        }
        view = build_auction_view(
            "wg53",
            lots,
            history,
            "ru",
            now=self.NOW,
            item_label="原子 / Atom",
            non_artifact=True,
        )
        self.assertIsNotNone(view)
        self.assertEqual(view["active_total"], 40)
        self.assertTrue(view["active_truncated"])
        self.assertEqual(len(view["active"]), 31)
        self.assertTrue(view["active"][15].get("ellipsis"))
        self.assertTrue(any(row.get("lowest") for row in view["active"]))
        text = format_auction_text(view)
        self.assertIn("共 40 条，显示前 15 条和后 15 条", text)
        self.assertIn("中间省略 10 条", text)

    def test_artifact_cap_keeps_cheapest_row_per_level(self):
        lots = {
            "total": 40,
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 1000 + i,
                    "buyoutPrice": 2000 + i,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {"qlt": 3, "ptn": i % 10},
                }
                for i in range(40)
            ],
        }
        view = build_auction_view(
            "wg53",
            lots,
            {"total": 0, "prices": []},
            "ru",
            now=self.NOW,
            item_label="原子 / Atom",
        )
        self.assertIsNotNone(view)
        self.assertEqual(view["active_total"], 40)
        self.assertTrue(view["active_grouped"])
        rows = [
            row for row in view["active"] if not row.get("quality_header")
        ]
        self.assertEqual(len(rows), 10)
        self.assertEqual(
            [row["level"] for row in rows], list(range(9, -1, -1))
        )
        self.assertEqual({row["level_count"] for row in rows}, {4})
        text = format_auction_text(view)
        self.assertIn("按品质分组显示每级最低价", text)
        self.assertIn("其他品质按 +等级保留最低价，组内按价格倒序", text)

    def test_artifact_gold_does_not_trigger_limit(self):
        lots = []
        for i in range(30):
            lots.append(
                {
                    "amount": 1,
                    "startPrice": 1000 + i,
                    "buyoutPrice": 2000 + i,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {"qlt": 3, "ptn": i % 10},
                }
            )
        for i in range(6):
            lots.append(
                {
                    "amount": 1,
                    "startPrice": 50000 + i,
                    "buyoutPrice": 60000 + i,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {"qlt": 5, "ptn": i},
                }
            )
        view = build_auction_view(
            "wg53",
            {"total": 36, "lots": lots},
            {"total": 0, "prices": []},
            "ru",
            now=self.NOW,
            item_label="原子 / Atom",
        )
        self.assertIsNotNone(view)
        self.assertFalse(view["active_truncated"])
        self.assertFalse(view["active_grouped"])
        self.assertEqual(len(view["active"]), 36)
        self.assertFalse(any(row.get("quality_header") for row in view["active"]))

    def test_red_gold_artifacts_all_shown_when_grouped(self):
        lots = []
        for i in range(31):
            lots.append(
                {
                    "amount": 1,
                    "startPrice": 1000 + i,
                    "buyoutPrice": 2000 + i,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {"qlt": 3, "ptn": i % 8},
                }
            )
        for i in range(3):
            lots.append(
                {
                    "amount": 1,
                    "startPrice": 50000 + i,
                    "buyoutPrice": 60000 + i,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {"qlt": 5, "ptn": 0},
                }
            )
        view = build_auction_view(
            "wg53",
            {"total": 34, "lots": lots},
            {"total": 0, "prices": []},
            "ru",
            now=self.NOW,
            item_label="原子 / Atom",
        )
        self.assertIsNotNone(view)
        self.assertTrue(view["active_grouped"])
        gold_rows = [
            row
            for row in view["active"]
            if row.get("quality") == 5 and not row.get("quality_header")
        ]
        self.assertEqual(len(gold_rows), 3)
        headers = [
            row["name"] for row in view["active"] if row.get("quality_header")
        ]
        self.assertTrue(any("全部显示" in name for name in headers))

    def test_stackable_auction_uses_cheapest_row_per_amount(self):
        lots = []
        for amount in (1, 2, 5, 10, 100):
            for offset in (0, 10, 20):
                lots.append(
                    {
                        "amount": amount,
                        "startPrice": amount * 1000 + offset,
                        "buyoutPrice": amount * 1200 + offset,
                        "endTime": "2026-10-25T06:00:00Z",
                        "additional": {},
                    }
                )
        view = build_auction_view(
            "y1q9",
            {"total": len(lots), "lots": lots},
            {"total": 0, "prices": []},
            "ru",
            now=self.NOW,
            item_label="弹药 / Ammo",
            non_artifact=True,
        )
        self.assertIsNotNone(view)
        self.assertTrue(view["quantity_mode"])
        self.assertEqual(view["quantity_count"], 5)
        self.assertEqual(view["active_total"], 15)
        self.assertEqual(len(view["active"]), 10)
        self.assertEqual(
            [row["offer_kind"] for row in view["active"]],
            ["auction"] * 5 + ["buyout"] * 5,
        )
        self.assertEqual(
            [row["amount"] for row in view["active"]],
            [1, 2, 5, 10, 100, 1, 2, 5, 10, 100],
        )
        self.assertTrue(
            all(
                row["offer_unit_value"]
                == min(
                    (
                        item.get("buyoutPrice")
                        if row["offer_kind"] == "buyout"
                        else item.get("startPrice")
                    )
                    / max(1, item["amount"])
                    for item in lots
                    if item["amount"] == row["amount"]
                )
                for row in view["active"]
            )
        )
        text = format_auction_text(view)
        self.assertIn("按数量汇总", text)
        self.assertIn("5 种数量 / 15 条在售", text)
        self.assertIn("竞拍 · 1,000", text)
        self.assertNotIn("[买断]", text)

    def test_stackable_auction_omits_auction_when_not_cheaper(self):
        lots = {
            "total": 2,
            "lots": [
                {
                    "amount": 2,
                    "startPrice": 5000,
                    "buyoutPrice": 1000,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {},
                },
                {
                    "amount": 5,
                    "startPrice": 1000,
                    "buyoutPrice": 5000,
                    "endTime": "2026-10-25T06:00:00Z",
                    "additional": {},
                },
            ],
        }
        view = build_auction_view(
            "y1q9",
            lots,
            {"total": 0, "prices": []},
            "ru",
            now=self.NOW,
            item_label="弹药 / Ammo",
            non_artifact=True,
        )
        self.assertIsNotNone(view)
        amount_two = [
            row for row in view["active"] if row["amount"] == 2
        ]
        self.assertEqual(len(amount_two), 1)
        self.assertEqual(amount_two[0]["offer_kind"], "buyout")
        amount_five = [
            row for row in view["active"] if row["amount"] == 5
        ]
        self.assertEqual(
            [row["offer_kind"] for row in amount_five],
            ["auction", "buyout"],
        )

    def test_auction_empty(self):
        text = format_auction("nope", {}, {}, "ru", now=self.NOW)
        self.assertIn("未找到相关数据", text)

    def test_emission_active_and_previous(self):
        text = format_emission(
            {
                "currentStart": "2026-10-22T05:00:00Z",
                "previousStart": "2026-10-22T03:00:00Z",
                "previousEnd": "2026-10-22T03:30:00Z",
            },
            "eu",
            now=self.NOW,
        )
        self.assertIn("进行中", text)
        self.assertIn("上次爆发", text)
        self.assertNotIn("下一次爆发：", text)

    def test_emission_inactive(self):
        text = format_emission(
            {"previousStart": "2026-10-22T03:00:00Z", "previousEnd": "2026-10-22T03:30:00Z"},
            "ru",
            now=self.NOW,
        )
        self.assertIn("无辐射爆发", text)
        self.assertIn("距离上次风暴", text)
        self.assertIn("2小时30分00秒", text)

    def test_format_diag(self):
        text = format_diag(
            {
                "version": "9.9.9",
                "system": "Linux",
                "python": "3.12.0",
                "region": "EU",
                "api_base": "https://eapi.stalzone.com",
                "env": "生产环境",
                "render_mode": "auto",
                "font": "自动查找",
                "credentials": "已配置",
                "items": 2615,
                "details": 1338,
                "balance_patches": 168,
                "pending": 2,
                "http": "已建立",
                "cache_entries": 3,
                "cache_hits": 8,
                "cache_misses": 2,
                "api_requests": 10,
                "api_successes": 8,
                "api_failures": 2,
                "api_last_status": 503,
                "api_last_latency": 1200,
                "api_avg_latency": 640,
                "api_last_path": "/eu/emission",
                "api_last_error": "HTTP 503: down",
                "api_circuit_seconds": 12,
                "auto_status": "已启用",
                "auto_window": "2–4 小时窗口内",
                "auto_whitelist": 2,
                "auto_targets": 2,
                "auto_last_check": "10-24 12:00",
                "auto_last_send": "成功 2 / 失败 0 · 10-24 12:00",
                "auto_last_error": "—",
            }
        )
        self.assertIn("STALZONE · 运行诊断", text)
        self.assertIn("插件 9.9.9", text)
        self.assertIn("物品索引：2,615 件", text)
        self.assertIn("缓存命中率：80%", text)
        self.assertIn("请求 / 失败：10 / 2", text)
        self.assertIn("自动提醒", text)

    def test_emission_view_active_and_idle(self):
        self.assertEqual(format_elapsed_hms(3661), "1小时01分01秒")
        idle = build_emission_view(
            {
                "previousStart": "2026-10-22T03:00:00Z",
                "previousEnd": "2026-10-22T03:30:00Z",
            },
            "ru",
            now=self.NOW,
        )
        self.assertEqual(idle["headline"], "距离上次风暴")
        self.assertEqual(idle["elapsed_text"], "2小时30分00秒")
        self.assertEqual(idle["state_label"], "无辐射爆发")
        self.assertEqual(idle["region"], "RU")
        self.assertIn("11:30", idle["reference_line"])

        active = build_emission_view(
            {
                "currentStart": "2026-10-22T05:00:00Z",
                "previousStart": "2026-10-22T03:00:00Z",
                "previousEnd": "2026-10-22T03:30:00Z",
            },
            "eu",
            now=self.NOW,
        )
        self.assertEqual(active["headline"], "本次风暴已持续")
        self.assertEqual(active["elapsed_text"], "1小时00分00秒")
        self.assertEqual(active["state_label"], "风暴进行中")
        self.assertEqual(active["state_key"], "active")

    def test_emission_alert_view(self):
        view = build_emission_alert_view(
            {
                "currentStart": "2026-10-22T05:00:00Z",
                "previousStart": "2026-10-22T03:00:00Z",
                "previousEnd": "2026-10-22T03:30:00Z",
            },
            "eu",
            now=__import__("datetime").datetime(
                2026, 10, 22, 5, 17, tzinfo=__import__("datetime").timezone.utc
            ),
        )
        self.assertEqual(view["headline"], "风暴已开始")
        self.assertEqual(view["region"], "EU")
        self.assertEqual(view["start_clock"], "13:00")
        self.assertEqual(view["start_date"], "2026-10-22")
        self.assertEqual(view["elapsed_text"], "17分00秒")
        self.assertEqual(view["start_time"], "2026-10-22 13:00:00 UTC+8")
        self.assertIn("风暴结束后 30 分钟内将伴随神器爆发", view["text"])
        self.assertIn("Tip：神器会在大世界的各处异常点中生成", view["text"])
        self.assertIn("更多功能：sz help 获取菜单", view["text"])
        self.assertIn("辐射风暴已开始", view["text"])
        self.assertIn("请尽快上线", view["text"])
        self.assertNotIn("检测时间", view["text"])
        self.assertEqual(build_emission_alert_view({}, "eu"), {})

    def test_emission_alert_uses_actual_start(self):
        view = build_emission_alert_view(
            {"currentStart": "2026-10-22T05:00:00Z"},
            "eu",
            now=__import__("datetime").datetime(
                2026, 10, 22, 5, 1, tzinfo=__import__("datetime").timezone.utc
            ),
        )
        self.assertEqual(view["start_clock"], "13:00")
        self.assertEqual(view["elapsed_text"], "1分00秒")
        self.assertIn("实际开始：2026-10-22 13:00:00 UTC+8", view["text"])

    def test_profile_fields(self):
        payload = {
            "username": "Test-1",
            "uuid": "abc",
            "status": "offline",
            "alliance": "duty",
            "lastLogin": "2026-10-21T12:00:00Z",
            "displayedAchievements": ["playtime"],
            "clan": {
                "info": {"name": "Clan #1", "tag": "TAG", "level": 2},
                "member": {"name": "Test-1", "rank": "LEADER"},
            },
            "stats": [
                {"id": "level", "type": "INTEGER", "value": {"value": 42}},
                {"id": "playtime", "type": "DURATION", "value": {"seconds": 3600}},
            ],
        }
        text = format_profile(payload, "eu", now=self.NOW)
        self.assertIn("Test-1", text)
        self.assertIn("纪律", text)
        self.assertIn("Clan #1 [TAG]", text)
        self.assertIn("LEADER", text)
        self.assertIn("等级：42", text)

    def test_hq_pvp_score_formula(self):
        stats = [
            {"id": "kil", "type": "INTEGER", "value": 12682},
            {"id": "ast", "type": "INTEGER", "value": 6008},
            {"id": "bul-dea", "type": "INTEGER", "value": 10313},
            {"id": "exp-dea", "type": "INTEGER", "value": 1040},
            {"id": "ble-to-dea", "type": "INTEGER", "value": 77},
            {"id": "col-dea", "type": "INTEGER", "value": 92},
        ]
        hq = calculate_hq_pvp_score(stats)
        self.assertIsNotNone(hq)
        self.assertEqual(hq["deaths"], 11522)
        self.assertEqual(hq["kills"], 12682)
        self.assertEqual(hq["assists"], 6008)
        self.assertEqual(hq["score"], 4125)

    def test_profile_long_name_renders_without_overflow(self):
        payload = {
            "username": "Extremely_Long_Player_Name_That_Must_Not_Overflow",
            "status": "online",
            "alliance": "duty",
            "lastLogin": "2026-10-22T05:59:00Z",
            "stats": [],
        }
        view = build_profile_view(payload, "eu", now=self.NOW)
        if not find_cjk_font():
            self.skipTest("CJK font unavailable")
        path = render_profile_card(view)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        path.unlink(missing_ok=True)

    def test_hq_current_formula_and_fight_stats(self):
        stats = [
            {"id": "kil", "value": 42083},
            {"id": "kills-bf", "value": 11053},
            {"id": "ast", "value": 16434},
            {"id": "dea", "value": 60286},
            {"id": "bul-dea", "value": 30000},
            {"id": "col-dea", "value": 20000},
            {"id": "exp-dea", "value": 5000},
            {"id": "ble-to-dea", "value": 878},
            {"id": "deaths-bf", "value": 19695},
            {"id": "ano-dea", "value": 627},
            {"id": "won-fights-personal", "value": 1347},
            {"id": "won-fights-equal", "value": 149},
            {"id": "fights-part", "value": 2516},
            {"id": "won-bf", "value": 533},
            {"id": "lost-bf", "value": 634},
            {"id": "part-bf", "value": 1167},
        ]
        hq = calculate_hq_pvp_score(stats)
        self.assertIsNotNone(hq)
        self.assertEqual(hq["kills"], 31030)
        self.assertEqual(hq["deaths"], 36183)
        self.assertEqual(hq["score"], 3286)
        self.assertEqual(hq["wins"], 1496)
        self.assertEqual(hq["losses"], 1020)
        self.assertEqual(hq["win_rate"], 1496 * 100 / 2516)
        self.assertEqual(hq["kd"], 31030 / 36183)
        self.assertEqual(hq["kd_total"], 42083 / 60286)

    def test_profile_hq_section(self):
        payload = {
            "username": "Sakura_Akira",
            "status": "online",
            "alliance": "duty",
            "stats": [
                {"id": "kil", "type": "INTEGER", "value": 12682},
                {"id": "ast", "type": "INTEGER", "value": 6008},
                {"id": "bul-dea", "type": "INTEGER", "value": 10313},
                {"id": "exp-dea", "type": "INTEGER", "value": 1040},
                {"id": "ble-to-dea", "type": "INTEGER", "value": 77},
            ],
        }
        text = format_profile(
            payload,
            "eu",
            hq_url="https://stalzonehq.com/characters/EU/SAKURA_AKIRA",
            lunar_url=None,
        )
        self.assertIn("开放世界 PvP", text)
        self.assertIn("PvP Score：4,158", text)
        self.assertIn("大世界 PvP 死亡（估算）：11,430", text)
        self.assertIn("StalzoneHQ", text)

    def test_profile_lunar_section(self):
        payload = {
            "username": "Sakura_Akira",
            "status": "online",
            "alliance": "freedom",
            "lastLogin": "2026-10-22T05:00:00Z",
            "stats": [],
        }
        lunar = {
            "player": {
                "kd": 2.84,
                "kda": 4.09,
                "total_score": 43164,
                "matches_count": 5,
                "total_kills": 128,
                "total_deaths": 45,
                "total_assists": 56,
                "clan_name": "Grand Fleet",
                "clan_tag": "SURF",
            },
            "matches": [
                {"date": "2026-04-24 00:00:00", "opponent": "Foo", "result": "win", "kills": 30, "deaths": 13, "score": 8774}
            ],
        }
        text = format_profile(payload, "eu", lunar=lunar, lunar_url="https://lunar-zone.com/players/eu/Sakura_Akira")
        self.assertIn("自由", text)
        self.assertIn("K/D：2.84", text)
        self.assertIn("战斗分：43,164", text)
        self.assertIn("Lunar 第三方", text)

    def test_time_is_utc_plus_8(self):
        text = format_emission(
            {"previousStart": "2026-10-22T03:00:00Z", "previousEnd": "2026-10-22T03:30:00Z"},
            "eu",
            now=__import__("datetime").datetime(2026, 10, 22, 6, 0, tzinfo=__import__("datetime").timezone.utc),
        )
        self.assertIn("14:00:00 UTC+8", text)
        self.assertIn("11:30 UTC+8", text)

    def test_profile_missing_stats_does_not_crash(self):
        payload = {"username": "Solo", "status": "online"}
        view = build_profile_view(payload, "ru", now=self.NOW)
        text = format_profile(payload, "ru", now=self.NOW, view=view)
        self.assertIn("Solo", text)
        self.assertIn("API 未返回", text)
        self.assertNotIn("无 / API 未返回", text)
        self.assertEqual(view["clan_label"], "—")
        self.assertEqual(view["clan_rank"], "—")
        self.assertFalse(view["has_clan"])

    def test_help(self):
        text = format_help("eu")
        self.assertIn("/sz auction", text)
        self.assertIn("EU", text)


class BalanceHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = BalanceHistory(PLUGIN_ROOT / "balance_history.json")

    def test_weapon_history(self):
        result = self.history.search(["AK-308", "АК-308"])
        self.assertTrue(result["patches"])
        self.assertIn("2026-07-22", [patch["date"] for patch in result["patches"]])
        text = "\n".join(
            change
            for patch in result["patches"]
            for change in patch["changes"]
        )
        self.assertIn("Damage: 39.8 → 39.1", text)

    def test_artifact_history(self):
        result = self.history.search(["Polyhedron"])
        self.assertTrue(result["patches"])
        self.assertIn("2026-01-14", [patch["date"] for patch in result["patches"]])
        text = "\n".join(
            change
            for patch in result["patches"]
            for change in patch["changes"]
        )
        self.assertIn("78.5 → 45", text)
        self.assertNotIn("Damage to mutant", text)

    def test_item_without_history(self):
        result = self.history.search(["Hunter’s Suit", "猎人套装"])
        self.assertEqual(result, {"rows": [], "patches": []})

    def test_historical_artifact_patchnotes(self):
        result = self.history.search(["Spiral", "螺旋", "Спираль", "gyq5"])
        dates = {patch["date"] for patch in result["patches"]}
        self.assertTrue(
            {
                "2026-06-03",
                "2026-01-14",
                "2025-11-12",
                "2025-09-03",
                "2023-12-20",
                "2023-10-11",
            }.issubset(dates)
        )
        changes = "\n".join(
            change
            for patch in result["patches"]
            for change in patch["changes"]
        )
        self.assertIn("Healing Effectiveness: 7.2% → 6.1%", changes)
        self.assertIn("Stability → -6.80%", changes)
        self.assertIn("Speed 2.8 → 2.5", changes)
        self.assertNotIn("too powerful", changes)

    def test_all_history_patches_are_rendered(self):
        patches = [
            {
                "date": f"2025-01-{day:02d}",
                "title": "Patch Notes",
                "changes": [f"伤害：{day} → {day + 1}"],
            }
            for day in range(1, 13)
        ]
        text = format_balance_history(
            "测试武器", {"rows": [], "patches": patches}
        )
        for day in range(1, 13):
            self.assertIn(f"2025-01-{day:02d}", text)

    def test_no_history_uses_short_card_title(self):
        text = format_balance_history(
            "猎人套装 / Hunter’s Suit", {"rows": [], "patches": []}
        )
        self.assertTrue(text.startswith("━━"))
        self.assertIn("STALZONE · 平衡调整", text)
        self.assertIn("没有找到该物品的平衡调整记录", text)
        self.assertNotIn("没有找到「", text)


class PDAFormattingTests(unittest.TestCase):
    def test_preset_and_reset(self):
        runs = parse_pda_segments("A§0B§6C§RD")
        self.assertEqual(
            runs,
            [
                ("A", "#FFFFFF"),
                ("B", "#000000"),
                ("C", "#FFAA00"),
                ("D", "#FFFFFF"),
            ],
        )

    def test_custom_colour_and_gradient(self):
        runs = parse_pda_segments("§#F3CF6FF§#F4CD66r")
        self.assertEqual(
            runs,
            [("F", "#F3CF6F"), ("r", "#F4CD66")],
        )
        self.assertEqual(strip_pda_formatting("§6橙色§R文字"), "橙色文字")

    def test_profile_card_with_pda_intro(self):
        payload = {
            "username": "Jackal",
            "status": "      §#F3CF6FPSYOPs§R Department\n§6CEO§7 / NA",
            "alliance": "mercenary",
            "stats": [
                {"id": "kil", "type": "INTEGER", "value": 100},
                {"id": "ast", "type": "INTEGER", "value": 20},
                {"id": "bul-dea", "type": "INTEGER", "value": 30},
                {"id": "exp-dea", "type": "INTEGER", "value": 5},
                {"id": "ble-to-dea", "type": "INTEGER", "value": 2},
            ],
        }
        view = build_profile_view(payload, "na")
        text = format_profile(payload, "na", view=view)
        self.assertIn("简介", text)
        self.assertIn("PSYOPs Department", text)
        self.assertNotIn("§", text)
        if find_cjk_font():
            path = render_profile_card(view)
            self.assertIsNotNone(path)
            path.unlink(missing_ok=True)


class SeasonPassTests(unittest.TestCase):
    def test_daily_and_weekly_xp_tables(self):
        self.assertEqual(daily_task_xp(7), 3500)
        self.assertEqual(daily_task_xp(15), 5500)
        self.assertEqual(daily_task_xp(45), 7750)
        self.assertEqual(daily_task_xp(100), 9125)
        self.assertEqual(weekly_reward(14), 0)
        self.assertEqual(weekly_reward(15), 3000)
        self.assertEqual(weekly_reward(45), 8000)
        self.assertEqual(weekly_reward(100), 20000)

    def test_example_calculation(self):
        result = calculate(*parse_arguments("15 15+2 20"))
        self.assertEqual(result.daily_total_xp, 6000)
        self.assertEqual(result.weekly_tasks, 105)
        self.assertEqual(result.weekly_reward_xp, 20000)
        self.assertEqual(result.weekly_xp, 58500)
        self.assertEqual(result.weekly_total_xp, 62000)
        self.assertEqual(result.full_weeks, 2)
        self.assertEqual(result.overloads_used, 40)
        self.assertEqual(result.season_base_xp, 158000)
        self.assertEqual(result.season_total_xp, 168000)
        self.assertEqual(result.final_level_without_overload, 173)
        self.assertEqual(result.final_level_with_overload, 183)

    def test_overload_cap(self):
        result = calculate(*parse_arguments("15 20+20 20"))
        self.assertEqual(result.effective_overloads, 15)
        self.assertEqual(result.daily_base_xp, 5875)
        self.assertEqual(result.daily_overload_xp, 3750)
        self.assertEqual(result.daily_total_xp, 9625)

    def test_no_overload_hides_overload_prediction(self):
        text = format_season_pass(calculate(*parse_arguments("15 15 20")))
        self.assertIn("预测等级：15 → 173 级", text)
        self.assertNotIn("不使用超载", text)
        self.assertNotIn("使用超载", text)
        self.assertNotIn("不用超载", text)

    def test_four_parameter_overload_form(self):
        self.assertEqual(
            parse_arguments("15 15 3 20"),
            (15, 15, 3, 20, 7),
        )
        self.assertEqual(
            parse_arguments("15 15 3 20 5"),
            (15, 15, 3, 20, 5),
        )
        self.assertEqual(
            parse_arguments("15 15 0 20 5"),
            (15, 15, 0, 20, 5),
        )
        self.assertEqual(
            parse_arguments("15 15+3 20 5"),
            (15, 15, 3, 20, 5),
        )
        self.assertEqual(
            parse_arguments("15 15 20"),
            (15, 15, 0, 20, 7),
        )


class ParserTests(unittest.TestCase):
    def test_command_variants(self):
        cases = {
            "/sz auction y1q9": ("auction", "y1q9"),
            "sz auction y1q9": ("auction", "y1q9"),
            "sz 拍卖 y1q9": ("auction", "y1q9"),
            "SZ 风暴": ("emission", ""),
            "stalzone auction y1q9": ("auction", "y1q9"),
            "auction y1q9": ("auction", "y1q9"),
            "/sz@bot profile Test 1": ("player", "Test 1"),
            "/sz": ("", ""),
            "帮助": ("help", ""),
            "/sz 拍卖 y1q9": ("auction", "y1q9"),
            "/sz 区服": ("regions", ""),
            "/sz 行动": ("operations", ""),
            "/sz diag": ("diag", ""),
            "/sz 诊断": ("diag", ""),
            "/sz 状态": ("diag", ""),
            "/sz 运行状态": ("diag", ""),
            "/sz 战队列表": ("clans", ""),
            "/sz 市场 y1q9": ("auction", "y1q9"),
            "/sz 交易行 y1q9": ("auction", "y1q9"),
            "/sz 风暴": ("emission", ""),
            "/sz fb": ("emission", ""),
            "/sz FB ru": ("emission", "ru"),
            "/sz 玩家 Sakura": ("player", "Sakura"),
            "/sz 角色 Sakura": ("player", "Sakura"),
            "/sz profile Sakura": ("player", "Sakura"),
            "/sz 物品 寒冰": ("item", "寒冰"),
            "/sz 调整 AK-308": ("balance", "AK-308"),
            "/sz 调整历史 多面体": ("balance", "多面体"),
            "/sz 候选 1": ("candidate", "1"),
            "sz 候选 2": ("candidate", "2"),
            "/sz 通行证 15 15+2 20": ("pass", "15 15+2 20"),
            "/sz 通行证计算器 15 15 20": ("pass", "15 15 20"),
            "/sz 战队 Clan": ("clan", "Clan"),
        }
        for raw, expected in cases.items():
            self.assertEqual(parse_command(raw), expected, raw)


class V2APIClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_region_override_path(self):
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.path)
            return json_response({"username": "Test-1"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.test"
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            await api.get_profile("Test-1", region="ru")
            await api.get_profile_by_uuid(
                "5c7e0994-bc22-4190-9774-5f197b1500e6", region="na"
            )
            await api.get_profile("Test-1")

        self.assertEqual(
            seen,
            [
                "/ru/character/by-name/Test-1/profile",
                "/na/character/by-uuid/5c7e0994-bc22-4190-9774-5f197b1500e6/profile",
                "/eu/character/by-name/Test-1/profile",
            ],
        )

    async def test_new_public_endpoints(self):
        clan = {
            "id": "647d6c53-b3d7-4d30-8d08-de874eb1d845",
            "name": "Clan #1",
            "tag": "TAG",
            "level": 2,
            "levelPoints": 100,
            "alliance": "covenant",
            "memberCount": 1,
            "leader": "Test-1",
        }
        session = {
            "id": 1,
            "map": "operation_bigcleanup",
            "difficulty": 3,
            "sessionDurationSeconds": 1200,
            "endTime": "2026-10-22T05:00:00Z",
            "participants": [{"username": "Test-1"}],
        }
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            path = request.url.path
            if path == "/regions":
                return httpx.Response(200, json=[{"id": "EU", "name": "EUROPE"}])
            if "/character/by-uuid/" in path:
                return json_response({"username": "Test-1"})
            if path.endswith("/clans"):
                return json_response({"totalClans": 1, "data": [clan]})
            if path.endswith("/info"):
                return json_response(clan)
            if path.endswith("/operations/sessions"):
                return json_response({"total": 1, "sessions": [session]})
            return json_response({}, 500)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.test"
        ) as http:
            api = StalzoneAPIClient("cid", "secret", region="eu", client=http)
            regions = await api.get_regions()
            profile = await api.get_profile_by_uuid(
                "5c7e0994-bc22-4190-9774-5f197b1500e6"
            )
            clans = await api.list_clans(limit=10, offset=0)
            clan_info = await api.get_clan(clan["id"])
            ops = await api.get_operations(map_name="operation_bigcleanup", limit=10)

        self.assertEqual(regions[0]["id"], "EU")
        self.assertEqual(profile["username"], "Test-1")
        self.assertEqual(clans["totalClans"], 1)
        self.assertEqual(clan_info["name"], "Clan #1")
        self.assertEqual(ops["total"], 1)
        self.assertEqual(seen[0].url.path, "/regions")
        self.assertIn("/character/by-uuid/", seen[1].url.path)
        self.assertEqual(seen[2].url.params["limit"], "10")
        self.assertIn("/clan/", seen[3].url.path)
        self.assertEqual(seen[4].url.params["map"], "operation_bigcleanup")


class ItemIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = ItemIndex(PLUGIN_ROOT / "item_index.json")

    def test_index_ready(self):
        self.assertTrue(self.index.ready)
        self.assertGreater(len(self.index.items), 2500)
        self.assertEqual([item["id"] for item in self.index.items if not item["zh"]], [])

    def test_chinese_artifact(self):
        item, matches = self.index.resolve("寒冰")
        self.assertEqual(item["id"], "ljn2")
        self.assertEqual(item["en"], "Chilly")
        self.assertEqual(len(matches), 1)

    def test_english_artifact(self):
        item, _ = self.index.resolve("Spectral Crystal")
        self.assertEqual(item["id"], "9nd0")
        self.assertIn("电水晶", item["zh"])

    def test_custom_alias_overrides(self):
        import json

        with tempfile.TemporaryDirectory() as directory:
            alias_path = Path(directory) / "item_aliases.json"
            alias_path.write_text(
                json.dumps({"ljn2": ["冰晶", "Chilly Ice"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            index = ItemIndex(
                PLUGIN_ROOT / "item_index.json",
                aliases_path=alias_path,
            )
            item, matches = index.resolve("冰晶")
            self.assertEqual(item["id"], "ljn2")
            self.assertEqual(matches[0]["id"], "ljn2")
            self.assertEqual(index.search("Chilly Ice")[0]["id"], "ljn2")

    def test_artifact_additional_stats_are_merged(self):
        item = dict(self.index.get("gyq5"))
        item["cat_label"] = "神器 / 电物理"
        item["display"] = display_name(item)
        text = format_item(item, self.index.get_details("gyq5"))
        self.assertIn(
            "移动速度：[+0.85%; +1%]（附加：[+0.28%; +0.35%]）", text
        )
        self.assertIn(
            "负重：[+7.4; +8.7]（附加：[+2.465; +2.9]）", text
        )
        self.assertIn("治疗效率（附加）：[+5.02%; +6.1%]", text)
        self.assertNotIn("负重（附加）：", text)

    def test_short_name_prefers_base_weapon_over_variant(self):
        short, _ = self.index.resolve("x95")
        full, _ = self.index.resolve("FN IWI Tavor X95")
        self.assertEqual(short["id"], "2ony6")
        self.assertEqual(full["id"], "2ony6")
        variant, _ = self.index.resolve("X95 (A)")
        self.assertEqual(variant["id"], "lyv9k")

    def test_non_artifact_derived_translations(self):
        premium = self.index.get("7l9d3")
        self.assertIsNotNone(premium)
        self.assertEqual(premium["zh"], "高级账户 180天")
        self.assertEqual(self.index.resolve("高级账户 180天")[0]["id"], "7l9d3")

        ammo = self.index.get("3vzg")
        self.assertEqual(ammo["zh"], "12号径 鹿弹")
        grenade = self.index.get("dsxs222x")
        self.assertEqual(grenade["zh"], "暴风雪")
        self.assertEqual(self.index.get("Dx54DzxD")["zh"], "逆变器")
        self.assertEqual(self.index.get("xz3235xD")["zh"], "符文")

    def test_display_translation_variants(self):
        from item_index import display_translation

        self.assertEqual(display_translation(self.index.get("wg53")), "原子")
        self.assertEqual(display_translation(self.index.get("zz2rn")), "")
        self.assertEqual(
            display_translation(self.index.get("vj297")), "格洛克18X"
        )
        self.assertEqual(
            display_translation(self.index.get("7l9d3")), "高级账户 180天"
        )

    def test_display_name_hides_locale_keys(self):
        from item_index import display_name

        ammo = self.index.get("3vzg")
        self.assertEqual(display_name(ammo), "12号径 鹿弹")
        missing = self.index.get("krzyp")
        self.assertEqual(display_name(missing), "Digamma小组追踪器")
        details = dict(self.index.get("wg53"))
        details["display"] = display_name(details)
        self.assertIn("原子", details["display"])

    def test_manual_name_override(self):
        with tempfile.TemporaryDirectory() as directory:
            override = Path(directory) / "item_name_overrides.json"
            override.write_text('{"xz3235xD":"符文"}', encoding="utf-8")
            index = ItemIndex(
                PLUGIN_ROOT / "item_index.json", overrides_path=override
            )
            self.assertEqual(index.get("xz3235xD")["zh"], "符文")

    def test_atom_details(self):
        atom = self.index.get("wg53")
        self.assertIsNotNone(atom)
        details = self.index.get_details("wg53")
        self.assertTrue(details.get("stats"))
        self.assertIn("玻尔原子模型", details.get("description_zh", ""))
        text = format_item(dict(atom, cat_label="神器 / 电物理"), details)
        self.assertIn("原子", text)
        self.assertIn("生命：", text)
        self.assertIn("辐射：", text)

    def test_weapon_id_and_english(self):
        self.assertEqual(self.index.resolve("vjr1n")[0]["id"], "vjr1n")
        self.assertEqual(self.index.resolve("AK-74M")[0]["id"], "vjr1n")
        for query in ("ak-308", "AK-308", "Ak-308"):
            self.assertEqual(self.index.resolve(query)[0]["id"], "dmjdn")
        self.assertEqual(self.index.resolve("Ak-308 (a)")[0]["id"], "j5vz0")

    def test_ambiguous_names(self):
        item, matches = self.index.resolve("Transformer")
        self.assertIsNone(item)
        self.assertGreaterEqual(len(matches), 2)

    def test_synonym_item_search(self):
        item, matches = self.index.resolve("高级会员")
        self.assertIsNone(item)
        self.assertIn("m0jyj", [candidate["id"] for candidate in matches])
        self.assertTrue(any("高级账户" in candidate["zh"] for candidate in matches))

    def test_single_character_item_search(self):
        matches = self.index.search("原", limit=8)
        self.assertTrue(matches)
        self.assertEqual(matches[0]["id"], "wg53")
        item, candidates = self.index.resolve("原")
        self.assertIsNone(item)
        self.assertIn("wg53", [candidate["id"] for candidate in candidates])

    def test_artifact_translation_coverage(self):
        mapped = dict(ITEM_STAT_CN)
        mapped.update(ARTEFACT_STAT_CN)
        for item in self.index.items:
            if item["cat"].startswith("artefact"):
                details = self.index.get_details(item["id"])
                for stat in details.get("stats", []):
                    label = stat.get("label", "")
                    self.assertIn(label, mapped, f"{item['en']}: {label}")

    def test_artifact_terms(self):
        atom = dict(self.index.get("wg53"))
        atom["cat_label"] = category_label(atom["cat"])
        from item_index import display_name

        atom["display"] = display_name(atom)
        text = format_item(atom, self.index.get_details("wg53"))
        self.assertIn("精神辐射", text)
        self.assertIn("流血", text)
        self.assertNotIn("心灵", text)
        self.assertNotIn("出血", text)
        self.assertIn(ITEM_STAT_CN["Healing effectiveness"], "治疗效率")
        self.assertEqual(ITEM_STAT_CN["Laceration protection"], "撕裂防护")
        self.assertEqual(ITEM_STAT_CN["Bullet resistance"], "子弹防护")
        self.assertEqual(ARTEFACT_STAT_CN["Reload"], "充能时间")

    def test_category_label(self):
        self.assertIn("神器", category_label("artefact/thermal"))


class V2FormatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = ItemIndex(PLUGIN_ROOT / "item_index.json")

    def _item(self, item_id):
        item = dict(self.index.get(item_id))
        item["cat_label"] = category_label(item["cat"])
        from item_index import display_name

        item["display"] = display_name(item)
        return item

    def test_format_item(self):
        text = format_item(self._item("ljn2"))
        self.assertIn("寒冰 / Chilly", text)
        self.assertIn("ljn2", text)
        self.assertIn("/sz auction ljn2", text)

    def test_item_candidates(self):
        text = format_item_candidates("Razor", [self._item("ljn2"), self._item("9nd0")])
        self.assertIn("没有精确匹配「Razor」", text)
        self.assertIn("ljn2", text)

    def test_candidate_views(self):
        view = build_item_candidate_view(
            "寒冰", [self._item("ljn2"), self._item("9nd0")]
        )
        self.assertEqual(view["count"], 2)
        self.assertEqual(view["entries"][0]["index"], 1)
        self.assertEqual(view["entries"][0]["title"], "寒冰")
        self.assertEqual(view["entries"][0]["subtitle"], "Chilly")
        self.assertIn("ID ljn2", view["entries"][0]["meta"])
        self.assertTrue(view["entries"][0]["color"].startswith("#"))

        clan_view = build_clan_candidate_view(
            "Clan",
            [
                {
                    "id": "abc",
                    "name": "Clan #1",
                    "tag": "TAG",
                    "level": 2,
                    "memberCount": 5,
                    "alliance": "covenant",
                }
            ],
        )
        self.assertEqual(clan_view["entries"][0]["title"], "Clan #1 [TAG]")
        self.assertIn("阵营 契约", clan_view["entries"][0]["meta"])
        self.assertEqual(clan_view["entries"][0]["faction"], "covenant")

    def test_clan_and_regions(self):
        clan = {
            "id": "abc",
            "name": "Clan #1",
            "tag": "TAG",
            "level": 2,
            "levelPoints": 100,
            "alliance": "covenant",
            "memberCount": 1,
            "leader": "Test-1",
        }
        text = format_clan(clan, "eu")
        self.assertIn("Clan #1 [TAG]", text)
        self.assertIn("User token", text)
        regions = format_regions([{"id": "EU", "name": "EUROPE"}])
        self.assertIn("EU — EUROPE", regions)

    def test_clan_list_translates_merc_short_code(self):
        text = format_clans_list(
            {
                "totalClans": 1,
                "data": [
                    {
                        "id": "abc",
                        "name": "Merc Clan",
                        "tag": "MERC",
                        "level": 1,
                        "memberCount": 5,
                        "alliance": "merc",
                    }
                ],
            },
            1,
        )
        self.assertIn("阵营 佣兵", text)

    def test_faction_labels(self):
        clan = {
            "id": "abc",
            "name": "Covenant Clan",
            "tag": "COV",
            "level": 1,
            "levelPoints": 0,
            "alliance": "covenant",
            "memberCount": 1,
            "leader": "A",
        }
        text = format_clan(clan, "eu")
        self.assertIn("契约", text)
        self.assertNotIn("盟约", text)
        for alliance, label in (("rise", "崛起"), ("frontier", "边境"), ("loners", "潜行者")):
            clan["alliance"] = alliance
            self.assertIn(f"阵营：{label}", format_clan(clan, "eu"))

    def test_operations(self):
        payload = {
            "total": 1,
            "sessions": [
                {
                    "map": "operation_bigcleanup",
                    "difficulty": 3,
                    "sessionDurationSeconds": 1200,
                    "endTime": "2026-10-22T05:00:00Z",
                    "participants": [{"username": "A"}],
                }
            ],
        }
        text = format_operations(payload)
        self.assertIn("行动记录", text)
        self.assertIn("operation_bigcleanup", text)
        self.assertIn("20 分钟", text)

    def test_help_has_v2_commands(self):
        text = format_help("eu")
        self.assertIn("/sz item", text)
        self.assertIn("/sz clan", text)
        self.assertIn("/sz operations", text)
        self.assertIn("拍卖行", text)
        self.assertIn("风暴", text)
        self.assertNotIn("/sz 市场", text)
        self.assertNotIn("/sz 交易", text)
        self.assertNotIn("/sz 爆发", text)
        self.assertNotIn("/sz profile", text)


class ImageRendererTests(unittest.TestCase):
    def test_rank_colors(self):
        self.assertEqual(rank_color("Newbie"), "#53C353")
        self.assertEqual(rank_color("Stalker"), "#4EA8FF")
        self.assertEqual(rank_color("Veteran"), "#FF6FB5")
        self.assertEqual(rank_color("Master"), "#FF5C5C")
        self.assertEqual(rank_color("Legend"), "#FFD166")
        self.assertIsNone(rank_color("Picklock"))
        self.assertEqual(item_color({"color": "RANK_MASTER"}), "#FF5C5C")
        self.assertEqual(item_color({"color": "DEFAULT"}), "#E7EDF5")
        self.assertEqual(
            item_color({"color": "RANK_NEWBIE", "rank": "Newbie"}), "#53C353"
        )

    def test_signature_text(self):
        from image_renderer import SIGNATURE

        self.assertEqual(SIGNATURE, "Created By @Sakura_Akira")

    def test_attachment_stat_colours_and_reaction_translation(self):
        self.assertEqual(_stat_direction("垂直后坐力"), -1)
        self.assertEqual(_artifact_label_color(-1, "-0.75%"), STAT_GREEN)
        self.assertEqual(ITEM_STAT_CN["Reaction to burns"], "燃烧反应")
        self.assertEqual(ITEM_STAT_CN["Reaction to laceration"], "撕裂反应")

    def test_faction_icons(self):
        for faction in (
            "freedom",
            "rise",
            "duty",
            "frontier",
            "mercenaries",
            "covenant",
            "merc",
            "stalker",
            "stalkers",
            "loners",
            "bandit",
            "bandits",
        ):
            path = faction_icon_path(faction)
            self.assertIsNotNone(path, faction)
            self.assertTrue(path.is_file())
        self.assertEqual(faction_icon_path("rise"), faction_icon_path("freedom"))
        self.assertEqual(faction_icon_path("frontier"), faction_icon_path("duty"))
        self.assertEqual(faction_icon_path("loners"), faction_icon_path("stalkers"))
        self.assertIsNone(faction_icon_path("unknown"))

    def test_artifact_stat_colours(self):
        self.assertEqual(_stat_direction("生命"), 1)
        self.assertEqual(_stat_direction("精神辐射"), -1)
        self.assertEqual(_stat_direction("流血"), -1)
        self.assertEqual(_stat_direction("撕裂反应"), 1)
        self.assertEqual(_artifact_label_color(1, "[+2%; +3%]"), STAT_GREEN)
        self.assertEqual(_artifact_label_color(1, "[-2%; -3%]"), STAT_RED)
        self.assertEqual(_artifact_label_color(-1, "[+20; +30]"), STAT_RED)
        self.assertEqual(_artifact_label_color(-1, "[-20; -30]"), STAT_GREEN)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_auction_signature_stays_inside_card(self):
        from PIL import Image

        path = render_auction_card(
            {
                "title": "原子 / Atom｜EU",
                "region": "EU",
                "now": "2026-10-23 14:00",
                "active": [
                    {
                        "name": "原子",
                        "start": "1,000",
                        "buyout": "2,000",
                        "remaining": "2天",
                    }
                ],
                "recent_groups": [],
            }
        )
        self.assertIsNotNone(path)
        with Image.open(path) as source:
            image = source.convert("RGB")
            width, height = image.size
            gold_y = [
                y
                for y in range(height)
                for x in range(0, width, 2)
                if all(
                    abs(channel - target) <= 6
                    for channel, target in zip(image.getpixel((x, y)), (231, 194, 125))
                )
            ]
        self.assertTrue(gold_y)
        self.assertLess(max(gold_y), height - 4)
        path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_candidate_card_two_columns(self):
        from PIL import Image

        view = build_item_candidate_view(
            "x",
            [
                {"display": "原子 / Atom", "cat_label": "神器", "color": "DEFAULT", "id": "wg53"},
                {"display": "原罪 / Sin", "cat_label": "其他物品", "color": "RANK_MASTER", "id": "7lrr9"},
                {"display": "原型机 / Prototype", "cat_label": "其他 / 外观", "color": "RANK_MASTER", "id": "1r6pq"},
            ],
        )
        path = render_candidate_card(view)
        self.assertIsNotNone(path)
        with Image.open(path) as image:
            self.assertEqual(image.size, (1200, 530))
        path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_creator_watermark_can_be_hidden(self):
        import image_renderer as renderer

        old = renderer.CREATOR_WATERMARK_HIDDEN
        try:
            renderer.set_creator_watermark_hidden(True)
            draw = Mock()
            renderer._draw_signature(
                draw,
                1200,
                100,
                find_cjk_font(),
                None,
                more_tip=False,
                max_bottom=500,
            )
            draw.text.assert_not_called()
            draw.textlength.assert_not_called()

            tip_draw = Mock()
            renderer._draw_signature(
                tip_draw,
                1200,
                100,
                find_cjk_font(),
                None,
                more_tip=True,
                max_bottom=500,
            )
            tip_draw.text.assert_called_once()
            self.assertEqual(
                tip_draw.text.call_args.args[1], renderer.MORE_FEATURES_TIP
            )
            tip_draw.textlength.assert_not_called()
        finally:
            renderer.set_creator_watermark_hidden(old)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_emission_card(self):
        from PIL import Image

        view = build_emission_view(
            {
                "previousStart": "2026-10-22T03:00:00Z",
                "previousEnd": "2026-10-22T03:30:00Z",
            },
            "ru",
        )
        path = render_emission_card(view)
        self.assertIsNotNone(path)
        with Image.open(path) as image:
            self.assertEqual(image.size, (1200, 780))
        path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_emission_alert_card(self):
        from PIL import Image

        view = build_emission_alert_view(
            {
                "currentStart": "2026-10-22T05:00:00Z",
                "previousStart": "2026-10-22T03:00:00Z",
                "previousEnd": "2026-10-22T03:30:00Z",
            },
            "ru",
            now=__import__("datetime").datetime(
                2026, 10, 22, 5, 17, tzinfo=__import__("datetime").timezone.utc
            ),
        )
        path = render_emission_alert_card(view)
        self.assertIsNotNone(path)
        with Image.open(path) as image:
            self.assertEqual(image.size, (1200, 700))
        path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_item_card_name_block(self):
        from PIL import Image

        path = render_text_card(
            "STALZONE · 物品\nGlock 18X\n\n● 标识\nID：vj297",
            item_meta={
                "en": "Glock 18X",
                "zh": "格洛克18X",
                "color": "RANK_MASTER",
                "rank": "Master",
            },
        )
        self.assertIsNotNone(path)
        try:
            with Image.open(path) as image:
                self.assertEqual(image.width, WIDTH)
        finally:
            path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_render_card_with_icon(self):
        icon = PLUGIN_ROOT / "item_icons" / "wg53.png"
        if not icon.exists():
            self.skipTest("Atom icon not downloaded")
        idx = ItemIndex(PLUGIN_ROOT / "item_index.json")
        item = dict(idx.get("wg53"))
        item["cat_label"] = category_label(item["cat"])
        from item_index import display_name

        item["display"] = display_name(item)
        text = format_item(item, idx.get_details("wg53"))
        path = render_text_card(text, icon_path=icon)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_render_card_to_png(self):
        lots = {
            "total": 1,
            "lots": [
                {
                    "amount": 1,
                    "startPrice": 2999999,
                    "buyoutPrice": 3000000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {},
                }
            ],
        }
        history = {
            "total": 1,
            "prices": [{"amount": 1, "price": 1300000, "time": "2026-09-21T00:01:00Z"}],
        }
        text = format_auction("ljn2", lots, history, "eu", item_label="寒冰 / Chilly")
        path = render_text_card(text)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 1000)
        path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_auction_card_columns_follow_name_length(self):
        from PIL import Image

        view = {
            "title": "原子 / Atom (wg53)",
            "region": "EU",
            "now": "2026-10-22 17:30",
            "active": [
                {
                    "name": "原子",
                    "color": "#E7EDF5",
                    "start": "1,520,000",
                    "buyout": "1,120,000",
                    "remaining": "剩余7小时29分钟",
                }
            ],
            "recent_groups": [],
            "recent_limit": 3,
            "quality_filter": None,
            "quality_filter_label": None,
        }
        path = render_auction_card(view)
        self.assertIsNotNone(path)
        try:
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 700)
                self.assertLess(image.width, WIDTH)
        finally:
            path.unlink(missing_ok=True)

        view["active"][0]["name"] = "“幽灵”超重型防护服＋15"
        view["active"][0]["start"] = "12,345,678"
        view["active"][0]["buyout"] = "12,345,678"
        path = render_auction_card(view)
        self.assertIsNotNone(path)
        try:
            with Image.open(path) as image:
                self.assertLessEqual(image.width, WIDTH)
        finally:
            path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_stacked_non_artifact_auction_card_renders(self):
        from PIL import Image

        lots = {
            "lots": [
                {
                    "amount": 10,
                    "startPrice": 5000,
                    "buyoutPrice": 6000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {},
                },
                {
                    "amount": 20,
                    "startPrice": 9000,
                    "buyoutPrice": 10000,
                    "endTime": "2026-10-22T16:00:00Z",
                    "additional": {},
                },
            ]
        }
        history = {
            "prices": [
                {"amount": 10, "price": 5500, "time": "2026-10-22T03:00:00Z"},
                {"amount": 2, "price": 2400, "time": "2026-10-22T05:00:00Z"},
            ]
        }
        view = build_auction_view(
            "cig",
            lots,
            history,
            "eu",
            now=FormatterTests.NOW,
            item_label="香烟",
            non_artifact=True,
            item_color="#E7EDF5",
        )
        path = render_auction_card(view)
        self.assertIsNotNone(path)
        try:
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 700)
                self.assertLessEqual(image.width, WIDTH)
                self.assertGreater(image.height, 430)
        finally:
            path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_auction_history_card_renders_without_active_table(self):
        from PIL import Image

        view = {
            "title": "原子 / Atom (wg53)",
            "region": "EU",
            "now": "2026-10-22 17:30",
            "active": [],
            "recent_groups": [
                {
                    "quality": 3,
                    "label": "稀有（粉）",
                    "color": "#FF6FB5",
                    "rows": [
                        {
                            "name": "原子",
                            "color": "#FF6FB5",
                            "price": "904,700",
                            "amount": 1,
                            "time": "2026/6/3 03:00",
                        },
                        {
                            "name": "原子",
                            "color": "#FF6FB5",
                            "price": "903,400",
                            "amount": 1,
                            "time": "2026/6/3 02:00",
                        },
                    ],
                }
            ],
            "recent_limit": 20,
            "quality_filter": 3,
            "quality_filter_label": "稀有（粉）",
            "history_only": True,
            "before": "2026/6/11",
            "history_note": "截至 2026/6/11｜最多 20 条",
        }
        path = render_auction_card(view)
        self.assertIsNotNone(path)
        try:
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 620)
                self.assertLessEqual(image.width, WIDTH)
                self.assertGreaterEqual(image.height, 430)
        finally:
            path.unlink(missing_ok=True)

    @unittest.skipUnless(find_cjk_font(), "No CJK font installed")
    def test_empty_auction_card_renders_colored_item_name(self):
        from PIL import Image

        view = build_empty_auction_view(
            "wg53",
            "原子 / Atom",
            "eu",
            quality_filter=3,
            before=auction_day_cutoff(
                __import__("datetime").date(2026, 10, 1)
            ),
            note="已检查最近 4000 条成交，仍未到达该日期。",
        )
        path = render_auction_card(view)
        self.assertIsNotNone(path)
        try:
            with Image.open(path) as image:
                self.assertEqual(image.width, 760)
                self.assertGreater(image.height, 300)
                self.assertLessEqual(image.height, 430)
        finally:
            path.unlink(missing_ok=True)

    def test_text_card_has_sections(self):
        text = format_help("eu")
        self.assertIn("━━", text)
        self.assertIn("●", text)


if __name__ == "__main__":
    unittest.main()
