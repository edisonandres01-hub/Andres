"""Técnica GAP de SPY, con las fórmulas de la hoja del Power Pack.

El trade deshace el hueco: si hoy abre por encima del cierre de ayer se
busca el corto; si abre por debajo, el largo. El objetivo es el cierre de
ayer. El stop es el 30% del rango de ayer (high - low), que es lo que
calcula la celda aunque el rótulo diga 35%.

Los dos filtros tienen que cumplirse:
1. Probabilidad ponderada mayor a 70%.
2. El hueco mide entre 20% y 40% del rango de ayer.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

# Probabilidades históricas de la hoja, separadas en largo y corto.
# Clave: número de día. Valor: (largo, corto).
WEEKDAY_PROB = {
    1: (0.695, 0.719),
    2: (0.739, 0.714),
    3: (0.719, 0.749),
    4: (0.743, 0.711),
    5: (0.676, 0.707),
}
MONTH_PROB = {
    1: (0.714, 0.750),
    2: (0.759, 0.790),
    3: (0.740, 0.710),
    4: (0.723, 0.763),
    5: (0.662, 0.731),
    6: (0.790, 0.730),
    7: (0.710, 0.790),
    8: (0.687, 0.767),
    9: (0.631, 0.649),
    10: (0.813, 0.734),
    11: (0.780, 0.760),
    12: (0.729, 0.714),
}
DAY_PROB = {
    1: (0.735, 0.452),
    2: (0.765, 0.750),
    3: (0.698, 0.659),
    4: (0.658, 0.767),
    5: (0.667, 0.459),
    6: (0.681, 0.735),
    7: (0.795, 0.762),
    8: (0.837, 0.786),
    9: (0.657, 0.867),
    10: (0.721, 0.762),
    11: (0.780, 0.641),
    12: (0.738, 0.732),
    13: (0.805, 0.643),
    14: (0.706, 0.755),
    15: (0.649, 0.667),
    16: (0.667, 0.617),
    17: (0.674, 0.684),
    18: (0.794, 0.646),
    19: (0.583, 0.792),
    20: (0.605, 0.821),
    21: (0.763, 0.886),
    22: (0.696, 0.703),
    23: (0.692, 0.762),
    24: (0.765, 0.717),
    25: (0.813, 0.651),
    26: (0.742, 0.745),
    27: (0.641, 0.738),
    28: (0.676, 0.681),
    29: (0.750, 0.738),
    30: (0.667, 0.756),
    31: (0.706, 0.774),
}

ZONE_WEIGHT = 0.70
WEEKDAY_WEIGHT = 0.15
MONTH_WEIGHT = 0.05
DAY_WEIGHT = 0.10


def zone_probability(
    prev_open: float,
    prev_high: float,
    prev_low: float,
    prev_close: float,
    today_open: float,
) -> float:
    """Probabilidad de la zona del hueco según dónde abre hoy respecto a ayer."""
    yesterday_bearish = prev_close <= prev_open
    opened = today_open
    if yesterday_bearish:
        # De arriba hacia abajo: high, open, close, low.
        if opened > prev_high:
            return 0.59
        if opened > prev_open:
            return 0.66
        if opened > prev_close:
            return 0.75
        if opened > prev_low:
            return 0.78
        return 0.65
    if opened > prev_high:
        return 0.71
    if opened > prev_close:
        return 0.82
    if opened > prev_open:
        return 0.75
    if opened > prev_low:
        return 0.72
    return 0.54


@dataclass
class GapPlan:
    session: dt.date
    side: str
    entry: float
    target: float
    stop: float
    shares: int
    probability: float
    zone_probability: float
    gap_to_range: float
    probability_ok: bool
    size_ok: bool
    tradable: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "fecha": self.session.isoformat(),
            "lado": self.side,
            "entrada": round(self.entry, 4),
            "objetivo": round(self.target, 4),
            "stop": round(self.stop, 4),
            "acciones": self.shares,
            "probabilidad": round(self.probability, 4),
            "probabilidad_zona": round(self.zone_probability, 4),
            "hueco_sobre_rango": round(self.gap_to_range, 4),
            "criterio_probabilidad": self.probability_ok,
            "criterio_tamano": self.size_ok,
            "operable": self.tradable,
            "motivo": self.reason,
        }


def evaluate_gap(
    prev_open: float,
    prev_high: float,
    prev_low: float,
    prev_close: float,
    today_open: float,
    session: dt.date,
    portfolio_usd: float,
    budget_usd: float | None = None,
    max_position_fraction: float = 0.30,
    max_loss_fraction: float = 0.02,
    min_probability: float = 0.70,
    gap_range_min: float = 0.20,
    gap_range_max: float = 0.40,
    stop_range_fraction: float = 0.30,
) -> GapPlan:
    yesterday_range = prev_high - prev_low
    gap_points = abs(today_open - prev_close)
    gap_to_range = gap_points / yesterday_range if yesterday_range > 0 else math.inf
    # Hueco hacia arriba se opera en corto; hueco hacia abajo, en largo.
    side = "short" if today_open > prev_close else "long"
    zone = zone_probability(prev_open, prev_high, prev_low, prev_close, today_open)
    column = 0 if side == "long" else 1
    weekday = session.weekday() + 1
    weekday_prob = WEEKDAY_PROB.get(weekday, (0.0, 0.0))[column] if weekday <= 5 else 0.0
    month_prob = MONTH_PROB[session.month][column]
    day_prob = DAY_PROB[session.day][column]
    probability = (
        zone * ZONE_WEIGHT
        + weekday_prob * WEEKDAY_WEIGHT
        + month_prob * MONTH_WEIGHT
        + day_prob * DAY_WEIGHT
    )
    probability_ok = probability > min_probability
    size_ok = gap_range_min < gap_to_range < gap_range_max
    stop_distance = yesterday_range * stop_range_fraction
    if side == "long":
        stop = today_open - stop_distance
    else:
        stop = today_open + stop_distance
    budget = budget_usd if budget_usd is not None else portfolio_usd * max_position_fraction
    max_loss = portfolio_usd * max_loss_fraction
    if today_open <= 0 or stop_distance <= 0 or budget <= 0:
        shares = 0
    else:
        shares = min(
            math.floor(budget / today_open),
            math.floor(max_loss / stop_distance),
        )
        shares = max(0, shares)
    tradable = probability_ok and size_ok and shares > 0
    if tradable:
        reason = "Los dos criterios del GAP se cumplen."
    elif not probability_ok and not size_ok:
        reason = "La probabilidad no supera 70% y el hueco queda fuera del 20% al 40% del rango de ayer."
    elif not probability_ok:
        reason = "La probabilidad ponderada no supera 70%."
    elif not size_ok:
        reason = "El hueco no está entre 20% y 40% del rango de ayer."
    else:
        reason = "El tamaño de la posición queda en cero con este capital."
    return GapPlan(
        session=session,
        side=side,
        entry=today_open,
        target=prev_close,
        stop=stop,
        shares=shares,
        probability=probability,
        zone_probability=zone,
        gap_to_range=gap_to_range,
        probability_ok=probability_ok,
        size_ok=size_ok,
        tradable=tradable,
        reason=reason,
    )
