"""Plain-text formatters for QQ group replies.

The layout is deliberately "card-like" but still plain text: a title, a
subtitle, section headings and short rows.  It renders well in QQ on both
desktop and mobile, and the same text can be fed to the optional Pillow
image renderer without parsing Markdown.
"""

from __future__ import annotations

import re
from datetime import date as date_cls
from datetime import datetime, time as time_cls, timedelta, timezone
from typing import Any

MAX_LINES = 5
SEP = "━━━━━━━━━━━━━━━━━━"
QUALITY_NAMES = {
    0: ("常见", "白"),
    1: ("罕见", "绿"),
    2: ("特殊", "蓝"),
    3: ("稀有", "粉"),
    4: ("独特", "红"),
    5: ("传奇", "金"),
}
QUALITY_ALIASES = {
    "常见": 0, "白": 0, "白色": 0, "common": 0, "white": 0,
    "罕见": 1, "绿": 1, "绿色": 1, "uncommon": 1, "green": 1,
    "特殊": 2, "蓝": 2, "蓝色": 2, "special": 2, "blue": 2,
    "稀有": 3, "粉": 3, "粉色": 3, "rare": 3, "pink": 3,
    "独特": 4, "红": 4, "红色": 4, "unique": 4, "red": 4,
    "传奇": 5, "金": 5, "金色": 5, "legendary": 5, "gold": 5,
}
CST = timezone(timedelta(hours=8))
UTC_NOTE = "时间为 UTC+8（北京时间）"

STAT_LABELS = {
    "level": "等级",
    "character_level": "角色等级",
    "playtime": "游戏时长",
    "kil": "击杀（kill）",
    "ast": "助攻",
    "dea": "总死亡",
    "bul-dea": "子弹死亡",
    "exp-dea": "爆炸死亡",
    "ble-to-dea": "流血死亡",
    "mel-dea": "近战死亡",
    "melee-dea": "近战死亡",
    "npc-kil": "NPC 击杀",
    "mut-kil": "变异体击杀",
    "kills-ops": "行动击杀",
    "kills-bf": "竞技场击杀",
    "pres-kills": "Preset 击杀",
    "deaths-bf": "竞技场死亡",
    "pres-deaths": "Preset 死亡",
    "won-bf": "竞技场胜场",
    "lost-bf": "竞技场败场",
    "completed-ops": "完成行动",
    "exp-kil": "爆炸击杀",
    "total_kills": "总击杀",
    "total_deaths": "总死亡",
    "total_assists": "总助攻",
    "total_score": "战斗分",
    "combat_score": "战斗分",
    "battle_score": "战斗分",
    "score": "战斗分",
    "rating": "评分",
    "kda": "KDA",
    "assists": "助攻",
    "winrate": "胜率",
    "matches_count": "场次",
    "matches": "场次",
    "completed-ops": "完成行动",
    "played_time": "游戏时长",
    "play_time": "游戏时长",
    "kills": "击杀",
    "deaths": "死亡",
    "kd": "K/D",
    "kdr": "K/D",
    "wins": "胜场",
    "losses": "败场",
    "matches": "场次",
    "completed-ops": "完成行动",
    "achievements": "成就",
    "reputation": "声望",
}

ALLIANCE_LABELS = {
    "duty": "纪律",
    "freedom": "自由",
    "covenant": "契约",
    "frontier": "边境",
    "mercenary": "佣兵",
    "mercenaries": "佣兵",
    "merc": "佣兵",
    "mercs": "佣兵",
    "rise": "崛起",
    "stalkers": "潜行者",
    "stalker": "潜行者",
    "loners": "潜行者",
    "bandits": "强盗",
    "bandit": "强盗",
}

STATUS_LABELS = {
    "online": "在线",
    "offline": "离线",
    "in_game": "游戏中",
}

ITEM_STAT_CN = {
    "Vitality": "生命",
    "Health": "生命",
    "Stamina": "耐力",
    "Stamina recovery": "耐力恢复",
    "Stamina regeneration": "耐力再生",
    "Health regeneration": "生命恢复",
    "Healing effectiveness": "治疗效率",
    "Periodic healing": "周期性治疗",
    "Radiation": "辐射",
    "Radiation protection": "辐射防护",
    "Temperature": "温度",
    "Thermal protection": "高温防护",
    "Biological infection": "生物感染",
    "Bioinfection protection": "生物感染防护",
    "Psyonics": "精神辐射",
    "Psy-emissions": "精神辐射",
    "Psy-emission protection": "精神辐射防护",
    "Psy-Emission protection": "精神辐射防护",
    "Bleeding": "流血",
    "Bleeding protection": "流血防护",
    "Frost": "寒冷",
    "Frost Protection": "防寒",
    "Burning": "燃烧",
    "Bullet resistance": "子弹防护",
    "Explosion protection": "爆炸防护",
    "Laceration protection": "撕裂防护",
    "Electricity resistance": "电抗性",
    "Resistance to electricity": "电抗性",
    "Fire resistance": "火抗性",
    "Resistance to fire": "火抗性",
    "Chemical resistance": "化学抗性",
    "Resistance to chemicals": "化学抗性",
    "Reaction to laceration": "撕裂反应",
    "Reaction to burns": "燃烧反应",
    "Reaction to electricity": "电反应",
    "Reaction to chemical burns": "化学灼烧反应",
    "Ergonomics": "人体工学",
    "Attack Speed": "攻击速度",
    "Penetration": "穿透",
    "Maximum damage": "最高伤害",
    "Magazine size": "弹匣容量",
    "Magazine size:": "弹匣容量",
    "Full reload": "完整换弹",
    "Reloading one round": "单发装填",
    "Additional magazine size": "附加弹匣容量",
    "Weapon reach": "武器攻击距离",
    "Damage modifier on mutants": "对变异体伤害",
    "Limb damage modifier": "四肢伤害倍率",
    "Damage to structures": "对建筑伤害",
    "Explosion damage": "爆炸伤害",
    "Frost damage": "寒冷伤害",
    "Laceration damage": "撕裂伤害",
    "Chemical damage": "化学伤害",
    "Electric damage": "电伤害",
    "Fire damage": "火焰伤害",
    "Absolute damage": "绝对伤害",
    "Damage at center": "中心伤害",
    "Damage range": "伤害范围",
    "Earnings from events": "活动收益",
    "Condition": "状态",
    "Inner protection": "内部防护",
    "Effectiveness": "效率",
    "Capacity": "容量",
    "Number of projectiles": "弹丸数量",
    "Duration": "持续时间",
    "Usage time": "使用时间",
    "Fuse time": "引信时间",
    "Time until detonation": "引爆时间",
    "Time until activation": "激活时间",
    "Max. blindness duration": "最大致盲时间",
    "Scanning angle": "扫描角度",
    "Passive range": "被动范围",
    "Active range": "主动范围",
    "Charge": "充能",
    "Movement speed": "移动速度",
    "Running speed": "奔跑速度",
    "Carry weight": "负重",
    "Recoil": "后坐力",
    "Sway": "晃动",
    "Stability": "稳定性",
    "Stabilization": "稳定化",
    "Stopping protection": "稳定性",
    "Aim speed": "瞄准速度",
    "Draw speed": "拔枪速度",
    "Recoil buildup": "后坐力增长",
    "Damage absorption": "伤害吸收",
    "Poison": "中毒",
    "Speed": "速度",
    "Damage": "伤害",
    "Rate of fire": "射速",
    "Magazine capacity": "弹匣容量",
    "Maximum distance": "最大射程",
    "Weight": "重量",
    "Durability": "耐久",
    "Max. durability": "最大耐久",
    "Spread": "散布",
    "Hip-fire spread": "腰射散布",
    "Vertical recoil": "垂直后坐力",
    "Horizontal recoil": "水平后坐力",
    "Reload": "换弹时间",
    "Tactical reload": "战术换弹时间",
    "Tactical Reload": "战术换弹时间",
    "Draw time": "拔枪时间",
    "Aiming time": "瞄准时间",
    "Aiming Movement Speed": "瞄准时移动速度",
    "Weapon ergonomics": "人体工学",
    "Ammo type": "弹药类型",
    "Type": "槽位",
    "Size": "尺寸",
    "Class": "类别",
    "Rank": "等级",
    "Armor-penetration": "穿甲",
    "Stopping power": "停止作用",
    "Plate penetration": "护甲板穿透",
    "Plate durability damage": "护甲板耐久伤害",
    "Additional stats": "附加属性",
    "Triggers when": "触发条件",
    "Reduces damage by": "减伤",
    "Charge required to activate": "激活所需充能",
}

ARTEFACT_STAT_CN = {
    "Reload": "充能时间",
}

BALANCE_STAT_CN = {
    key.casefold(): value for key, value in ITEM_STAT_CN.items()
}
BALANCE_STAT_CN.update(
    {
        "speed": "移动速度",
        "additional speed": "附加移动速度",
        "bonus speed": "额外移动速度",
        "bonus properties": "额外属性",
        "additional properties": "附加属性",
        "main properties": "主属性",
        "type": "类型",
        "weak": "弱",
        "standard": "标准",
        "minimum damage": "最低伤害",
        "maximum damage": "最高伤害",
        "headshot damage": "爆头伤害",
        "limb damage": "四肢伤害",
        "minimum damage distance": "最小伤害距离",
        "maximum damage distance": "最大伤害距离",
        "speed during aiming": "瞄准时移动速度",
        "recoil increase": "后坐力增长",
        "first shot recoil multiplier": "首发后坐力倍率",
        "stamina to base stats": "基础耐力",
        "bleed": "流血",
        "extra property": "额外属性",
        "additional property": "附加属性",
    }
)
BALANCE_PREFIX_CN = {
    "added": "新增",
    "removed": "移除",
    "increased": "提高",
    "reduced": "降低",
    "changed": "调整",
}
BALANCE_VALUE_CN = {
    "Weak": "弱",
    "Standard": "标准",
    "Strong": "强",
    "High": "高",
    "Medium": "中",
    "Low": "低",
}


def _balance_values(text: str) -> str:
    value = text
    for source, target in BALANCE_VALUE_CN.items():
        value = re.sub(
            r"(?<![A-Za-z])" + re.escape(source) + r"(?![A-Za-z])",
            target,
            value,
        )
    return value


def _balance_change_text(text: str) -> str:
    """Translate the label of an official English balance line.

    Numbers, arrows and unknown labels stay verbatim so the card still matches
    the official patch note.
    """
    value = str(text or "").strip().strip("|").strip()
    if not value or re.search(r"[\u4e00-\u9fff]", value):
        return value
    bare = value.rstrip(":：").strip()
    direct = BALANCE_STAT_CN.get(bare.casefold())
    if direct:
        if bare.casefold() in {"bonus properties", "additional properties", "main properties"}:
            return f"{direct}："
        return direct

    label_match = re.match(
        r"^(?P<label>[A-Za-z][A-Za-z .'’()/+-]*?)\s*[:：]\s*(?P<value>.+)$",
        value,
    )
    if label_match:
        label = label_match.group("label").strip()
        prefix = ""
        folded = label.casefold()
        for source, target in BALANCE_PREFIX_CN.items():
            if folded.startswith(source + " "):
                prefix = target
                label = label[len(source) + 1 :].strip()
                break
        translated = BALANCE_STAT_CN.get(label.casefold())
        if translated:
            rest = _balance_values(label_match.group("value").strip())
            return f"{prefix}{translated}：{rest}"

    for source in sorted(BALANCE_STAT_CN, key=len, reverse=True):
        match = re.match(
            r"^" + re.escape(source) + r"\s+(.+)$", value, re.IGNORECASE
        )
        if match:
            return f"{BALANCE_STAT_CN[source]} {_balance_values(match.group(1))}"
    return _balance_values(value)


def _balance_dedupe_key(text: str) -> str:
    return re.sub(r"[\s:：,，;；。]", "", str(text or ""))


def _clean_patch_title(title: str) -> str:
    value = re.sub(
        r"\s*\[?\d{1,4}[./-]\d{1,2}[./-]\d{2,4}\]?\s*$", "", str(title or "")
    ).strip()
    return value or str(title or "").strip()


def _item_stat_label(label: str, category: str = "") -> str:
    if category.startswith("artefact"):
        value = ARTEFACT_STAT_CN.get(label)
        if value:
            return value
    return ITEM_STAT_CN.get(label, label)


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


def _money(value: Any) -> str:
    number = _safe_int(value)
    return "未知" if number is None else f"{number:,} 卢布"


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_auction_time(value: Any) -> datetime | None:
    """Public UTC timestamp parser used by the dated-history paginator."""
    return _parse_dt(value)


def _fmt_dt(value: Any, *, with_year: bool = False) -> str:
    dt = _parse_dt(value)
    if dt is None:
        return "未知"
    fmt = "%Y-%m-%d %H:%M" if with_year else "%m-%d %H:%M"
    return f"{dt.astimezone(CST).strftime(fmt)} UTC+8"


def _remaining(value: Any, now: datetime | None = None) -> str:
    dt = _parse_dt(value)
    if dt is None:
        return "剩余时间未知"
    now = now or datetime.now(timezone.utc)
    seconds = (dt - now).total_seconds()
    if seconds <= 0:
        return "已结束"
    if seconds >= 86400:
        return f"剩 {int(seconds // 86400)} 天"
    if seconds >= 3600:
        return f"剩 {int(seconds // 3600)} 小时"
    return f"剩 {max(1, int(seconds // 60))} 分钟"


def _quality_of(lot: dict[str, Any]) -> int | None:
    additional = lot.get("additional")
    if not isinstance(additional, dict):
        return None
    for key in ("qlt", "quality", "itemQuality", "item_quality"):
        value = additional.get(key)
        number = _safe_int(value)
        if number is not None and 0 <= number <= 5:
            return number
        if isinstance(value, str) and value.strip().lower() in QUALITY_ALIASES:
            return QUALITY_ALIASES[value.strip().lower()]
    return None


def auction_quality_of(entry: dict[str, Any]) -> int | None:
    """Public quality accessor for pagination stop conditions."""
    return _quality_of(entry)


def _level_of(lot: dict[str, Any]) -> int:
    additional = lot.get("additional")
    if not isinstance(additional, dict):
        return 0
    for key in ("ptn", "level", "upgradeLevel", "upgrade_level", "itemLevel"):
        number = _safe_int(additional.get(key))
        if number is not None and number > 0:
            return number
    return 0


def quality_label(quality: int | None) -> str:
    if quality is None:
        return "品质未标注"
    name, color = QUALITY_NAMES.get(quality, (f"品质{quality}", ""))
    return f"{name}（{color}）" if color else name


def parse_quality_query(argument: str) -> tuple[str, int | None]:
    """Split a trailing quality word from an item query.

    ``/sz 市场 原子 粉`` -> ("原子", 3)
    ``/sz 市场 原子 稀有`` -> ("原子", 3)
    """
    text = str(argument or "").strip()
    if not text:
        return text, None
    parts = text.rsplit(maxsplit=1)
    if len(parts) == 2:
        candidate = parts[1].strip().lower()
        if candidate in QUALITY_ALIASES and parts[0].strip():
            return parts[0].strip(), QUALITY_ALIASES[candidate]
    return text, None


AUCTION_DATE_RE = re.compile(r"^(?:(\d{2}|\d{4})[./])?(\d{1,2})[./](\d{1,2})$")


def parse_auction_date(token: str, *, now: datetime | None = None) -> date_cls | None:
    """Parse ``6.11`` / ``25.6.11`` / ``2025/6/11`` as a calendar date.

    A missing year means the current UTC+8 year.  Invalid calendar days
    simply do not match, so item names containing numbers are left alone.
    """
    match = AUCTION_DATE_RE.match(str(token or "").strip())
    if not match:
        return None
    year_text, month_text, day_text = match.groups()
    local_year = (now or datetime.now(timezone.utc)).astimezone(CST).year
    if year_text is None:
        year = local_year
    else:
        year = int(year_text)
        if len(year_text) == 2:
            year += 2000
    try:
        return date_cls(year, int(month_text), int(day_text))
    except ValueError:
        return None


def auction_day_cutoff(day: date_cls) -> datetime:
    """Return the inclusive end of ``day`` in UTC+8."""
    return datetime.combine(day, time_cls.max, tzinfo=CST)


def parse_auction_query(
    argument: str, *, now: datetime | None = None
) -> tuple[str, int | None, date_cls | None, int | None]:
    """Split ``item [quality] [date] [count]`` from an auction argument.

    The order is fixed, and every trailing part is optional except the item.
    A count is only accepted together with both a quality and a date.
    """
    text = " ".join(str(argument or "").split())
    if not text:
        return "", None, None, None
    parts = text.split(" ")

    if len(parts) >= 3 and parts[-1].isdigit():
        day = parse_auction_date(parts[-2], now=now)
        if day is not None:
            if len(parts) < 4 or parts[-3].lower() not in QUALITY_ALIASES:
                raise ValueError(
                    "数量需要同时指定品质和时间，例如：/sz 拍卖 原子 粉 6.11 20"
                )
            count = int(parts[-1])
            if not 1 <= count <= 200:
                raise ValueError("数量请填 1–200。")
            item = " ".join(parts[:-3]).strip()
            if not item:
                raise ValueError("请填写要查询的物品名或 ID。")
            return item, QUALITY_ALIASES[parts[-3].lower()], day, count

    if len(parts) >= 2:
        day = parse_auction_date(parts[-1], now=now)
        if day is not None:
            item_end = len(parts) - 1
            quality: int | None = None
            if len(parts) >= 3:
                candidate = QUALITY_ALIASES.get(parts[-2].lower())
                if candidate is not None:
                    quality = candidate
                    item_end = len(parts) - 2
            item = " ".join(parts[:item_end]).strip()
            if not item:
                raise ValueError("请填写要查询的物品名或 ID。")
            return item, quality, day, None

    if len(parts) >= 2:
        candidate = QUALITY_ALIASES.get(parts[-1].lower())
        if candidate is not None:
            item = " ".join(parts[:-1]).strip()
            if item:
                return item, candidate, None, None
    return text, None, None, None


def _lot_price(lot: dict[str, Any]) -> int:
    current = _safe_int(lot.get("currentPrice"))
    start = _safe_int(lot.get("startPrice"))
    buyout = _safe_int(lot.get("buyoutPrice"))
    if current and current > 0:
        return current
    if start and start > 0:
        return start
    return buyout or 0


def _unit_price(total: Any, amount: Any) -> int | None:
    total_int = _safe_int(total)
    amount_int = _safe_int(amount) or 0
    if total_int is None or amount_int <= 0:
        return None
    return int(total_int / amount_int)


def _additional_hint(lot: dict[str, Any]) -> str:
    additional = lot.get("additional")
    if not isinstance(additional, dict):
        return ""
    pieces: list[str] = []
    seen: set[str] = set()
    for key, label in (
        ("quality", "品质"),
        ("qlt", "品质"),
        ("level", "等级"),
        ("upgradeLevel", "强化"),
        ("durability", "耐久"),
    ):
        value = additional.get(key)
        if value in (None, "") or label in seen:
            continue
        seen.add(label)
        pieces.append(f"{label} {value}")
    return "｜" + "，".join(pieces) if pieces else ""


def _stat_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("value", "total", "amount", "integer", "decimal", "duration", "seconds"):
            if key in value and value[key] not in (None, ""):
                return value[key]
        for candidate in value.values():
            if isinstance(candidate, (str, int, float)) and not isinstance(candidate, bool):
                return candidate
        return None
    return value


def _format_stat(stat: dict[str, Any]) -> str | None:
    stat_id = str(stat.get("id") or "").strip()
    value = _stat_value(stat.get("value"))
    if not stat_id or value in (None, ""):
        return None
    label = STAT_LABELS.get(stat_id.lower(), stat_id)
    if str(stat.get("type") or "").upper() == "DURATION":
        value = _fmt_duration(value)
    elif isinstance(value, float):
        value = round(value, 2)
    return f"{label} {value}"


def _fmt_duration(seconds: Any) -> str:
    value = _safe_int(seconds)
    if value is None or value < 0:
        return "未知"
    minutes = value // 60
    if minutes < 60:
        return f"{minutes} 分钟"
    if minutes % 60 == 0:
        return f"{minutes // 60} 小时"
    return f"{minutes // 60} 小时 {minutes % 60} 分"


def _clan_line(clan: dict[str, Any]) -> str:
    name = str(clan.get("name") or "未知战队")
    tag = clan.get("tag")
    label = f"{name} [{tag}]" if tag else name
    level = clan.get("level")
    members = clan.get("memberCount")
    alliance_raw = str(clan.get("alliance") or "未知")
    alliance = ALLIANCE_LABELS.get(alliance_raw.lower(), alliance_raw)
    parts = [label]
    if level is not None:
        parts.append(f"等级 {level}")
    if members is not None:
        parts.append(f"成员 {members}")
    parts.append(f"阵营 {alliance}")
    return "｜".join(parts)


def _truncate(text: str, limit: int = 3500) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n……（结果过长已截断）"


def _card(
    title: str,
    subtitle: list[str],
    sections: list[tuple[str, list[str]]],
    footer: str = "",
    *,
    limit: int = 3500,
) -> str:
    lines = [SEP, title]
    lines.extend(subtitle)
    lines.append(SEP)
    for heading, rows in sections:
        lines.append("")
        lines.append(f"● {heading}")
        lines.extend(rows)
    if footer:
        lines.extend(["", SEP, footer])
    return _truncate("\n".join(lines), limit)


QUALITY_COLORS = {
    0: "#E7EDF5",
    1: "#53C353",
    2: "#4EA8FF",
    3: "#FF6FB5",
    4: "#FF5C5C",
    5: "#FFD166",
}


ITEM_RANK_COLORS = {
    "RANK_NEWBIE": "#53C353",
    "RANK_STALKER": "#4EA8FF",
    "RANK_VETERAN": "#FF6FB5",
    "RANK_MASTER": "#FF5C5C",
    "RANK_LEGEND": "#FFD166",
    "DEFAULT": "#E7EDF5",
    "QUEST_ITEM": "#FFB454",
    "EXCLUSIVE": "#FF5C5C",
}


def item_rank_color(color: Any) -> str:
    return ITEM_RANK_COLORS.get(str(color or "").strip().upper(), "#E7EDF5")


def _quality_color(quality: int | None) -> str:
    if quality is None:
        return "#93A6BA"
    return QUALITY_COLORS.get(quality, "#93A6BA")


def _remaining_text(value: Any, now: datetime | None = None) -> str:
    dt = _parse_dt(value)
    if dt is None:
        return "剩余未知"
    now = now or datetime.now(timezone.utc)
    seconds = int((dt - now).total_seconds())
    if seconds <= 0:
        return "已结束"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes or not parts:
        parts.append(f"{minutes}分钟")
    return "剩余" + "".join(parts)


def _cn_datetime(value: Any) -> str:
    dt = _parse_dt(value)
    if dt is None:
        return "未知"
    local = dt.astimezone(CST)
    return f"{local.year}/{local.month}/{local.day} {local.hour:02d}:{local.minute:02d}"


def _auction_short_name(item_label: str | None, item_id: str) -> str:
    return (item_label or item_id).split(" / ", 1)[0]


def _auction_level_name(short: str, lot: dict[str, Any]) -> str:
    level = _level_of(lot)
    return f"{short}＋{level}" if level > 0 else short


def _display_price(value: Any) -> str:
    number = _safe_int(value)
    return "\\" if number is None or number <= 0 else f"{number:,}"


def build_auction_view(
    item_id: str,
    lots_payload: dict[str, Any] | None,
    history_payload: dict[str, Any] | None,
    region: str,
    *,
    now: datetime | None = None,
    item_label: str | None = None,
    quality_filter: int | None = None,
    before: datetime | None = None,
    history_limit: int | None = None,
    non_artifact: bool = False,
    item_color: str | None = None,
) -> dict[str, Any] | None:
    lots_payload = lots_payload if isinstance(lots_payload, dict) else {}
    history_payload = history_payload if isinstance(history_payload, dict) else {}
    raw_lots = lots_payload.get("lots")
    raw_history = history_payload.get("prices")
    lots = [x for x in raw_lots if isinstance(x, dict)] if isinstance(raw_lots, list) else []
    history = [x for x in raw_history if isinstance(x, dict)] if isinstance(raw_history, list) else []
    lots = [lot for lot in lots if _lot_price(lot) > 0]
    history = [entry for entry in history if (_safe_int(entry.get("price")) or 0) > 0]
    if non_artifact:
        quality_filter = None

    if quality_filter is not None:
        lots = [lot for lot in lots if _quality_of(lot) == quality_filter]
        history = [entry for entry in history if _quality_of(entry) == quality_filter]

    if before is not None:
        lots = []
        dated: list[dict[str, Any]] = []
        for entry in history:
            timestamp = _parse_dt(entry.get("time"))
            if timestamp is not None and timestamp <= before:
                dated.append(entry)
        history = dated

    now = (now or datetime.now(timezone.utc)).astimezone(CST)
    short = _auction_short_name(item_label, item_id)
    title = f"{item_label}（{item_id}）" if item_label and item_label != item_id else item_id

    active: list[dict[str, Any]] = []
    for lot in lots:
        quality = None if non_artifact else _quality_of(lot)
        buyout = _safe_int(lot.get("buyoutPrice"))
        start = _safe_int(lot.get("startPrice"))
        amount = _safe_int(lot.get("amount")) or 1
        effective_total = buyout if buyout and buyout > 0 else start
        unit_value = _unit_price(effective_total, amount)
        sort_price = (buyout or start or _lot_price(lot)) if not non_artifact else (buyout or start or 0)
        name = _auction_level_name(short, lot)
        if non_artifact and amount > 1:
            name = f"{name}×{amount}"
        active.append(
            {
                "name": name,
                "quality": quality,
                "color": (
                    (item_color or "#E7EDF5")
                    if non_artifact
                    else _quality_color(quality)
                ),
                "start": "\\" if non_artifact else _display_price(start),
                "buyout": _display_price(buyout),
                "unit_price": (
                    f"{unit_value:,}" if unit_value is not None else "\\"
                ),
                "unit_value": unit_value or 0,
                "amount": amount,
                "remaining": _remaining_text(lot.get("endTime"), now),
                "sort_price": sort_price,
            }
        )
    active.sort(key=lambda row: row["sort_price"], reverse=True)
    if non_artifact and active:
        unit_values = [
            row["unit_value"] for row in active if row.get("unit_value", 0) > 0
        ]
        if unit_values:
            lowest_unit = min(unit_values)
            for row in active:
                if row.get("unit_value") == lowest_unit:
                    row["lowest"] = True
                    row["lowest_label"] = "最低单价"
                    break

    recent: dict[int | None, list[dict[str, Any]]] = {}
    for entry in history:
        quality = None if non_artifact else _quality_of(entry)
        price = _safe_int(entry.get("price"))
        amount = _safe_int(entry.get("amount")) or 1
        unit_value = _unit_price(price, amount)
        name = _auction_level_name(short, entry)
        if non_artifact and amount > 1:
            name = f"{name}×{amount}"
        recent.setdefault(quality, []).append(
            {
                "name": name,
                "quality": quality,
                "color": (
                    (item_color or "#E7EDF5")
                    if non_artifact
                    else _quality_color(quality)
                ),
                "price": f"{price:,}" if price is not None else "未知",
                "price_value": price or 0,
                "unit_price": (
                    f"{unit_value:,}" if unit_value is not None else "\\"
                ),
                "unit_value": unit_value or 0,
                "amount": amount,
                "time": _cn_datetime(entry.get("time")),
                "ts": _parse_dt(entry.get("time")) or datetime.min.replace(tzinfo=timezone.utc),
            }
        )
    for rows in recent.values():
        rows.sort(key=lambda row: row.get("ts") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    if history_limit is not None:
        limit = max(1, min(history_limit, 200))
    elif non_artifact:
        limit = 10
    elif before is not None:
        limit = 20 if quality_filter is not None else 5
    elif quality_filter is not None:
        limit = 10
    else:
        limit = 3
    total_limit = limit if non_artifact else None
    if non_artifact:
        rows = recent.get(None, [])[:limit]
        if rows:
            unit_values = [
                row.get("unit_value", 0) for row in rows if row.get("unit_value", 0) > 0
            ]
            if unit_values:
                lowest = min(unit_values)
                for row in rows:
                    if row.get("unit_value", 0) == lowest:
                        row["lowest"] = True
                        row["lowest_label"] = "最低单价"
                        break
        groups = [
            {
                "quality": None,
                "label": "",
                "color": item_color or "#E7EDF5",
                "rows": rows,
            }
        ] if rows else []
    else:
        groups = []
        for quality in sorted(
            recent, key=lambda q: -1 if q is None else q, reverse=True
        ):
            groups.append(
                {
                    "quality": quality,
                    "label": quality_label(quality),
                    "color": _quality_color(quality),
                    "rows": recent[quality][:limit],
                }
            )

    if not active and not groups:
        return None

    before_label = None
    history_note = ""
    if before is not None:
        local_before = before.astimezone(CST)
        before_label = f"{local_before.year}/{local_before.month}/{local_before.day}"
        if non_artifact or quality_filter is not None:
            history_note = f"截至 {before_label}｜最多 {limit} 条"
        else:
            history_note = f"截至 {before_label}｜每品质最多 {limit} 条"

    source = str(history_payload.get("source") or "official")
    if source == "sc_core":
        data_note = "历史数据：SC CORE 第三方存档｜价格随时变化｜时间为 UTC+8"
    elif source == "official+sc_core":
        data_note = "历史数据：官方 API + SC CORE 第三方存档｜价格为卢布｜时间为 UTC+8"
    else:
        data_note = "数据来自官方 API｜价格随时变化｜时间为 UTC+8（北京时间）"

    return {
        "item_id": item_id,
        "item_label": item_label,
        "title": title,
        "short": short,
        "region": region.upper(),
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "quality_filter": quality_filter,
        "quality_filter_label": quality_label(quality_filter) if quality_filter is not None else None,
        "active": active,
        "recent_groups": groups,
        "recent_limit": limit,
        "recent_total_limit": total_limit,
        "non_artifact": non_artifact,
        "history_only": before is not None,
        "before": before_label,
        "history_note": history_note,
        "history_source": source,
        "data_note": data_note,
    }


def build_empty_auction_view(
    item_id: str,
    item_label: str | None,
    region: str,
    *,
    now: datetime | None = None,
    quality_filter: int | None = None,
    before: datetime | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Minimal view used to render a friendly empty auction card."""
    now = (now or datetime.now(timezone.utc)).astimezone(CST)
    short = _auction_short_name(item_label, item_id)
    title = f"{item_label}（{item_id}）" if item_label and item_label != item_id else item_id
    before_label = None
    if before is not None:
        local_before = before.astimezone(CST)
        before_label = f"{local_before.year}/{local_before.month}/{local_before.day}"
    return {
        "item_id": item_id,
        "item_label": item_label,
        "title": title,
        "short": short,
        "region": region.upper(),
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "quality_filter": quality_filter,
        "quality_filter_label": quality_label(quality_filter) if quality_filter is not None else None,
        "active": [],
        "recent_groups": [],
        "recent_limit": 5,
        "recent_total_limit": None,
        "history_only": before is not None,
        "before": before_label,
        "history_note": "",
        "empty": True,
        "empty_name": short,
        "empty_color": _quality_color(quality_filter) if quality_filter is not None else "#E7EDF5",
        "empty_note": note,
    }


def format_auction_text(view: dict[str, Any] | None) -> str:
    if not view:
        return "未找到相关数据，请检查物品 ID / 角色名是否正确。"
    lines = [
        SEP,
        "STALZONE · 拍卖行",
        f"{view['title']}｜{view['region']}",
        f"查询时间：{view['now']} UTC+8",
    ]
    if view.get("empty"):
        lines.append(SEP)
        lines.append("")
        if view.get("before"):
            lines.append(f"截至 {view['before']}")
        lines.append(
            f"未查到关于「{view.get('empty_name') or view.get('short')}」的成交记录。"
        )
        if view.get("empty_note"):
            lines.append(view["empty_note"])
        lines.extend([SEP, "数据来自官方 API｜价格为卢布｜时间为 UTC+8（北京时间）"])
        return "\n".join(lines)
    if view["quality_filter"] is not None:
        lines.append(f"仅看品质：{quality_label(view['quality_filter']).split('（', 1)[0]}")
    is_non_artifact = bool(view.get("non_artifact"))
    lines.append(SEP)
    if view.get("history_only"):
        if view.get("recent_total_limit") is not None or view["quality_filter"] is not None:
            scope = "最多"
        else:
            scope = "每品质最多"
        lines.extend([
            "",
            f"历史成交（截至 {view['before']}，{scope} {view['recent_limit']} 条，按时间倒序）",
        ])
        if is_non_artifact:
            lines.append("  名称  成交价  单价  时间")
    else:
        lines.extend(["", "在售（按买断价从高到低）"])
        if view["active"]:
            if is_non_artifact:
                lines.append("  名称  起拍  买断  单价  剩余时间")
            for index, row in enumerate(view["active"], 1):
                if is_non_artifact:
                    marker_text = row.get("lowest_label") or "最低单价"
                    marker = f" [{marker_text}]" if row.get("lowest") else ""
                    lines.append(
                        f"{index}. {row['name']}{marker}  {row['start']}  {row['buyout']}  "
                        f"{row['unit_price']}  {row['remaining']}"
                    )
                else:
                    lines.append(
                        f"{index}. {row['name']}  {row['start']}  {row['buyout']}  {row['remaining']}"
                    )
        else:
            lines.append("当前无在售")
        if view.get("recent_total_limit") is not None:
            recent_heading = (
                f"最近成交（最多 {view['recent_total_limit']} 条，按时间倒序）"
            )
        else:
            recent_heading = (
                f"最近成交（每品质最多 {view['recent_limit']} 条，按时间倒序）"
            )
        lines.extend(["", SEP, recent_heading])
        if is_non_artifact:
            lines.append("  名称  成交价  单价  时间")
    if view["recent_groups"]:
        for group in view["recent_groups"]:
            label = str(group.get("label") or "").split("（", 1)[0]
            if label:
                lines.append(f"【{label}】")
            for row in group["rows"]:
                marker_text = row.get("lowest_label") or (
                    "最低单价" if is_non_artifact else "最低价"
                )
                marker = f" [{marker_text}]" if row.get("lowest") else ""
                if is_non_artifact:
                    lines.append(
                        f"  {row['name']}{marker}  {row['price']}  "
                        f"{row['unit_price']}  {row['time']}"
                    )
                else:
                    amount = f" ×{row['amount']}" if row["amount"] > 1 else ""
                    lines.append(
                        f"  {row['name']}{marker}  {row['price']}{amount}  {row['time']}"
                    )
    else:
        lines.append("暂无成交记录")
    if view["quality_filter"] is None and not view.get("non_artifact"):
        lines.append("")
        lines.append("可按品质筛选：物品名 + 白/绿/蓝/粉/红/金（或 常见/罕见/特殊/稀有/独特/传奇）")
    lines.extend([
        SEP,
        view.get("data_note")
        or "数据来自官方 API｜价格随时变化｜时间为 UTC+8（北京时间）",
    ])
    return _truncate("\n".join(lines))


def format_auction(
    item_id: str,
    lots_payload: dict[str, Any] | None,
    history_payload: dict[str, Any] | None,
    region: str,
    *,
    now: datetime | None = None,
    item_label: str | None = None,
    quality_filter: int | None = None,
    before: datetime | None = None,
    history_limit: int | None = None,
    non_artifact: bool = False,
) -> str:
    view = build_auction_view(
        item_id,
        lots_payload,
        history_payload,
        region,
        now=now,
        item_label=item_label,
        quality_filter=quality_filter,
        before=before,
        history_limit=history_limit,
        non_artifact=non_artifact,
    )
    if view is None and quality_filter is not None:
        return f"没有找到{quality_label(quality_filter)}的在售或成交记录。"
    return format_auction_text(view)


def format_elapsed_hms(seconds: Any) -> str:
    """Format a duration as ``Xh MMm SSs`` with two-digit minutes/seconds."""
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}小时{minutes:02d}分{secs:02d}秒"


def build_emission_view(
    payload: dict[str, Any] | None,
    region: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the shared text/image model for an emission query.

    The headline counts from the end of the last completed emission.  While an
    emission is in progress the useful number is its current duration, so the
    headline switches to "本次风暴已持续" and the previous storm stays visible
    as secondary information.
    """
    if not isinstance(payload, dict):
        return {}

    current = _parse_dt(payload.get("currentStart"))
    previous_start = _parse_dt(payload.get("previousStart"))
    previous_end = _parse_dt(payload.get("previousEnd"))
    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_utc = now_utc.astimezone(timezone.utc)
    now_cst = now_utc.astimezone(CST)

    active = current is not None
    if active:
        reference = current
        headline = "本次风暴已持续"
        state_key = "active"
        state_label = "风暴进行中"
        reference_line = f"本次风暴开始：{_fmt_dt(current, with_year=True)}"
    else:
        reference = previous_end or previous_start
        headline = "距离上次风暴"
        state_key = "idle" if reference else "unknown"
        state_label = "无辐射爆发" if reference else "暂无数据"
        if previous_end:
            reference_line = f"上次风暴结束：{_fmt_dt(previous_end, with_year=True)}"
        elif previous_start:
            reference_line = f"上次风暴开始：{_fmt_dt(previous_start, with_year=True)}"
        else:
            reference_line = "API 未返回上次风暴记录"

    elapsed_seconds = (
        max(0, int((now_utc - reference).total_seconds()))
        if reference is not None
        else None
    )
    elapsed_text = (
        format_elapsed_hms(elapsed_seconds)
        if elapsed_seconds is not None
        else "暂无数据"
    )

    details: list[str] = []
    if active:
        if previous_start or previous_end:
            details.append(f"上次风暴：{_fmt_dt(previous_start, with_year=True)} 开始")
            details.append(f"结束：{_fmt_dt(previous_end, with_year=True)}")
        else:
            details.append("API 未返回上次风暴记录")
    else:
        if previous_end and previous_start:
            details.append(f"上次开始：{_fmt_dt(previous_start, with_year=True)}")
        if not reference:
            details.append("API 未返回上次风暴记录")

    return {
        "region": str(region).upper(),
        "now": now_cst.strftime("%Y-%m-%d %H:%M:%S"),
        "state_key": state_key,
        "state_label": state_label,
        "headline": headline,
        "elapsed_seconds": elapsed_seconds,
        "elapsed_text": elapsed_text,
        "reference_line": reference_line,
        "details": details[:2],
        "footer": "官方 API 不提供下一次爆发时间｜" + UTC_NOTE,
    }


def format_emission(
    payload: dict[str, Any] | None,
    region: str,
    *,
    now: datetime | None = None,
    view: dict[str, Any] | None = None,
) -> str:
    view = view if isinstance(view, dict) and view else build_emission_view(
        payload, region, now=now
    )
    if not view:
        return "未找到辐射爆发数据，请检查区服配置。"

    return _card(
        "STALZONE · 辐射爆发",
        [f"{view['region']}｜{view['now']} UTC+8"],
        [
            (view["headline"], [view["elapsed_text"], f"当前：{view['state_label']}"]),
            ("上次爆发", [view["reference_line"], *view["details"]]),
        ],
        view["footer"],
    )


STAT_PRIORITY = [
    "level",
    "character_level",
    "kil",
    "ast",
    "dea",
    "bul-dea",
    "exp-dea",
    "ble-to-dea",
    "npc-kil",
    "mut-kil",
    "kills-ops",
    "kills-bf",
    "deaths-bf",
    "won-bf",
    "lost-bf",
    "pres-kills",
    "pres-deaths",
    "completed-ops",
    "playtime",
]


def _profile_stat_rows(stats: Any) -> list[str]:
    entries: list[tuple[int, int, str, str]] = []
    if isinstance(stats, list):
        for index, stat in enumerate(stats):
            if not isinstance(stat, dict):
                continue
            stat_id = str(stat.get("id") or "").strip()
            value = _stat_value(stat.get("value"))
            if not stat_id or value in (None, ""):
                continue
            key = stat_id.lower()
            if key not in STAT_LABELS:
                continue
            label = STAT_LABELS[key]
            if str(stat.get("type") or "").upper() == "DURATION":
                shown = _fmt_duration(value)
            elif isinstance(value, float):
                shown = round(value, 2)
            else:
                shown = value
            rank = STAT_PRIORITY.index(key) if key in STAT_PRIORITY else len(STAT_PRIORITY)
            if isinstance(shown, int) and abs(shown) >= 1000:
                shown = f"{shown:,}"
            entries.append((rank, index, label, str(shown)))

    entries.sort(key=lambda item: (item[0], item[1]))
    rows = [f"{label}：{shown}" for _, _, label, shown in entries]
    return rows or ["官方 API 未返回可读统计字段"]


HQ_PVP_DEATH_KEYS = (
    "bul-dea",
    "exp-dea",
    "ble-to-dea",
    "col-dea",
    "mel-dea",
    "melee-dea",
    "kni-dea",
)


def calculate_hq_pvp_score(stats: Any) -> dict[str, Any] | None:
    """Apply StalzoneHQ's documented Open World PvP estimate formula.

    Formula: ((kills + assists * 0.5) / (deaths * 0.33)) * 1000
    Deaths are the sum of bullet/explosion/bleeding/melee death counters.
    This is a third-party estimate, not an official combat rating.
    """
    if not isinstance(stats, list):
        return None
    values = {
        str(stat.get("id", "")).lower(): _stat_value(stat.get("value"))
        for stat in stats
        if isinstance(stat, dict)
    }
    kills = _safe_int(values.get("kil", values.get("kills")))
    assists = _safe_int(values.get("ast", values.get("assists")))
    deaths = sum(
        _safe_int(values.get(key)) or 0
        for key in HQ_PVP_DEATH_KEYS
    )
    if kills is None or assists is None or deaths <= 0:
        return None
    score = ((kills + assists * 0.5) / (deaths * 0.33)) * 1000
    return {
        "score": int(score),
        "kills": kills,
        "assists": assists,
        "deaths": deaths,
        "kd": kills / deaths,
    }


def build_profile_view(
    payload: dict[str, Any] | None,
    region: str,
    *,
    now: datetime | None = None,
    lunar: dict[str, Any] | None = None,
    lunar_url: str | None = None,
    hq_url: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload.get("username"):
        return {}
    try:
        from .pda_format import strip_pda_formatting
    except ImportError:
        from pda_format import strip_pda_formatting

    now = (now or datetime.now(timezone.utc)).astimezone(CST)
    name = str(payload.get("username"))
    status_raw = str(payload.get("status") or "")
    status_key = status_raw.strip().casefold()
    status_presence = STATUS_LABELS.get(status_key)
    bio = "" if status_presence else status_raw.strip()
    bio_lines: list[str] = []
    if bio:
        plain_bio = strip_pda_formatting(bio)
        bio_lines = [line.rstrip() for line in plain_bio.splitlines()]
        while bio_lines and not bio_lines[0].strip():
            bio_lines.pop(0)
        while bio_lines and not bio_lines[-1].strip():
            bio_lines.pop()

    alliance_raw = str(payload.get("alliance") or "")
    alliance = ALLIANCE_LABELS.get(alliance_raw.lower(), alliance_raw or "未知")
    last_login = _fmt_dt(payload.get("lastLogin"), with_year=True)
    state = status_presence or ("公开资料" if bio else "未知")

    basics = [
        f"阵营：{alliance}",
        f"状态：{state}",
        f"最后登录：{last_login}",
    ]

    clan = payload.get("clan") if isinstance(payload.get("clan"), dict) else {}
    info = clan.get("info") if isinstance(clan.get("info"), dict) else {}
    member = clan.get("member") if isinstance(clan.get("member"), dict) else {}
    clan_rows: list[str] = []
    if info.get("name"):
        clan_name = str(info.get("name"))
        tag = info.get("tag")
        clan_label = f"{clan_name} [{tag}]" if tag else clan_name
        rank = member.get("rank") or "未知"
        clan_level = info.get("level")
        clan_rows.append(clan_label)
        clan_rows.append(f"职位：{rank}｜战队等级：{clan_level if clan_level is not None else '未知'}")
    else:
        clan_rows.append("无 / API 未返回")

    hq = calculate_hq_pvp_score(payload.get("stats"))
    stat_rows = _profile_stat_rows(payload.get("stats"))

    lunar_rows: list[str] = []
    lunar_heading = "战队战报（Lunar 第三方）"
    player = lunar.get("player") if isinstance(lunar, dict) and isinstance(lunar.get("player"), dict) else {}
    if player:
        def num(key: str) -> str:
            value = player.get(key)
            if value is None:
                return "—"
            if isinstance(value, float):
                return f"{value:.2f}"
            number = _safe_int(value)
            return f"{number:,}" if number is not None else str(value)

        lunar_rows.append(
            f"K/D：{num('kd')}｜KDA：{num('kda')}｜战斗分：{num('total_score')}"
        )
        lunar_rows.append(
            f"场次：{num('matches_count')}｜击杀：{num('total_kills')}"
            f"｜死亡：{num('total_deaths')}｜助攻：{num('total_assists')}"
        )
        if player.get("clan_name"):
            tag = player.get("clan_tag")
            lunar_rows.append(
                f"战队：{player.get('clan_name')}" + (f" [{tag}]" if tag else "")
            )
        matches = lunar.get("matches")
        if isinstance(matches, list) and matches:
            recent = [m for m in matches if isinstance(m, dict)][:2]
            for match in recent:
                result = {"win": "胜", "loss": "负"}.get(
                    str(match.get("result")), match.get("result") or "—"
                )
                lunar_rows.append(
                    f"最近：{match.get('date', '—')} vs {match.get('opponent', '—')}"
                    f" {result}｜{match.get('kills', 0)}/{match.get('deaths', 0)}"
                    f"｜{match.get('score', 0)} 分"
                )
    elif lunar_url:
        lunar_heading = "更多战斗统计"
        lunar_rows.append("Lunar 未返回该玩家的战队战报（未收录或服务不可达）；可点击下方链接查看")

    displayed = payload.get("displayedAchievements")
    achievements = [str(x) for x in displayed[:5]] if isinstance(displayed, list) else []

    footer = "官方公开资料"
    if player:
        footer += " + Lunar 第三方战队战报"
    if lunar_url:
        footer += f"｜{lunar_url}"
    if hq_url:
        footer += f"｜HQ：{hq_url}"

    return {
        "name": name,
        "region": str(region).upper(),
        "alliance": alliance,
        "alliance_raw": alliance_raw,
        "state": state,
        "bio": bio,
        "bio_lines": bio_lines,
        "last_login": last_login,
        "clan_label": clan_rows[0] if clan_rows else "无 / API 未返回",
        "clan_rank": member.get("rank") or "未知",
        "clan_level": info.get("level"),
        "clan_rows": clan_rows,
        "hq": hq,
        "stat_rows": stat_rows,
        "lunar_rows": lunar_rows,
        "lunar_heading": lunar_heading,
        "lunar_url": lunar_url,
        "hq_url": hq_url,
        "achievements": achievements,
        "footer": footer,
        "now": now.strftime("%Y-%m-%d %H:%M"),
    }


def format_profile(
    payload: dict[str, Any] | None,
    region: str,
    *,
    now: datetime | None = None,
    lunar: dict[str, Any] | None = None,
    lunar_url: str | None = None,
    hq_url: str | None = None,
    view: dict[str, Any] | None = None,
) -> str:
    view = view if isinstance(view, dict) and view else build_profile_view(
        payload,
        region,
        now=now,
        lunar=lunar,
        lunar_url=lunar_url,
        hq_url=hq_url,
    )
    if not view:
        return "未找到相关数据，请检查物品 ID / 角色名是否正确。"

    basic_lines = [
        f"阵营：{view['alliance']}",
        f"状态：{view['state']}",
        f"最后登录：{view['last_login']}",
    ]
    sections: list[tuple[str, list[str]]] = [
        ("基本信息", basic_lines),
    ]
    if view.get("bio_lines"):
        sections.append(("简介", list(view["bio_lines"])))
    sections.append(("战队", list(view["clan_rows"])))

    hq = view.get("hq")
    if hq:
        sections.append(
            (
                "开放世界 PvP（StalzoneHQ 公式）",
                [
                    f"PvP Score：{hq['score']:,}",
                    f"击杀：{hq['kills']:,}｜助攻：{hq['assists']:,}｜估算死亡：{hq['deaths']:,}",
                    f"K/D（估算）：{hq['kd']:.2f}",
                    "公式：((击杀 + 助攻×0.5) / (估算死亡×0.33)) × 1000",
                    "注：HQ 页面显示的是其缓存分，可能与此实时统计值不同",
                ],
            )
        )
    sections.append(("官方统计", list(view["stat_rows"])))

    if view.get("lunar_rows"):
        sections.append((view["lunar_heading"], list(view["lunar_rows"])))
    if view.get("achievements"):
        sections.append(("展示成就", ["、".join(view["achievements"])]))

    return _card(
        "STALZONE · 角色资料",
        [f"{view['name']}｜{view['region']}", f"查询时间：{view['now']} UTC+8"],
        sections,
        view["footer"],
    )

def format_item(item: dict[str, Any], details: dict[str, Any] | None = None) -> str:
    details = details if isinstance(details, dict) else {}
    zh = str(item.get("zh") or "").strip()
    en = str(item.get("en") or "").strip()
    ru = str(item.get("ru") or "").strip()
    name = item.get("display") or zh or en or str(item.get("id") or "未知物品")
    rank = str(details.get("rank") or "").strip()
    category = str(item.get("cat") or "")
    identity = [
        f"ID：{item.get('id', '未知')}",
        f"类别：{item.get('cat_label') or item.get('cat') or '未知'}",
    ]
    if rank:
        identity.append(f"等级：{rank}")

    stats = details.get("stats")
    stat_rows: list[str] = []
    if isinstance(stats, list):
        normalized: list[tuple[str, str]] = []
        for stat in stats:
            if not isinstance(stat, dict):
                continue
            label = str(stat.get("label") or "").strip().rstrip(":")
            value = str(stat.get("value") or "").strip()
            if label and value:
                normalized.append((_item_stat_label(label, category), value))

        if category.startswith("artefact") and normalized:
            seen: set[str] = set()
            boundary: int | None = None
            for index, (label, _value) in enumerate(normalized):
                if label in seen:
                    boundary = index
                    break
                seen.add(label)
            base_rows: list[dict[str, Any]] = []
            additional_only: list[dict[str, Any]] = []
            for index, (label, value) in enumerate(normalized):
                is_additional = boundary is not None and index >= boundary
                if not is_additional:
                    base_rows.append({"label": label, "value": value, "extras": []})
                    continue
                base = next((row for row in base_rows if row["label"] == label), None)
                if base is not None:
                    if value not in base["extras"]:
                        base["extras"].append(value)
                    continue
                extra = next(
                    (row for row in additional_only if row["label"] == label), None
                )
                if extra is None:
                    additional_only.append(
                        {"label": label, "values": [value]}
                    )
                elif value not in extra["values"]:
                    extra["values"].append(value)
            for row in base_rows:
                if row["extras"]:
                    extras = "；".join(row["extras"])
                    stat_rows.append(
                        f"{row['label']}：{row['value']}（附加：{extras}）"
                    )
                else:
                    stat_rows.append(f"{row['label']}：{row['value']}")
            for row in additional_only:
                stat_rows.append(
                    f"{row['label']}（附加）：{'；'.join(row['values'])}"
                )
        else:
            seen_labels: dict[str, int] = {}
            for label, value in normalized:
                count = seen_labels.get(label, 0)
                seen_labels[label] = count + 1
                shown_label = label + (f"（附加{count if count > 1 else ''}）" if count else "")
                stat_rows.append(f"{shown_label}：{value}")
    falloff = [str(x) for x in details.get("falloff", []) if x] if isinstance(details.get("falloff"), list) else []
    if falloff:
        stat_rows.extend(f"距离衰减：{x}" for x in falloff[:2])

    sections = [
        ("标识", identity),
        ("属性", stat_rows or ["WIKI 未收录该物品的详细属性"]),
    ]
    description = str(details.get("description_zh") or details.get("description") or "").strip()
    if description:
        description = " ".join(description.split())
        sections.append(("描述", [description[:900]]))
    return _card(
        "STALZONE · 物品",
        [name],
        sections,
        f"查实时价格：/sz auction {item.get('id', '')}｜图标与属性来自 STALZONE WIKI｜中文名来自社区汉化（非官方）",
    )


def build_item_candidate_view(
    query: str, items: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the two-column candidate card model shared by the image renderer."""
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(items, 1):
        display = str(
            item.get("display")
            or item.get("zh")
            or item.get("en")
            or item.get("id")
            or "未知物品"
        ).strip()
        title, _, subtitle = display.partition(" / ")
        category = str(item.get("cat_label") or item.get("cat") or "").strip()
        meta = f"ID {item.get('id') or '—'}"
        if category:
            meta += f"｜{category}"
        entries.append(
            {
                "index": index,
                "title": title or display,
                "subtitle": subtitle.strip(),
                "meta": meta,
                "color": item_rank_color(item.get("color") or item.get("rank")),
                "icon_url": str(item.get("icon") or ""),
            }
        )
    return {
        "title": "STALZONE · 物品候选",
        "query": query,
        "count": len(entries),
        "entries": entries,
        "subtitle": f"没有精确匹配「{query}」，共 {len(entries)} 个候选",
        "hint": "回复 sz 候选 <序号> 直接按当前指令查询",
        "footer": "候选按相关性排序｜名称/ID 匹配忽略大小写",
    }


def build_clan_candidate_view(
    query: str, clans: list[dict[str, Any]]
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for index, clan in enumerate(clans, 1):
        name = str(clan.get("name") or "未命名战队")
        tag = str(clan.get("tag") or "").strip()
        title = f"{name} [{tag}]" if tag else name
        level = clan.get("level")
        members = clan.get("memberCount")
        subtitle_parts = []
        if level is not None:
            subtitle_parts.append(f"等级 {level}")
        if members is not None:
            subtitle_parts.append(f"成员 {members}")
        alliance_raw = str(clan.get("alliance") or "")
        alliance = ALLIANCE_LABELS.get(alliance_raw.lower(), alliance_raw or "未知")
        entries.append(
            {
                "index": index,
                "title": title,
                "subtitle": "｜".join(subtitle_parts),
                "meta": f"阵营 {alliance}｜ID {clan.get('id') or '—'}",
                "color": "#ffb454",
                "faction": alliance_raw,
            }
        )
    return {
        "title": "STALZONE · 战队候选",
        "query": query,
        "count": len(entries),
        "entries": entries,
        "subtitle": f"找到 {len(entries)} 个战队，请选择更精确的名称/标签",
        "hint": "回复 sz 候选 <序号> 直接查看该战队",
        "footer": "标签匹配不区分大小写｜也可用完整名称、标签或 UUID",
    }


def format_item_candidates(query: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return "未找到相关数据，请检查物品 ID / 物品名是否正确。"
    if len(items) == 1:
        return format_item(items[0])
    rows = []
    for index, item in enumerate(items, 1):
        name = item.get("display") or item.get("zh") or item.get("en") or str(item.get("id"))
        rows.append(f"{index}. {name}")
        rows.append(f"   ID {item.get('id')}｜{item.get('cat_label') or item.get('cat')}")
    return _card(
        "STALZONE · 物品候选",
        [
            f"没有精确匹配「{query}」，物品库里你可能想找：",
            "回复 sz 候选 <序号> 可直接按当前指令查询",
        ],
        [("候选", rows)],
        "例如当前想选第 1 个：sz 候选 1｜也可补充名称或 ID",
        limit=12000,
    )


def build_season_pass_view(result: Any) -> dict[str, Any]:
    """Build the forecast-first season-pass model used by text and images."""
    level = int(getattr(result, "level", 0))
    has_overload = int(getattr(result, "effective_overloads", 0)) > 0
    final_without = int(getattr(result, "final_level_without_overload", level))
    final_with = int(getattr(result, "final_level_with_overload", final_without))
    final_level = final_with if has_overload else final_without
    gain = final_level - level
    gain_without = final_without - level
    gain_with = final_with - level
    reward_levels = int(getattr(result, "weekly_reward_xp", 0)) // 1000
    reward_label = (
        f"{int(result.weekly_reward_xp):,}（{reward_levels} 级）"
        if getattr(result, "weekly_reward_xp", 0)
        else "0"
    )
    daily_rows = [
        ("每日任务经验", f"{int(result.daily_base_xp):,}"),
    ]
    if has_overload:
        daily_rows.append(
            (
                "每日超载经验",
                f"{int(result.daily_overload_xp):,}"
                f"（{int(result.effective_overloads)} 次 × 250）",
            )
        )
    daily_rows.append(("每日合计", f"{int(result.daily_total_xp):,}"))
    weekly_rows = [
        ("每周任务数", f"{int(result.weekly_tasks):,}"),
        ("每周任务经验", f"{int(result.daily_base_xp) * int(result.weekly_days):,}"),
        ("每周奖励经验", reward_label),
        ("每周合计", f"{int(result.weekly_total_xp):,}"),
    ]
    season_rows = [
        ("完整周数", f"{int(result.full_weeks)} 周 + {int(result.remainder_days)} 天"),
        ("实际完成天数", f"{int(result.active_days)} 天"),
    ]
    if has_overload:
        season_rows.append(("将消耗超载", f"{int(result.overloads_used)} 次"))
    season_rows.extend(
        [
            ("赛季总经验（不含超载）", f"{int(result.season_base_xp):,}"),
        ]
    )
    if has_overload:
        season_rows.append(("赛季总经验（含超载）", f"{int(result.season_total_xp):,}"))
    input_chips = [
        ("当前等级", f"Lv {level}"),
        ("每日任务", f"{int(result.daily_tasks)} 个"),
        ("剩余天数", f"{int(result.remaining_days)} 天"),
        ("每周计划", f"{int(result.weekly_days)} 天"),
    ]
    if has_overload:
        input_chips.insert(
            2,
            (
                "超载",
                f"{int(result.overloads)}（有效 {int(result.effective_overloads)}）",
            ),
        )
    footer = "每日 12:00 / 每周三 12:00 UTC+8 重置｜等级按 1000 经验/级估算"
    if has_overload:
        footer += "｜每日前 15 个任务可吃超载"
    note = (
        "预测等级完全来自每日/每周任务经验；未考虑季节性/周期活动、主线与支线任务等额外等级来源。"
    )
    if not has_overload:
        primary_label = ""
    else:
        primary_label = "使用超载"
    return {
        "level": level,
        "final_level": final_level,
        "final_without": final_without,
        "final_with": final_with,
        "gain": gain,
        "gain_without": gain_without,
        "gain_with": gain_with,
        "has_overload": has_overload,
        "effective_overloads": int(result.effective_overloads),
        "overloads": int(result.overloads),
        "daily_rows": daily_rows,
        "weekly_rows": weekly_rows,
        "season_rows": season_rows,
        "input_chips": input_chips,
        "note": note,
        "footer": footer,
        "primary_label": primary_label,
        "reward_label": reward_label,
    }


def format_season_pass(result: Any, *, view: dict[str, Any] | None = None) -> str:
    view = view if isinstance(view, dict) and view else build_season_pass_view(result)
    level = int(view.get("level") or 0)
    has_overload = bool(view.get("has_overload"))
    if has_overload:
        primary = (
            f"使用超载：{level} → {int(view['final_with'])} 级"
            f"（+{int(view['gain_with'])} 级）"
        )
    else:
        primary = (
            f"预测等级：{level} → {int(view['final_level'])} 级"
            f"（+{int(view['gain'])} 级）"
        )
    lines = [primary]
    if has_overload:
        lines.append(
            f"不使用超载：{level} → {int(view['final_without'])} 级"
            f"（+{int(view['gain_without'])} 级）"
        )
    lines.append(str(view.get("note") or ""))
    groups = [
        ("每日", [f"{key}：{value}" for key, value in view.get("daily_rows") or []]),
        ("每周", [f"{key}：{value}" for key, value in view.get("weekly_rows") or []]),
        ("赛季", [f"{key}：{value}" for key, value in view.get("season_rows") or []]),
    ]
    inputs = "｜".join(f"{key} {value}" for key, value in view.get("input_chips") or [])
    return _truncate(
        _card(
            "STALZONE · 通行证计算",
            lines,
            [("输入参数", [inputs]), *groups],
            str(view.get("footer") or ""),
        )
    )

def format_balance_history(
    label: str,
    result: dict[str, Any] | None,
) -> str:
    result = result if isinstance(result, dict) else {}
    rows = result.get("rows") or []
    patches = result.get("patches") or []
    footer = "数据源：官方 Steam Patch Notes / 公告（2023-2026）｜箭头为旧→新"
    if not rows and not patches:
        return _card(
            "STALZONE · 平衡调整",
            [f"{label}｜EU / 全球服"],
            [("查询结果", ["没有找到该物品的平衡调整记录。", "已检索 2023-2026 官方 Patch Notes。"])],
            footer,
        )
    sections: list[tuple[str, list[str]]] = []
    if rows:
        row_lines: list[str] = []
        for row in rows:
            row_lines.append(f"{row.get('label')}：{row.get('changes')}")
        sections.append(("长期调整索引（中文整理）", row_lines))
    if patches:
        patch_lines: list[str] = []
        for patch in patches:
            title = _clean_patch_title(str(patch.get("title") or ""))
            patch_lines.append(f"◆ {patch.get('date')}｜{title}")
            seen: set[str] = set()
            changes = [
                part
                for raw in patch.get("changes", [])
                for part in re.split(r"[；。]", str(raw))
                if part.strip()
            ]
            for raw in changes:
                change = _balance_change_text(raw)
                key = _balance_dedupe_key(change)
                if not key or key in seen:
                    continue
                seen.add(key)
                patch_lines.append(f"  {change}")
        sections.append(("官方补丁逐条记录（新→旧）", patch_lines))
    return _card(
        "STALZONE · 平衡调整",
        [f"{label}｜EU / 全球服"],
        sections,
        footer,
        limit=16000,
    )


def format_clan(clan: dict[str, Any], region: str) -> str:
    if not isinstance(clan, dict) or not clan.get("id"):
        return "未找到相关数据，请检查战队名/标签/ID 是否正确。"
    name = str(clan.get("name") or "未知战队")
    tag = clan.get("tag")
    label = f"{name} [{tag}]" if tag else name
    alliance_raw = str(clan.get("alliance") or "")
    alliance = ALLIANCE_LABELS.get(alliance_raw.lower(), alliance_raw or "未知")
    overview = [
        f"等级：{clan.get('level', '未知')}｜积分：{clan.get('levelPoints', '未知')}",
        f"阵营：{alliance}｜成员：{clan.get('memberCount', '未知')}",
        f"队长：{clan.get('leader') or '未知'}",
        f"成立：{_fmt_dt(clan.get('registrationTime'), with_year=True)}",
    ]
    sections = [("概况", overview)]
    description = str(clan.get("description") or "").strip()
    if description:
        sections.append(("简介", [description[:300]]))
    sections.append(("标识", [f"ID：{clan.get('id')}"]))
    return _card(
        "STALZONE · 战队",
        [f"{label}｜{region.upper()}"],
        sections,
        "成员列表需要 User token，本插件不提供｜数据来自官方 API",
    )


def format_clan_candidates(query: str, clans: list[dict[str, Any]]) -> str:
    if not clans:
        return "未找到相关数据，请检查战队名/标签/ID 是否正确。"
    if len(clans) == 1:
        return _clan_line(clans[0])
    rows = []
    for index, clan in enumerate(clans, 1):
        rows.append(f"{index}. {_clan_line(clan)}")
        rows.append(f"   ID {clan.get('id')}")
    return _card(
        "STALZONE · 战队候选",
        [
            f"找到 {len(clans)} 个战队，请用更精确的名称/标签或 ID",
            "回复 sz 候选 <序号> 可直接查看该战队",
        ],
        [("候选", rows)],
        "例如：sz 候选 1｜也可用完整名称、标签或 UUID",
        limit=12000,
    )


def format_clans_list(payload: dict[str, Any] | None, page: int) -> str:
    payload = payload if isinstance(payload, dict) else {}
    raw = payload.get("data")
    clans = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
    total = _safe_int(payload.get("totalClans"))
    if not clans:
        return "未找到相关数据，请检查页码或区服。"
    rows = []
    for index, clan in enumerate(clans, 1):
        rows.append(f"{(page - 1) * 10 + index}. {_clan_line(clan)}")
    return _card(
        "STALZONE · 战队列表",
        [f"第 {page} 页" + (f"｜共 {total} 个" if total is not None else "")],
        [("战队", rows)],
        "查看详情：/sz clan <战队名/标签/ID>",
    )


def format_regions(regions: list[dict[str, Any]] | None) -> str:
    if not regions:
        return "未找到区服数据。"
    rows = []
    for region in regions:
        if isinstance(region, dict):
            rows.append(f"{region.get('id', '?')} — {region.get('name', '')}")
    return _card(
        "STALZONE · 区服列表",
        ["插件当前区服以配置 region 为准"],
        [("官方区服", rows)],
        "数据来自官方 API",
    )


def _diag_bytes(value: Any) -> str:
    try:
        size = float(value or 0)
    except (TypeError, ValueError):
        size = 0.0
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"


def _diag_uptime(value: Any) -> str:
    try:
        seconds = max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        seconds = 0
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    if days:
        return f"{days}天 {hours:02d}小时 {minutes:02d}分"
    return f"{hours:02d}小时 {minutes:02d}分 {secs:02d}秒"


def build_diag_view(
    info: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the detailed diagnostic model shared by text and image output."""
    info = info if isinstance(info, dict) else {}
    cache_entries = int(info.get("cache_entries") or 0)
    hits = int(info.get("cache_hits") or 0)
    misses = int(info.get("cache_misses") or 0)
    total = hits + misses
    hit_rate = f"{hits * 100 / total:.0f}%" if total else "无请求"
    stamp = (now or datetime.now(CST)).strftime("%Y-%m-%d %H:%M")
    version = str(info.get("version") or "?")
    system = str(info.get("system") or "?")
    release = str(info.get("release") or "")
    machine = str(info.get("machine") or "?")
    python = str(info.get("python") or "?")
    implementation = str(info.get("implementation") or "Python")
    region = str(info.get("region") or "?").upper()
    api_base = str(info.get("api_base") or "?")
    env = str(info.get("env") or "?")
    render_mode = str(info.get("render_mode") or "?")
    credentials = str(info.get("credentials") or "未配置")
    font = str(info.get("font") or "未找到")
    font_ready = bool(info.get("font_ready"))
    pillow = str(info.get("pillow") or "未安装")
    items = int(info.get("items") or 0)
    details = int(info.get("details") or 0)
    categories = int(info.get("categories") or 0)
    aliases = int(info.get("aliases") or 0)
    balance_patches = int(info.get("balance_patches") or 0)
    balance_weapons = int(info.get("balance_weapons") or 0)
    balance_generated = str(info.get("balance_generated") or "—")
    pending = int(info.get("pending") or 0)
    sc_keys = int(info.get("sc_keys") or 0)
    cooldown_scopes = int(info.get("cooldown_scopes") or 0)
    data_dir_ok = bool(info.get("data_dir_ok"))
    http = str(info.get("http") or "未建立")
    uptime = _diag_uptime(info.get("uptime_seconds"))

    def yes_no(value: Any) -> str:
        if value is True:
            return "开启"
        if value is False:
            return "关闭"
        return "—"

    runtime_rows = [
        ("Python", f"{python} · {implementation}"),
        ("操作系统", f"{system} {release}".strip()),
        ("架构", machine),
        ("运行时间", uptime),
        ("进程 PID", str(info.get("pid") or "—")),
        ("时区", str(info.get("timezone") or "UTC+8")),
        ("渲染模式", render_mode),
    ]
    api_rows = [
        ("区服", region),
        ("API 地址", api_base),
        ("环境", env),
        ("凭证", credentials),
        ("HTTP 连接池", http),
        ("并发 / 超时", f"{info.get('concurrency', 6)} / {info.get('timeout', 10)}s"),
        ("重试", f"{info.get('retries', 2)} 次 · {info.get('retry_base', 0.5)}s"),
        ("Lunar 补充", yes_no(info.get("lunar_enrich"))),
        ("SC CORE 兜底", yes_no(info.get("sc_core_fallback"))),
        ("群冷却", f"{info.get('cooldown', 1.0)}s"),
    ]
    data_rows = [
        ("物品索引", f"{items:,} 件"),
        ("物品详情", f"{details:,} 件"),
        ("分类", f"{categories:,} 类"),
        ("别名", f"{aliases:,} 条"),
        ("平衡武器", f"{balance_weapons:,} 条"),
        ("平衡公告", f"{balance_patches:,} 份"),
        ("公告生成", balance_generated),
        ("离线图标", f"{int(info.get('item_icon_files') or 0):,} 个 · {_diag_bytes(info.get('item_icon_bytes'))}"),
        ("阵营图标", f"{int(info.get('faction_icons') or 0)} 个"),
    ]
    cache_rows = [
        ("API 缓存", f"{cache_entries:,} / {int(info.get('cache_limit') or 128):,} 条"),
        ("命中 / 未命中", f"{hits:,} / {misses:,}"),
        ("缓存命中率", hit_rate),
        ("待选会话", f"{pending:,} / {int(info.get('pending_limit') or 200):,} · TTL {int(info.get('pending_ttl') or 600)}s"),
        ("SC 物品键", f"{sc_keys:,} / {int(info.get('sc_limit') or 4096):,}"),
        ("冷却会话", f"{cooldown_scopes:,} / {int(info.get('cooldown_limit') or 500):,}"),
    ]
    storage_rows = [
        ("数据目录", "可写" if data_dir_ok else "不可写"),
        ("帮助图缓存", f"{int(info.get('help_files') or 0):,} 个 · {_diag_bytes(info.get('help_bytes'))}"),
        ("图标下载缓存", f"{int(info.get('icon_files') or 0):,} 个 · {_diag_bytes(info.get('icon_bytes'))}"),
        ("临时卡片", f"{int(info.get('temp_files') or 0):,} 个 · {_diag_bytes(info.get('temp_bytes'))}"),
        ("CJK 字体", font if font_ready else f"{font}（不可用）"),
        ("Pillow", pillow),
    ]

    health = [
        ("凭证", "ok" if credentials == "已配置" else "warn", credentials),
        ("物品索引", "ok" if items else "bad", f"{items:,} 件"),
        ("平衡库", "ok" if balance_patches or balance_weapons else "bad", f"{balance_patches:,} 份"),
        ("CJK 字体", "ok" if font_ready else "bad", font),
        ("Pillow", "ok" if pillow != "未安装" else "bad", pillow),
        ("数据目录", "ok" if data_dir_ok else "bad", "可写" if data_dir_ok else "不可写"),
    ]
    summary_lines = [
        f"核心数据：物品 {items:,} 件 / 详情 {details:,} 件 / 图标 {int(info.get('item_icon_files') or 0):,} 个",
        f"凭证：{credentials}｜HTTP 连接池：{http}",
        f"字体：{font if font_ready else '不可用'}｜Pillow：{pillow}",
    ]
    if credentials != "已配置":
        summary_lines.append("配置 Client-Id / Client-Secret 后可执行实时查询。")
    critical_bad = any(
        state == "bad" for label, state, _ in health if label != "凭证"
    )
    if critical_bad:
        status, status_key = "需要检查", "bad"
    elif credentials != "已配置":
        status, status_key = "待配置凭证", "warn"
    else:
        status, status_key = "运行正常", "ok"

    groups = [
        {"title": "运行环境", "subtitle": "RUNTIME", "column": 0, "rows": runtime_rows},
        {"title": "API 与配置", "subtitle": "API & CONFIG", "column": 0, "rows": api_rows},
        {"title": "数据资产", "subtitle": "DATA", "column": 1, "rows": data_rows},
        {"title": "缓存与队列", "subtitle": "CACHE", "column": 1, "rows": cache_rows},
        {"title": "存储与渲染", "subtitle": "STORAGE", "column": 1, "rows": storage_rows},
    ]
    return {
        "version": version,
        "system": system,
        "release": release,
        "machine": machine,
        "python": python,
        "implementation": implementation,
        "region": region,
        "api_base": api_base,
        "env": env,
        "render_mode": render_mode,
        "credentials": credentials,
        "font": font,
        "font_ready": font_ready,
        "pillow": pillow,
        "items": items,
        "details": details,
        "categories": categories,
        "aliases": aliases,
        "balance_patches": balance_patches,
        "balance_weapons": balance_weapons,
        "pending": pending,
        "cache_entries": cache_entries,
        "cache_hits": hits,
        "cache_misses": misses,
        "hit_rate": hit_rate,
        "now": stamp,
        "status": status,
        "status_key": status_key,
        "health": health,
        "metrics": [
            {"label": "物品索引", "value": f"{items:,}", "unit": "件"},
            {"label": "物品详情", "value": f"{details:,}", "unit": "件"},
            {"label": "平衡公告", "value": f"{balance_patches:,}", "unit": "份"},
            {"label": "缓存命中率", "value": hit_rate, "unit": ""},
        ],
        "groups": groups,
        "uptime": uptime,
        "summary_lines": summary_lines,
        "footer_note": "凭证只显示配置状态，不读取或输出 Client-Secret；诊断不包含玩家账号或聊天内容。",
    }


def format_diag(
    info: dict[str, Any],
    *,
    view: dict[str, Any] | None = None,
) -> str:
    """Render a copyable fallback card with all diagnostic sections."""
    view = view if isinstance(view, dict) and view else build_diag_view(info)
    sections = [
        (
            str(group.get("title") or ""),
            [f"{key}：{value}" for key, value in group.get("rows") or []],
        )
        for group in view.get("groups") or []
    ]
    return _card(
        "STALZONE · 运行诊断",
        [
            f"插件 {view.get('version', '?')}｜{view.get('system', '?')}",
            f"状态：{view.get('status', '?')}｜{view.get('region', '?')}｜{view.get('now', '?')} UTC+8",
        ],
        sections,
        str(view.get("footer_note") or "诊断不包含凭证或玩家数据"),
    )


def format_operations(payload: dict[str, Any] | None, map_name: str | None = None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    raw = payload.get("sessions")
    sessions = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
    total = _safe_int(payload.get("total"))
    if not sessions:
        return "未找到相关数据，请检查地图 ID 或区服。"
    rows = []
    for index, session in enumerate(sessions[:10], 1):
        participants = session.get("participants")
        count = len(participants) if isinstance(participants, list) else 0
        rows.append(
            f"{index}. {session.get('map', '未知地图')}｜难度 {session.get('difficulty', '?')}"
        )
        rows.append(
            f"   {_fmt_duration(session.get('sessionDurationSeconds'))}｜{count} 人"
            f"｜结束 {_fmt_dt(session.get('endTime'), with_year=True)}"
        )
    subtitle = map_name or "全部地图"
    if total is not None:
        subtitle += f"｜共 {total} 场"
    return _card(
        "STALZONE · 行动记录",
        [subtitle],
        [("最近场次", rows)],
        "数据来自官方 API",
    )


def format_help(region: str, *, demo: bool = False) -> str:
    env = "演示环境（假数据）" if demo else "生产环境"
    commands = [
        "/sz auction / 拍卖行 <物品> [品质] [日期] [数量] — 查看在售、成交与成交历史；日期如 6.11、25.6.11",
        "/sz emission / 风暴 [EU/RU/NA/SEA/NEA] — 查看上次风暴时间与当前状态，可指定区服",
        "/sz player / 玩家 <角色名/UUID> [EU/RU/NA/SEA/NEA] — 查看角色资料、战队与区服",
        "/sz item / 物品 <中文名/英文名/ID> — 查看物品属性、描述和 ID",
        "/sz 候选 <序号> — 使用最近一次候选继续查询",
        "/sz 调整 / 平衡 <武器/神器> — 查看 2023-2026 官方平衡调整记录",
        "/sz 通行证计算 <等级> <每日任务>[+超载] <剩余天数> [每周天数] — 计算通行证经验与等级预测",
        "/sz clan / 战队 <战队名/标签/ID> [EU/RU/NA/SEA/NEA] — 查看战队资料",
        "/sz clans [页码] — 战队列表",
        "/sz operations [地图ID] — 最近行动记录",
        "/sz regions — 官方区服列表",
        "/sz diag / 状态 — 查看运行环境、数据、缓存与存储状态（不包含凭证）",
        "/sz help — 显示本帮助",
    ]
    return _card(
        "STALZONE · 查询帮助",
        [f"当前区服：{region.upper()}｜{env}"],
        [("指令", commands)],
        "斜杠可省略，但 sz 后需加空格｜时间均为 UTC+8｜玩家/战队/风暴可指定区服（如 sz 玩家 aaa ru）｜填日期只查该日及之前的成交｜拍卖数量需同时有品质和日期｜角色战报可含 Lunar 第三方补充｜需要 User token 的接口不提供",
    )
