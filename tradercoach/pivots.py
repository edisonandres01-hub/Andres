"""Puntos pivote de la lección 18.

Diarios: high, low y close del día anterior.
Semanales: high, low y close de la semana anterior.
El precio por encima de un nivel lo trata como soporte; por debajo, como resistencia.
El stop y el objetivo se apoyan en esos niveles. Si ningún nivel deja
la relación de 2 a 1, el objetivo se alarga hasta esa relación.
"""

from __future__ import annotations

from tradercoach.bars import Bars
from tradercoach.indicators import floor_pivots


def previous_week_hlc(bars: Bars) -> tuple[float, float, float] | None:
    if len(bars) < 2:
        return None
    current = bars.dates[-1].isocalendar()[:2]
    week = None
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    for index in range(len(bars) - 1, -1, -1):
        key = bars.dates[index].isocalendar()[:2]
        if key == current:
            continue
        if week is None:
            week = key
        if key != week:
            break
        highs.append(bars.high[index])
        lows.append(bars.low[index])
        closes.append(bars.close[index])
    if not closes:
        return None
    return max(highs), min(lows), closes[0]


def pivot_map(bars: Bars) -> dict[str, dict[str, float]]:
    daily = floor_pivots(bars.high[-2], bars.low[-2], bars.close[-2])
    week = previous_week_hlc(bars)
    weekly = floor_pivots(*week) if week else {}
    return {"diarios": daily, "semanales": weekly}


def _named(levels: dict[str, dict[str, float]]) -> list[tuple[str, float]]:
    names = []
    for frame, values in (("diario", levels.get("diarios") or {}), ("semanal", levels.get("semanales") or {})):
        for name, value in values.items():
            names.append((f"{name} {frame}", value))
    return names


def locate_stop_target(
    side: str,
    entry: float,
    levels: dict[str, dict[str, float]],
    swing_stop: float,
    min_reward_risk: float,
) -> tuple[float, float | None, float | None, float | None, str | None, str | None]:
    named = _named(levels)
    below = sorted(((name, value) for name, value in named if value < entry), key=lambda item: item[1])
    above = sorted(((name, value) for name, value in named if value > entry), key=lambda item: item[1])
    if side == "long":
        stop_name, stop = below[-1] if below else ("mínimo de las últimas velas", swing_stop)
        if stop >= entry:
            return entry, None, None, None, None, None
        risk = entry - stop
        distance = entry + (min_reward_risk * risk)
        choices = [(name, value) for name, value in above if value + 1e-9 >= distance]
        if choices:
            target_name, target = choices[0]
            reward = (target - entry) / risk
        else:
            target_name, target = "relación 2 a 1", distance
            reward = min_reward_risk
    else:
        stop_name, stop = above[0] if above else ("máximo de las últimas velas", swing_stop)
        if stop <= entry:
            return entry, None, None, None, None, None
        risk = stop - entry
        distance = entry - (min_reward_risk * risk)
        choices = [(name, value) for name, value in below if value <= distance + 1e-9]
        if choices:
            target_name, target = choices[-1]
            reward = (entry - target) / risk
        else:
            target_name, target = "relación 2 a 1", distance
            reward = min_reward_risk
    if reward < min_reward_risk:
        reward = min_reward_risk
    return entry, stop, target, reward, stop_name, target_name
