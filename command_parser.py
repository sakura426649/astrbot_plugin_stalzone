"""Command parsing helpers kept separate from AstrBot for easy testing."""

from __future__ import annotations

import re

COMMAND_PREFIX_RE = re.compile(r"^[/!！.#]+\s*")
COMMAND_NAME_RE = re.compile(r"^(?:sz|stalzone)(?:@\S+)?(?:\s+|$)", re.IGNORECASE)

ALIASES = {
    "help": "help",
    "帮助": "help",
    "?": "help",
    "auction": "auction",
    "ah": "auction",
    "market": "auction",
    "市场": "auction",
    "拍卖": "auction",
    "拍卖行": "auction",
    "交易": "auction",
    "交易场": "auction",
    "交易行": "auction",
    "emission": "emission",
    "em": "emission",
    "fb": "emission",
    "风暴": "emission",
    "爆发": "emission",
    "辐射": "emission",
    "player": "player",
    "profile": "player",
    "p": "player",
    "资料": "player",
    "角色": "player",
    "玩家": "player",
    "clan": "clan",
    "战队": "clan",
    "clans": "clans",
    "战队列表": "clans",
    "item": "item",
    "物品": "item",
    "balance": "balance",
    "changes": "balance",
    "adjust": "balance",
    "调整": "balance",
    "调整历史": "balance",
    "改动": "balance",
    "平衡": "balance",
    "平衡历史": "balance",
    "pass": "pass",
    "seasonpass": "pass",
    "season_pass": "pass",
    "通行证": "pass",
    "赛季通行证": "pass",
    "通行证计算": "pass",
    "通行证计算器": "pass",
    "通行证等级计算": "pass",
    "通行证等级预测": "pass",
    "通行证预测": "pass",
    "regions": "regions",
    "region": "regions",
    "区服": "regions",
    "operations": "operations",
    "ops": "operations",
    "行动": "operations",
    "行动记录": "operations",
    "diag": "diag",
    "diagnostic": "diag",
    "诊断": "diag",
    "状态": "diag",
    "运行状态": "diag",
    "candidate": "candidate",
    "候选": "candidate",
    "update": "update",
    "upgrade": "update",
    "更新": "update",
    "升级": "update",
    "插件更新": "update",
    "更新插件": "update",
    "插件升级": "update",
    "version": "check_version",
    "check": "check_version",
    "check_version": "check_version",
    "版本": "check_version",
    "检查版本": "check_version",
    "检查更新": "check_version",
    "风暴订阅": "emission_subscribe",
    "订阅风暴": "emission_subscribe",
    "风暴提醒": "alert",
    "区服切换": "set_region",
    "默认区服": "set_region",
    "拍卖显示模式": "auction_mode",
    "显示模式": "auction_mode",
}


def parse_command(message: str | None) -> tuple[str, str]:
    """Return ``(subcommand, argument)`` from a raw QQ message.

    Handles both possible AstrBot behaviours: the message may include the
    command name (``/sz auction y1q9``) or only the arguments (``auction y1q9``).
    """
    text = (message or "").strip()
    text = COMMAND_PREFIX_RE.sub("", text)
    text = COMMAND_NAME_RE.sub("", text).strip()
    if not text:
        return "", ""
    parts = text.split(maxsplit=1)
    sub = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return ALIASES.get(sub, sub), arg
