"""Indicadores del Factor X7 y pivotes, sin dependencias externas."""

from __future__ import annotations


def sma(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return out
    window = sum(values[:length])
    out[length - 1] = window / length
    for index in range(length, len(values)):
        window += values[index] - values[index - length]
        out[index] = window / length
    return out


def rsi(close: list[float], period: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(close)
    if len(close) <= period:
        return result
    gains = []
    losses = []
    for index in range(1, len(close)):
        delta = close[index] - close[index - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = _rsi_value(avg_gain, avg_loss)
    for offset, (gain, loss) in enumerate(zip(gains[period:], losses[period:]), start=period):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        result[offset + 1] = _rsi_value(avg_gain, avg_loss)
    return result


def atr(high: list[float], low: list[float], close: list[float], period: int = 14) -> list[float | None]:
    """ATR de Wilder, el mismo largo que el estudio ATR(14) de la plantilla."""
    result: list[float | None] = [None] * len(close)
    if len(close) <= period:
        return result
    true_ranges = []
    for index in range(1, len(close)):
        true_ranges.append(max(
            high[index] - low[index],
            abs(high[index] - close[index - 1]),
            abs(low[index] - close[index - 1]),
        ))
    value = sum(true_ranges[:period]) / period
    result[period] = value
    for offset, true_range in enumerate(true_ranges[period:], start=period):
        value = ((value * (period - 1)) + true_range) / period
        result[offset + 1] = value
    return result


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def trend_aligned(close: list[float], days: int, bullish: bool) -> bool:
    if len(close) < days + 6:
        return False
    average = sma(close, days)
    ma_now = average[-1]
    ma_prev = average[-6]
    if ma_now is None or ma_prev is None:
        return False
    latest = close[-1]
    if bullish:
        return latest > ma_now and ma_now > ma_prev
    return latest < ma_now and ma_now < ma_prev


def cross_age(
    fast: list[float | None],
    slow: list[float | None],
    direction: int,
    max_age: int,
) -> int | None:
    if len(fast) < max_age + 2 or len(slow) < max_age + 2:
        return None
    for age in range(max_age + 1):
        index = len(fast) - 1 - age
        previous = index - 1
        if previous < 0:
            return None
        values = (fast[index], slow[index], fast[previous], slow[previous])
        if any(value is None for value in values):
            continue
        fast_now, slow_now, fast_prev, slow_prev = values
        crossed_up = fast_now > slow_now and fast_prev <= slow_prev
        crossed_down = fast_now < slow_now and fast_prev >= slow_prev
        if direction == 1 and crossed_up:
            return age
        if direction == -1 and crossed_down:
            return age
    return None


def still_ordered(fast: list[float | None], slow: list[float | None], direction: int) -> bool:
    if not fast or fast[-1] is None or slow[-1] is None:
        return False
    if direction == 1:
        return fast[-1] > slow[-1]
    return fast[-1] < slow[-1]


def floor_pivots(high: float, low: float, close: float) -> dict[str, float]:
    pivot = (high + low + close) / 3
    span = high - low
    return {
        "P": pivot,
        "R1": (2 * pivot) - low,
        "R2": pivot + span,
        "S1": (2 * pivot) - high,
        "S2": pivot - span,
    }


def eps_growth(current: float, previous: float) -> float | None:
    """Misma fórmula de la hoja: (actual - anterior) / anterior."""
    if previous == 0:
        return None
    return (current - previous) / previous
