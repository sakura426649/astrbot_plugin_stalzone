"""Season pass XP calculator.

Rules (EU/global, 2026):
- 1,000 XP = 1 level.
- Daily tasks: first 7 at 500, tasks 8-15 at 250, tasks 16-45 at 75,
  tasks 46+ at 25. The scale resets every day at 12:00 UTC+8.
- Overload: 250 XP for each of the first 15 daily tasks; extra overloads
  beyond the number of completed tasks or 15 are wasted.
- Weekly rewards: 15 tasks = 3,000 XP; 45 tasks = 8,000 XP cumulative;
  100 tasks = 20,000 XP cumulative. Week resets Wednesday 12:00 UTC+8.
"""

from __future__ import annotations

from dataclasses import dataclass


class SeasonPassError(ValueError):
    """Invalid calculator input."""


def daily_task_xp(tasks: int) -> int:
    tasks = max(0, int(tasks))
    xp = min(tasks, 7) * 500
    xp += max(0, min(tasks, 15) - 7) * 250
    xp += max(0, min(tasks, 45) - 15) * 75
    xp += max(0, tasks - 45) * 25
    return xp


def weekly_reward(tasks: int) -> int:
    tasks = max(0, int(tasks))
    if tasks >= 100:
        return 20_000
    if tasks >= 45:
        return 8_000
    if tasks >= 15:
        return 3_000
    return 0


@dataclass(frozen=True)
class SeasonPassResult:
    level: int
    daily_tasks: int
    overloads: int
    remaining_days: int
    weekly_days: int
    effective_overloads: int
    daily_base_xp: int
    daily_overload_xp: int
    daily_total_xp: int
    weekly_tasks: int
    weekly_reward_xp: int
    weekly_xp: int
    weekly_overload_xp: int
    weekly_total_xp: int
    full_weeks: int
    remainder_days: int
    active_days: int
    overloads_used: int
    season_base_xp: int
    season_overload_xp: int
    season_total_xp: int
    final_level_without_overload: int
    final_level_with_overload: int


def calculate(
    level: int,
    daily_tasks: int,
    overloads: int,
    remaining_days: int,
    weekly_days: int = 7,
) -> SeasonPassResult:
    level = int(level)
    daily_tasks = int(daily_tasks)
    overloads = int(overloads)
    remaining_days = int(remaining_days)
    weekly_days = int(weekly_days)
    if level < 0:
        raise SeasonPassError("当前等级不能小于 0。")
    if daily_tasks < 0:
        raise SeasonPassError("每日任务数不能小于 0。")
    if overloads < 0:
        raise SeasonPassError("超载数量不能小于 0。")
    if remaining_days < 0:
        raise SeasonPassError("剩余赛季天数不能小于 0。")
    if not 1 <= weekly_days <= 7:
        raise SeasonPassError("每周计划天数请填 1–7。")

    effective_overloads = (
        min(overloads, daily_tasks, 15) if daily_tasks > 0 else 0
    )
    daily_base = daily_task_xp(daily_tasks)
    daily_overload = effective_overloads * 250
    daily_total = daily_base + daily_overload

    weekly_tasks = daily_tasks * weekly_days
    weekly_bonus = weekly_reward(weekly_tasks)
    weekly_base = daily_base * weekly_days + weekly_bonus
    weekly_over = daily_overload * weekly_days
    weekly_total = weekly_base + weekly_over

    full_weeks, remainder = divmod(remaining_days, 7)
    partial_days = min(weekly_days, remainder)
    active_days = full_weeks * weekly_days + partial_days
    partial_tasks = daily_tasks * partial_days
    season_base = (
        daily_base * active_days
        + full_weeks * weekly_bonus
        + weekly_reward(partial_tasks)
    )
    season_overload = daily_overload * active_days
    season_total = season_base + season_overload

    return SeasonPassResult(
        level=level,
        daily_tasks=daily_tasks,
        overloads=overloads,
        remaining_days=remaining_days,
        weekly_days=weekly_days,
        effective_overloads=effective_overloads,
        daily_base_xp=daily_base,
        daily_overload_xp=daily_overload,
        daily_total_xp=daily_total,
        weekly_tasks=weekly_tasks,
        weekly_reward_xp=weekly_bonus,
        weekly_xp=weekly_base,
        weekly_overload_xp=weekly_over,
        weekly_total_xp=weekly_total,
        full_weeks=full_weeks,
        remainder_days=remainder,
        active_days=active_days,
        overloads_used=effective_overloads * active_days,
        season_base_xp=season_base,
        season_overload_xp=season_overload,
        season_total_xp=season_total,
        final_level_without_overload=level + season_base // 1000,
        final_level_with_overload=level + season_total // 1000,
    )


def parse_arguments(argument: str) -> tuple[int, int, int, int, int]:
    """Parse the flexible season-pass argument forms.

    Three values: level, daily tasks, remaining days (no overload).
    Four values without ``+``: level, daily tasks, overloads, remaining days.
    Four values with ``+``: level, daily+overload, remaining days, weekly days.
    Five values: level, daily tasks, overloads, remaining days, weekly days.
    """
    parts = str(argument or "").split()
    if len(parts) not in (3, 4, 5):
        raise SeasonPassError(
            "用法：/sz 通行证计算 <等级> <每日任务>[+超载] <剩余天数> [每周天数=7]\n"
            "也可：/sz 通行证计算 <等级> <每日任务> <超载> <剩余天数> [每周天数]"
        )
    plus_form = "+" in parts[1]
    if len(parts) == 5 and plus_form:
        raise SeasonPassError(
            "五参数格式不要再给每日任务加“+”，直接写：等级 每日任务 超载 剩余天数 每周天数"
        )
    try:
        level = int(parts[0])
        daily_parts = parts[1].split("+")
        if len(daily_parts) not in (1, 2) or not daily_parts[0]:
            raise ValueError
        daily_tasks = int(daily_parts[0])
        inline_overload = int(daily_parts[1]) if len(daily_parts) == 2 else None

        if len(parts) == 3:
            overloads = inline_overload or 0
            remaining_days = int(parts[2])
            weekly_days = 7
        elif len(parts) == 4 and plus_form:
            overloads = inline_overload or 0
            remaining_days = int(parts[2])
            weekly_days = int(parts[3])
        elif len(parts) == 4:
            overloads = int(parts[2])
            remaining_days = int(parts[3])
            weekly_days = 7
        else:
            overloads = int(parts[2])
            remaining_days = int(parts[3])
            weekly_days = int(parts[4])
    except ValueError as exc:
        raise SeasonPassError(
            "参数格式错误。示例：/sz 通行证计算 15 15+2 20 7\n"
            "或：/sz 通行证计算 15 15 2 20 7"
        ) from exc
    return level, daily_tasks, overloads, remaining_days, weekly_days
