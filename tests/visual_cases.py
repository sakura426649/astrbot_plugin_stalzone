"""Deterministic card views used by the Windows visual-regression snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from formatters import (
    build_auction_view,
    build_diag_view,
    build_empty_auction_view,
    build_emission_alert_view,
    build_emission_view,
    build_item_candidate_view,
    build_profile_view,
    build_season_pass_view,
    format_item,
)
from image_renderer import (
    render_auction_card,
    render_candidate_card,
    render_diag_card,
    render_emission_alert_card,
    render_emission_card,
    render_help_card,
    render_notice_card,
    render_pass_card,
    render_profile_card,
    render_text_card,
)
from season_pass import calculate

NOW = datetime(2026, 10, 24, 6, 0, tzinfo=timezone.utc)


def _profile() -> Path | None:
    payload = {
        "username": "Visual-Test",
        "status": "online",
        "alliance": "duty",
        "lastLogin": "2026-10-24T05:30:00Z",
        "displayedAchievements": ["dispenser", "env_hater", "signal-hunter"],
        "clan": {
            "info": {"name": "Visual Clan", "tag": "TEST", "level": 7},
            "member": {"name": "Visual-Test", "rank": "OFFICER"},
        },
        "stats": [
            {"id": "kil", "value": 12683},
            {"id": "kills-bf", "value": 1480},
            {"id": "ast", "value": 6009},
            {"id": "dea", "value": 14250},
            {"id": "bul-dea", "value": 10315},
            {"id": "col-dea", "value": 92},
            {"id": "exp-dea", "value": 1040},
            {"id": "ble-to-dea", "value": 77},
            {"id": "deaths-bf", "value": 1429},
            {"id": "ano-dea", "value": 152},
            {"id": "won-bf", "value": 56},
            {"id": "lost-bf", "value": 55},
            {"id": "part-bf", "value": 111},
            {"id": "won-fights-personal", "value": 11},
            {"id": "won-fights-equal", "value": 1},
            {"id": "fights-part", "value": 15},
        ],
    }
    view = build_profile_view(payload, "eu", now=NOW)
    return render_profile_card(view)


def _auction() -> Path | None:
    lots = {
        "total": 4,
        "lots": [
            {
                "amount": 1,
                "startPrice": 100000,
                "buyoutPrice": 250000,
                "endTime": "2026-10-25T06:00:00Z",
                "additional": {"qlt": 4},
            },
            {
                "amount": 2,
                "startPrice": 90000,
                "buyoutPrice": 220000,
                "endTime": "2026-10-25T05:00:00Z",
                "additional": {"qlt": 4},
            },
        ],
    }
    history = {
        "total": 3,
        "prices": [
            {
                "amount": 1,
                "price": 210000,
                "time": "2026-10-24T05:00:00Z",
                "additional": {"qlt": 4},
            },
            {
                "amount": 1,
                "price": 200000,
                "time": "2026-10-24T04:00:00Z",
                "additional": {"qlt": 4},
            },
        ],
    }
    view = build_auction_view(
        "wg53",
        lots,
        history,
        "eu",
        now=NOW,
        item_label="原子 / Atom",
        item_color="#FF6FB5",
    )
    return render_auction_card(view) if view else None


def _auction_quantity() -> Path | None:
    lots = []
    for amount in (1, 2, 5, 10, 20, 50):
        for offset in (0, 100):
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
        now=NOW,
        item_label="弹药 / Ammo",
        non_artifact=True,
    )
    return render_auction_card(view) if view else None


def _candidate() -> Path | None:
    view = build_item_candidate_view(
        "原子",
        [
            {"display": "原子 / Atom", "cat_label": "神器", "color": "RANK_MASTER", "id": "wg53"},
            {"display": "原罪 / Sin", "cat_label": "其他物品", "color": "RANK_MASTER", "id": "7lrr9"},
            {"display": "原型机 / Prototype", "cat_label": "其他 / 外观", "color": "RANK_MASTER", "id": "1r6pq"},
            {"display": "测试物品", "cat_label": "材料", "color": "DEFAULT", "id": "test"},
        ],
    )
    return render_candidate_card(view)


def _notice() -> Path | None:
    view = build_empty_auction_view(
        "nonexistent",
        "测试物品",
        "eu",
        now=NOW,
        note="请检查物品名或稍后重试。",
    )
    return render_notice_card(view)


def _diag() -> Path | None:
    info = {
        "version": "visual-test",
        "system": "Windows",
        "release": "11",
        "machine": "AMD64",
        "python": "3.12.0",
        "implementation": "CPython",
        "pid": 1234,
        "uptime_seconds": 3661,
        "timezone": "UTC+8",
        "region": "EU",
        "api_base": "https://eapi.stalzone.com",
        "env": "生产环境",
        "render_mode": "auto",
        "credentials": "已配置",
        "http": "已建立",
        "items": 2615,
        "details": 1338,
        "categories": 48,
        "aliases": 4,
        "balance_patches": 168,
        "balance_weapons": 400,
        "balance_generated": "2026-10-24",
        "pending": 1,
        "pending_limit": 200,
        "pending_ttl": 600,
        "sc_keys": 2,
        "sc_limit": 4096,
        "cooldown_scopes": 1,
        "cooldown_limit": 500,
        "cooldown": 1.0,
        "lunar_enrich": True,
        "sc_core_fallback": True,
        "cache_entries": 3,
        "cache_limit": 128,
        "cache_hits": 8,
        "cache_misses": 2,
        "help_files": 1,
        "help_bytes": 200000,
        "icon_files": 4,
        "icon_bytes": 50000,
        "temp_files": 2,
        "temp_bytes": 300000,
        "item_icon_files": 826,
        "item_icon_bytes": 9000000,
        "faction_icons": 6,
        "data_dir_ok": True,
        "concurrency": 6,
        "timeout": 10,
        "retries": 2,
        "retry_base": 0.5,
        "api_requests": 12,
        "api_successes": 10,
        "api_failures": 2,
        "api_last_path": "/eu/emission",
        "api_last_status": 503,
        "api_last_latency": 1200,
        "api_avg_latency": 640,
        "api_last_error": "HTTP 503: down",
        "api_circuit_seconds": 12,
        "auto_status": "已启用",
        "auto_window": "2–4 小时窗口内",
        "auto_whitelist": 2,
        "auto_targets": 2,
        "auto_last_check": "10-24 12:00",
        "auto_last_send": "成功 2 / 失败 0 · 10-24 12:00",
        "auto_last_error": "—",
        "font_ready": True,
        "font": "VisualCJK.ttc",
        "pillow": "10.0.0",
    }
    view = build_diag_view(info, now=datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc))
    return render_diag_card(view)


def _pass() -> Path | None:
    view = build_season_pass_view(calculate(15, 15, 2, 20, 7))
    return render_pass_card(view)


def _emission_payload() -> dict[str, str]:
    return {
        "currentStart": "2026-10-24T05:59:00Z",
        "previousStart": "2026-10-24T03:00:00Z",
        "previousEnd": "2026-10-24T03:30:00Z",
    }


def _emission() -> Path | None:
    return render_emission_card(
        build_emission_view(_emission_payload(), "eu", now=NOW)
    )


def _alert() -> Path | None:
    return render_emission_alert_card(
        build_emission_alert_view(_emission_payload(), "eu", now=NOW)
    )


def _item() -> Path | None:
    item = {
        "id": "wg53",
        "zh": "原子",
        "en": "Atom",
        "cat": "artefact",
        "color": "RANK_MASTER",
    }
    text = format_item(item, {})
    return render_text_card(
        text,
        item_meta={
            "en": "Atom",
            "zh": "原子",
            "color": "RANK_MASTER",
            "rank": "Master",
            "id": "wg53",
        },
    )


def _help() -> Path | None:
    return render_help_card(region="EU", version="visual-test")


CASES: dict[str, Callable[[], Path | None]] = {
    "profile": _profile,
    "auction": _auction,
    "auction_quantity": _auction_quantity,
    "candidate": _candidate,
    "notice": _notice,
    "diag": _diag,
    "pass": _pass,
    "emission": _emission,
    "emission_alert": _alert,
    "item": _item,
    "help": _help,
}
