"""Factor X7 para acciones, con los puntos de chequeo de la lección 14.

Compra (largo), análisis fundamental y técnico:
- EPS del mismo trimestre, año contra año, mayor a 15%.
- EPS anual mayor a 25%.
- Acciones en circulación / volumen promedio de 3 meses, lo más pequeño posible.
- Propiedad institucional mayor a 50% y menor a 90%.
- Productos y líderes: chequeo humano. El bot lo deja pendiente.
- S&P 500 y la acción en tendencia alcista de unos 3 meses.
- La media de 5 cruza por encima de la media de 10, con volumen del día
  de la señal por encima de la media de volumen de 50 barras. Esa media
  es el estudio visible en la plantilla de Interactive Brokers.
- RSI menor a 70. Por debajo de 30 es el caso ideal, no un requisito.
- La señal se toma el día del cruce o como máximo 1 o 2 días después.
- Se cierra en el stop, en el objetivo, o si la media de 10 cruza sobre la de 5.

Venta en corto: el curso dice que no usa análisis fundamental.
- S&P 500 y la acción en tendencia bajista de unos 3 meses.
- La media de 10 cruza por encima de la media de 5, con volumen alto.
- RSI mayor a 30. Por encima de 70 es el caso ideal.
- Se cierra en el stop, en el objetivo, o si la media de 5 cruza sobre la de 10.

El objetivo se coloca para que la relación ganancia/pérdida sea al menos 2 a 1.
El stop y el objetivo se apoyan en los pivotes diarios y semanales. Si ningún
nivel alcanza esa relación, el objetivo se alarga hasta ella. Smart Picks
filtra antes: el largo usa EPS, volumen, beta, instituciones y medias 20/50/200.
El corto usa ese filtro sin EPS y con las medias al revés.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tradercoach.bars import Bars
from tradercoach.ib_chart import ATR_LENGTH, VOLUME_SMA_LENGTH
from tradercoach.indicators import (
    atr,
    cross_age,
    eps_growth,
    rsi,
    sma,
    still_ordered,
    trend_aligned,
)
from tradercoach.pivots import locate_stop_target, pivot_map
from tradercoach.sizing import position_size
from tradercoach.smart_picks import moving_average_stack, screen


@dataclass
class Fundamentals:
    quarterly_eps: list[float] | None = None
    annual_eps: list[float] | None = None
    shares_outstanding: float | None = None
    institutional_ownership: float | None = None
    beta: float | None = None
    leader_confirmed: bool = False


@dataclass
class Check:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict:
        return {"nombre": self.name, "cumple": self.passed, "detalle": self.detail}


@dataclass
class StockPlan:
    symbol: str
    side: str
    tradable: bool
    entry: float
    stop: float | None
    target: float | None
    shares: int
    reward_risk: float | None
    signal_age_days: int | None
    checks: list[Check] = field(default_factory=list)
    pivots: dict = field(default_factory=dict)
    supply_demand_days: float | None = None
    atr: float | None = None
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "simbolo": self.symbol,
            "lado": self.side,
            "operable": self.tradable,
            "entrada": None if self.entry != self.entry else round(self.entry, 4),
            "stop": None if self.stop is None else round(self.stop, 4),
            "objetivo": None if self.target is None else round(self.target, 4),
            "acciones": self.shares,
            "relacion_ganancia_perdida": None if self.reward_risk is None else round(self.reward_risk, 2),
            "edad_senal_dias": self.signal_age_days,
            "oferta_demanda_dias": None if self.supply_demand_days is None else round(self.supply_demand_days, 1),
            "atr_14": None if self.atr is None else round(self.atr, 4),
            "motivo": self.reason,
            "chequeos": [item.as_dict() for item in self.checks],
            "pivotes": _public_pivots(self.pivots),
        }


def _yoy_quarterly_growth(values: list[float] | None) -> float | None:
    if not values or len(values) < 5:
        return None
    return eps_growth(values[0], values[4])


def _annual_growth(values: list[float] | None) -> float | None:
    if not values or len(values) < 2:
        return None
    return eps_growth(values[0], values[1])


def _levels(bars: Bars, side: str, lookback: int, min_reward_risk: float):
    entry = bars.close[-1]
    window_low = min(bars.low[-lookback:])
    window_high = max(bars.high[-lookback:])
    swing = window_low if side == "long" else window_high
    located = locate_stop_target(side, entry, pivot_map(bars), swing, min_reward_risk)
    return located


def _public_pivots(pivots: dict) -> dict:
    def rounded(levels: dict) -> dict:
        return {key: round(value, 4) for key, value in levels.items()}

    return {
        "diarios": rounded(pivots.get("diarios") or {}),
        "semanales": rounded(pivots.get("semanales") or {}),
        "stop": pivots.get("stop_nivel"),
        "objetivo": pivots.get("objetivo_nivel"),
    }


def _with_levels(levels: dict, stop_name: str | None, target_name: str | None) -> dict:
    payload = dict(levels)
    if stop_name:
        payload["stop_nivel"] = stop_name
    if target_name:
        payload["objetivo_nivel"] = target_name
    return payload


def evaluate_stock(
    symbol: str,
    bars: Bars,
    spy: Bars,
    fundamentals: Fundamentals | None = None,
    portfolio_usd: float = 10_000,
    max_position_fraction: float = 0.30,
    max_loss_fraction: float = 0.02,
    min_reward_risk: float = 2.0,
    signal_max_age_days: int = 2,
    trend_days: int = 63,
    rsi_period: int = 14,
    swing_lookback: int = 5,
    max_supply_demand_days: float | None = None,
) -> StockPlan:
    fundamentals = fundamentals or Fundamentals()
    needed = max(trend_days + 6, 20)
    if len(bars) < needed or len(spy) < needed:
        return StockPlan(symbol, "none", False, float("nan"), None, None, 0, None, None, reason="No hay datos suficientes.")

    fast = sma(bars.close, 5)
    slow = sma(bars.close, 10)
    long_age = cross_age(fast, slow, 1, signal_max_age_days)
    short_age = cross_age(fast, slow, -1, signal_max_age_days)
    if long_age is not None and still_ordered(fast, slow, 1):
        side = "long"
        age = long_age
    elif short_age is not None and still_ordered(fast, slow, -1):
        side = "short"
        age = short_age
    else:
        bullish_stack, _ = moving_average_stack(bars.close, True)
        hinted = "long" if bullish_stack else "short"
        return StockPlan(
            symbol,
            "none",
            False,
            bars.close[-1],
            None,
            None,
            0,
            None,
            None,
            checks=_smart_checks(bars, fundamentals, hinted, trend_days),
            pivots=_with_levels(pivot_map(bars), None, None),
            atr=_latest_atr(bars),
            reason="No hay cruce de medias vigente. La señal vale el día del cruce o hasta 2 días después.",
        )

    signal_index = len(bars) - 1 - age
    average_volume = sma(bars.volume, VOLUME_SMA_LENGTH)[signal_index]
    three_month_volume = sma(bars.volume, trend_days)[signal_index]
    signal_volume = bars.volume[signal_index]
    rsi_values = rsi(bars.close, rsi_period)
    rsi_value = rsi_values[signal_index]
    bullish_market = trend_aligned(spy.close, trend_days, True)
    bearish_market = trend_aligned(spy.close, trend_days, False)
    bullish_stock = trend_aligned(bars.close, trend_days, True)
    bearish_stock = trend_aligned(bars.close, trend_days, False)
    levels = pivot_map(bars)
    entry, stop, target, reward, stop_name, target_name = _levels(bars, side, swing_lookback, min_reward_risk)
    pivots = _with_levels(levels, stop_name, target_name)

    checks: list[Check] = []
    supply_days = None
    if side == "long":
        checks.append(Check(
            "Tendencia 3 meses del S&P 500 y de la acción",
            bullish_market and bullish_stock,
            "Alcista en los dos" if bullish_market and bullish_stock else "El mercado o la acción no está alcista en 3 meses",
        ))
        checks.append(Check("Cruce de SMA 5 sobre SMA 10", True, f"El cruce tiene {age} día(s)"))
        volume_ok = average_volume is not None and signal_volume > average_volume
        checks.append(Check(
            "Volumen sobre la media de 50 barras",
            volume_ok,
            _volume_detail(signal_volume, average_volume),
        ))
        checks.append(Check("RSI menor a 70", rsi_value is not None and rsi_value < 70, _rsi_detail(rsi_value, "ideal menor a 30", rsi_value is not None and rsi_value < 30)))
        q_growth = _yoy_quarterly_growth(fundamentals.quarterly_eps)
        a_growth = _annual_growth(fundamentals.annual_eps)
        checks.append(Check(
            "EPS trimestral mayor a 15%",
            q_growth is not None and q_growth > 0.15,
            "Sin datos de EPS" if q_growth is None else f"Crecimiento {q_growth:.1%}",
        ))
        checks.append(Check(
            "EPS anual mayor a 25%",
            a_growth is not None and a_growth > 0.25,
            "Sin datos de EPS" if a_growth is None else f"Crecimiento {a_growth:.1%}",
        ))
        ownership = fundamentals.institutional_ownership
        checks.append(Check(
            "Propiedad institucional entre 50% y 90%",
            ownership is not None and 0.50 < ownership < 0.90,
            "Sin dato" if ownership is None else f"{ownership:.1%}",
        ))
        if fundamentals.shares_outstanding and three_month_volume:
            supply_days = fundamentals.shares_outstanding / three_month_volume
        if max_supply_demand_days is None:
            supply_ok = supply_days is not None
            supply_detail = (
                "Sin dato"
                if supply_days is None
                else f"{supply_days:,.0f} días para rotar las acciones. Más pequeño es mejor; el curso no fija un tope."
            )
        else:
            supply_ok = supply_days is not None and supply_days <= max_supply_demand_days
            supply_detail = "Sin dato" if supply_days is None else f"{supply_days:,.0f} días, tope {max_supply_demand_days:,.0f}"
        checks.append(Check("Oferta contra demanda, ratio pequeño", supply_ok, supply_detail))
        checks.append(Check(
            "Líderes, productos y servicios",
            fundamentals.leader_confirmed,
            "Confirmado por ti" if fundamentals.leader_confirmed else "Pendiente: este punto es cualitativo y lo confirmas tú",
        ))
    else:
        checks.append(Check(
            "Tendencia 3 meses del S&P 500 y de la acción",
            bearish_market and bearish_stock,
            "Bajista en los dos" if bearish_market and bearish_stock else "El mercado o la acción no está bajista en 3 meses",
        ))
        checks.append(Check("Cruce de SMA 10 sobre SMA 5", True, f"El cruce tiene {age} día(s)"))
        volume_ok = average_volume is not None and signal_volume > average_volume
        checks.append(Check(
            "Volumen sobre la media de 50 barras",
            volume_ok,
            _volume_detail(signal_volume, average_volume),
        ))
        checks.append(Check("RSI mayor a 30", rsi_value is not None and rsi_value > 30, _rsi_detail(rsi_value, "ideal mayor a 70", rsi_value is not None and rsi_value > 70)))

    checks.extend(_smart_checks(bars, fundamentals, side, trend_days))
    quantitative = [item for item in checks if item.name != "Líderes, productos y servicios"]
    rules_ok = all(item.passed for item in quantitative)
    leader_pending = any(item.name == "Líderes, productos y servicios" and not item.passed for item in checks)
    shares = 0
    if stop is not None:
        size = position_size(
            portfolio_usd,
            entry,
            abs(entry - stop),
            max_position_fraction,
            max_loss_fraction,
        )
        shares = int(size["shares"])
    tradable = rules_ok and shares > 0 and stop is not None and target is not None
    if tradable:
        reason = "Los chequeos cuantitativos del Factor X7 se cumplen y el tamaño cabe en el 2% de riesgo."
        if leader_pending:
            reason += " Falta tu visto bueno de líderes y productos."
    elif not rules_ok:
        missing = [item.name for item in quantitative if not item.passed]
        reason = "Falta: " + "; ".join(missing)
    elif stop is None:
        reason = "El stop de gráfico no queda del lado correcto del precio."
    else:
        reason = "El tamaño queda en cero: el stop está demasiado lejos para el 2% del portafolio."

    return StockPlan(
        symbol=symbol,
        side=side,
        tradable=tradable,
        entry=entry,
        stop=stop,
        target=target,
        shares=shares,
        reward_risk=reward,
        signal_age_days=age,
        checks=checks,
        pivots=pivots,
        supply_demand_days=supply_days,
        atr=_latest_atr(bars),
        reason=reason,
    )


def _smart_checks(bars: Bars, fundamentals: Fundamentals, side: str, trend_days: int) -> list[Check]:
    rows = screen(
        bars,
        side,
        quarterly_eps=fundamentals.quarterly_eps,
        annual_eps=fundamentals.annual_eps,
        institutional_ownership=fundamentals.institutional_ownership,
        beta=fundamentals.beta,
        average_days=trend_days,
    )
    return [Check(name, passed, detail) for name, passed, detail in rows]


def contrary_exit(bars: Bars, side: str) -> bool:
    fast = sma(bars.close, 5)
    slow = sma(bars.close, 10)
    if side == "long":
        return cross_age(fast, slow, -1, 0) == 0
    return cross_age(fast, slow, 1, 0) == 0


def _latest_atr(bars: Bars) -> float | None:
    values = atr(bars.high, bars.low, bars.close, ATR_LENGTH)
    return None if not values else values[-1]


def _volume_detail(signal_volume: float, average_volume: float | None) -> str:
    if average_volume is None:
        return "Sin media de volumen de 50 barras"
    return f"Volumen de la señal {signal_volume:,.0f} contra la media de 50 barras {average_volume:,.0f}"


def _rsi_detail(value: float | None, ideal_label: str, ideal: bool) -> str:
    if value is None:
        return "Sin RSI"
    extra = f" Caso {ideal_label}." if ideal else ""
    return f"RSI {value:.1f}.{extra}"
