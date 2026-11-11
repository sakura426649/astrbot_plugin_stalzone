"""Artifact price-watch parsing, lot evaluation helpers and text views.

The actual polling and persistence live in ``main.py``; this module keeps the
pure parsing/statistics/rendering pieces testable without AstrBot.
"""

from __future__ import annotations

import re
from typing import Any

from formatters import (
    QUALITY_ALIASES,
    QUALITY_COLORS,
    QUALITY_NAMES,
    _card,
    quality_label,
)

LEVEL_TOKEN = re.compile(r"^[+＋](\d{1,2})$")
RELATIVE_TOKEN = re.compile(r"^-(\d{1,2})%$")
PRICE_TOKEN = re.compile(
    r"^(\d[\d,._]*)(kk|k|m|b|кк|к|м|б)?$", re.IGNORECASE
)
PRICE_MULTIPLIERS = {
    "": 1,
    "k": 1_000,
    "к": 1_000,
    "kk": 1_000_000,
    "кк": 1_000_000,
    "m": 1_000_000,
    "м": 1_000_000,
    "b": 1_000_000_000,
    "б": 1_000_000_000,
}
WATCH_DEFAULT_TTL_DAYS = 7
WATCH_MAX_TTL_DAYS = 30


class WatchQueryError(ValueError):
    """User-facing validation error for ``/sz 关注``."""


def parse_watch_query(argument: str) -> dict[str, Any]:
    """Parse ``item [quality] +level <price|-N%> [cap]``.

    Examples::

        原子 金 +15 8000
        原子 +15 -20%
        原子 +15 -20% 12000
    """
    tokens = str(argument or "").split()
    if not tokens:
        raise WatchQueryError("请填写要关注的神器、等级和目标价。")
    level: int | None = None
    level_at = -1
    for index, token in enumerate(tokens):
        match = LEVEL_TOKEN.fullmatch(token)
        if match is not None:
            value = int(match.group(1))
            if not 0 <= value <= 15:
                raise WatchQueryError("等级请填 +0～+15。")
            level = value
            level_at = index
            break
    if level is None:
        raise WatchQueryError(
            "神器关注必须写等级，例如：/sz 关注 原子 +15 8000"
        )
    tokens.pop(level_at)
    _merge_grouped_price(tokens)
    if not tokens:
        raise WatchQueryError("请填写目标价，例如：8000、3K、3M 或 -20%。")

    mode = "absolute"
    threshold: int | None = None
    relative_pct: int | None = None
    cap: int | None = None
    last = tokens[-1]
    relative = RELATIVE_TOKEN.fullmatch(last)
    if relative is not None:
        mode = "relative"
        relative_pct = int(relative.group(1))
        tokens.pop()
    elif PRICE_TOKEN.fullmatch(last):
        if len(tokens) >= 2:
            previous = RELATIVE_TOKEN.fullmatch(tokens[-2])
            if previous is not None:
                mode = "relative"
                relative_pct = int(previous.group(1))
                cap = _parse_price_token(last, "价格上限")
                tokens.pop()
                tokens.pop()
            else:
                mode = "absolute"
                threshold = _parse_price_token(last, "目标价")
                tokens.pop()
        else:
            mode = "absolute"
            threshold = _parse_price_token(last, "目标价")
            tokens.pop()
    else:
        raise WatchQueryError(
            "目标价请填整数（如 8000）或相对幅度（如 -20%）。"
        )
    if mode == "relative":
        if relative_pct is None or not 1 <= relative_pct <= 90:
            raise WatchQueryError("相对幅度请填 1%～90%，例如 -20%。")
    else:
        if threshold is None or threshold <= 0:
            raise WatchQueryError("目标价必须大于 0。")
    if cap is not None and cap <= 0:
        raise WatchQueryError("价格上限必须大于 0。")

    quality: int | None = None
    if tokens:
        quality = QUALITY_ALIASES.get(tokens[-1].lower())
        if quality is not None:
            tokens.pop()
    if quality is None:
        raise WatchQueryError(
            "神器关注必须写品质，例如：/sz 关注 原子 红 +15 8000"
        )
    item = " ".join(tokens).strip()
    if not item:
        raise WatchQueryError("请填写要关注的神器名或 ID。")
    return {
        "item": item,
        "quality": quality,
        "level": level,
        "mode": mode,
        "threshold": threshold,
        "relative_pct": relative_pct,
        "cap": cap,
    }


def _parse_price_token(token: str, label: str) -> int:
    """Parse ``8000``, ``3K``, ``3M``, ``3kk`` or ``3,000,000``."""
    text = str(token or "").strip().replace("_", "")
    match = PRICE_TOKEN.fullmatch(text)
    if match is None:
        raise WatchQueryError(
            f"{label}格式不正确，支持 8000、3K、3M、3kk 或 3,000,000。"
        )
    number, unit = match.group(1), (match.group(2) or "").lower()
    multiplier = PRICE_MULTIPLIERS.get(unit)
    if multiplier is None:
        raise WatchQueryError(f"{label}单位不支持，请用 K、M 或 kk。")
    try:
        if unit:
            normalized = number.replace("_", "")
            if "," in normalized and "." not in normalized:
                normalized = normalized.replace(",", ".", 1)
            else:
                normalized = normalized.replace(",", "")
            numeric = float(normalized) * multiplier
        else:
            # No suffix: commas/dots are thousands separators, not decimals.
            numeric = float(number.replace(",", "").replace("_", ""))
    except ValueError:
        raise WatchQueryError(
            f"{label}格式不正确，支持 8000、3K、3M、3kk 或 3,000,000。"
        ) from None
    value = int(round(numeric))
    if value <= 0:
        raise WatchQueryError(f"{label}必须大于 0。")
    return value


def _merge_grouped_price(tokens: list[str]) -> None:
    """Merge ``3 000 000`` into one token when it is a trailing price."""
    start = len(tokens)
    while start > 0 and tokens[start - 1].isdigit():
        start -= 1
    group = tokens[start:]
    if (
        len(group) >= 2
        and 1 <= len(group[0]) <= 3
        and all(len(part) == 3 for part in group[1:])
    ):
        tokens[start:] = ["".join(group)]


def watch_query_summary(query: dict[str, Any]) -> str:
    parts = [str(query.get("item") or "")]
    quality = query.get("quality")
    if quality is not None:
        parts.append(quality_label(int(quality)))
    parts.append(f"+{int(query.get('level') or 0)}")
    if query.get("mode") == "relative":
        target = f"低于中位 {int(query.get('relative_pct') or 0)}%"
        if query.get("cap"):
            target += f"，且 ≤ {int(query['cap']):,}"
    else:
        target = f"≤ {int(query.get('threshold') or 0):,}"
    parts.append(target)
    return "｜".join(part for part in parts if part)


def watch_quality_color(quality: int | None) -> str:
    if quality is None:
        return "#54D6A1"
    return QUALITY_COLORS.get(int(quality), "#93A6BA")


def watch_quality_short(quality: int | None) -> str:
    if quality is None:
        return "全部品质"
    # The quality column uses the quality name (独特/传奇), not its color (红/金).
    return QUALITY_NAMES.get(int(quality), ("品质", ""))[0]


def _safe_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("_", "")
        if cleaned.lstrip("-").isdigit():
            return int(cleaned)
    return None


def _unit_price(value: Any, amount: int) -> int | None:
    total = _safe_int(value)
    if total is None or amount <= 0:
        return None
    return int(total / amount)


def _quality_of(lot: dict[str, Any]) -> int:
    additional = lot.get("additional")
    if not isinstance(additional, dict):
        return 0
    for key in ("qlt", "quality", "itemQuality", "item_quality"):
        value = _safe_int(additional.get(key))
        if value is not None and 0 <= value <= 5:
            return value
    return 0


def _level_of(lot: dict[str, Any]) -> int:
    additional = lot.get("additional")
    if not isinstance(additional, dict):
        return 0
    for key in ("ptn", "level", "upgradeLevel", "upgrade_level", "itemLevel"):
        value = _safe_int(additional.get(key))
        if value is not None and value > 0:
            return value
    return 0


def watch_lot_rows(
    payload: dict[str, Any] | None, item_id: str
) -> list[dict[str, Any]]:
    lots = payload.get("lots") if isinstance(payload, dict) else None
    rows: list[dict[str, Any]] = []
    for lot in lots if isinstance(lots, list) else []:
        if not isinstance(lot, dict):
            continue
        amount = max(1, _safe_int(lot.get("amount")) or 1)
        buyout = _unit_price(lot.get("buyoutPrice"), amount)
        current = _unit_price(lot.get("currentPrice"), amount)
        if current is None:
            current = _unit_price(lot.get("startPrice"), amount)
        if buyout is None and current is None:
            continue
        quality = _quality_of(lot)
        level = _level_of(lot)
        start_price = _safe_int(lot.get("startPrice"))
        buyout_raw = _safe_int(lot.get("buyoutPrice"))
        signature = "|".join(
            [
                item_id,
                f"q{quality}",
                f"l{level}",
                f"a{amount}",
                f"s{start_price or 0}",
                f"b{buyout_raw or 0}",
                f"st{lot.get('startTime') or ''}",
                f"et{lot.get('endTime') or ''}",
            ]
        )
        rows.append(
            {
                "buyout": buyout if buyout and buyout > 0 else None,
                "current": current if current and current > 0 else None,
                "amount": amount,
                "quality": quality,
                "level": level,
                "start": lot.get("startTime"),
                "end": lot.get("endTime"),
                "signature": signature,
            }
        )
    return rows


def weighted_median(values: list[tuple[int, int]]) -> int | None:
    """Return a weighted median from ``(value, weight)`` pairs."""
    ordered = sorted((int(value), max(1, int(weight))) for value, weight in values)
    total = sum(weight for _value, weight in ordered)
    if total <= 0:
        return None
    target = total / 2
    accumulated = 0
    for value, weight in ordered:
        accumulated += weight
        if accumulated >= target:
            return value
    return ordered[-1][0] if ordered else None


def history_medians(
    payload: dict[str, Any] | None,
    level: int,
    *,
    cutoff: Any = None,
    now: Any = None,
) -> dict[int | None, int]:
    """Compute per-quality weighted medians for one artifact level."""
    prices = payload.get("prices") if isinstance(payload, dict) else None
    buckets: dict[int, list[tuple[int, int]]] = {}
    for entry in prices if isinstance(prices, list) else []:
        if not isinstance(entry, dict):
            continue
        if _level_of(entry) != level:
            continue
        if cutoff is not None and now is not None:
            stamp = parse_time(entry.get("time"))
            if stamp is not None and stamp < cutoff:
                continue
        amount = max(1, _safe_int(entry.get("amount")) or 1)
        price = _unit_price(entry.get("price"), amount)
        if price is None or price <= 0:
            continue
        buckets.setdefault(_quality_of(entry), []).append((price, amount))
    result: dict[int | None, int] = {}
    for quality, values in buckets.items():
        median = weighted_median(values)
        if median is not None:
            result[quality] = median
    overall = weighted_median(
        [pair for values in buckets.values() for pair in values]
    )
    if overall is not None:
        result[None] = overall
    return result


def parse_time(value: Any) -> Any:
    from formatters import parse_auction_time

    return parse_auction_time(value)


def build_watch_alert_view(
    item: dict[str, Any],
    query: dict[str, Any],
    match: dict[str, Any],
    *,
    region: str,
    target: int,
    now: Any,
    extra: int = 0,
) -> dict[str, Any]:
    kind = str(match.get("kind") or "").lower()
    buyout = int(match["buyout"]) if match.get("buyout") else None
    current = int(match["current"]) if match.get("current") else None
    if kind not in {"buyout", "auction"}:
        kind = "buyout" if buyout is not None and buyout <= int(target) else "auction"
    short_name = str(item.get("zh") or item.get("en") or item.get("id") or "")
    name = short_name
    en = str(item.get("en") or "").strip()
    if en and en.lower() not in name.lower():
        name = f"{name}（{en}）"
    quality = match.get("quality")
    level = int(match.get("level") or 0)
    quality_color = watch_quality_color(
        int(quality) if quality is not None else None
    )
    quality_short = watch_quality_short(
        int(quality) if quality is not None else None
    )
    price = int((buyout if kind == "buyout" else current) or 0)
    remaining = str(match.get("remaining") or "未知")
    checked_at = now.astimezone().strftime("%Y-%m-%d %H:%M") if now else ""
    if kind == "buyout":
        note = (
            f"目标价 ≤ {target:,}；当前在售最低买断 {price:,} 卢布；"
            f"{remaining}。"
        )
        hint = "已命中买断价，关注任务会自动取消；没买到请重新 /sz 关注。"
        accent = "#54D6A1"
        watermark = "DEAL"
        kind_label = "买断提醒"
        title = "买断提醒"
        price_label = "当前在售最低买断"
    else:
        note = (
            f"目标价 ≤ {target:,}；当前竞拍价 {price:,} 卢布"
            + (
                f"（买断 {int(match['buyout']):,}）"
                if match.get("buyout")
                else ""
            )
            + f"；{remaining}。"
        )
        hint = "竞拍仅提醒，不保证拍到；若已拍到可手动 /sz 取消关注。"
        accent = "#FFB454"
        watermark = "BID"
        kind_label = "竞拍提醒"
        title = "竞拍提醒"
        price_label = "当前竞拍价"
    if extra:
        note += f" 同轮另有 {extra} 条符合条件的挂单。"
    return {
        "kind": kind,
        "kind_label": kind_label,
        "title": title,
        "watermark": watermark,
        "accent": accent,
        "item_name": name,
        "item_label": f"{short_name} +{level}",
        "short_name": short_name,
        "quality_color": quality_color,
        "quality_short": quality_short,
        "price_label": price_label,
        "item_id": str(item.get("id") or ""),
        "region": str(region or "EU").upper(),
        "quality": quality,
        "level": level,
        "price": price,
        "target": target,
        "buyout": match.get("buyout"),
        "current": match.get("current"),
        "amount": int(match.get("amount") or 1),
        "remaining": remaining,
        "checked_at": checked_at,
        "query": f"{short_name}｜{quality_short}｜+{level}",
        "note": note,
        "hint": hint,
        "footer": "STALZONE · 神器价格关注",
        "auto_cancel": kind == "buyout",
    }


def format_watch_alert_text(view: dict[str, Any]) -> str:
    headline = str(view.get("title") or "神器价格提醒")
    lines = [
        f"STALZONE · {headline}",
        f"{view.get('item_label')}｜{view.get('quality_short')}｜{view.get('region')}",
        f"当前价格：{int(view.get('price') or 0):,} 卢布",
        f"目标价：≤ {int(view.get('target') or 0):,} 卢布",
        f"{view.get('remaining')}",
        str(view.get("hint") or ""),
    ]
    return "\n".join(line for line in lines if line)


def format_watch_list(view: dict[str, Any]) -> str:
    subtitle = [
        f"{view.get('region')} · 本群 {int(view.get('session_items') or 0)}/"
        f"{int(view.get('session_limit') or 5)} 种"
        f"｜全局 {int(view.get('global_items') or 0)} 种"
        f"｜预计每 {int(view.get('refresh_minutes') or 2)} 分钟刷新",
    ]
    users = [user for user in (view.get("users") or []) if isinstance(user, dict)]
    sections: list[tuple[str, list[str]]] = []
    if users:
        for user in users:
            name = str(user.get("user_name") or "未知用户")
            if user.get("own"):
                name += "  [你]"
            rows: list[str] = []
            for item in user.get("items") or []:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    f"#{item.get('index')} {item.get('item_label')}"
                    f"｜{item.get('target_short') or item.get('target')}｜{item.get('remaining')}"
                )
            if rows:
                sections.append((name, rows))
    else:
        # Backward-compatible fallback for callers without grouped users.
        own = [row for row in (view.get("own") or []) if isinstance(row, dict)]
        others = [row for row in (view.get("others") or []) if isinstance(row, dict)]
        own_rows = [str(row.get("line") or "") for row in own if row.get("line")]
        other_rows = [str(row.get("line") or "") for row in others if row.get("line")]
        if own_rows:
            sections.append(("关注", own_rows))
        if other_rows:
            sections.append(("其他关注", other_rows))
    if not sections:
        sections.append(("暂无关注", ["发送 /sz 关注 <神器> +等级 <目标价> 创建第一条关注。"]))
    footer = (
        "买断命中会提醒后自动取消；竞拍命中只提醒、不取消"
        "｜普通用户只能取消自己的关注"
    )
    return _card("STALZONE · 神器价格关注", subtitle, sections, footer, limit=5000)
