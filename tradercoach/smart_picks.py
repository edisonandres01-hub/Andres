"""Filtros de Smart Picks, copiados de la barra de Finviz en los videos.

Largo, el día del ejemplo el sector era Technology. Ese sector no es fijo:
sale del Sector Tracker. Corto: sin EPS y sin sector, ordenado por volumen.
"""

from __future__ import annotations

from tradercoach.bars import Bars
from tradercoach.indicators import eps_growth, sma

MIN_AVG_VOLUME = 200_000
MIN_BETA = 0.5
MIN_INSTITUTIONAL = 0.50

SECTOR_TRACKER = "https://www.sectorspdrs.com/sectortracker"

# El video de largos usó sec_technology. El resto son los códigos de Finviz
# para los ETF que el Sector Tracker lista.
SECTOR_CODES = {
    "XLK": "sec_technology",
    "XLF": "sec_financial",
    "XLE": "sec_energy",
    "XLV": "sec_healthcare",
    "XLY": "sec_consumercyclical",
    "XLP": "sec_consumerdefensive",
    "XLI": "sec_industrials",
    "XLB": "sec_basicmaterials",
    "XLRE": "sec_realestate",
    "XLC": "sec_communicationservices",
    "XLU": "sec_utilities",
}


def sector_code(sector: str | None) -> str | None:
    if not sector:
        return None
    cleaned = sector.strip()
    if cleaned.startswith("sec_"):
        return cleaned
    return SECTOR_CODES.get(cleaned.upper())


def long_url(sector: str | None = None) -> str:
    filters = ["fa_epsqoq_o15", "fa_epsyoy_o25"]
    code = sector_code(sector)
    if code:
        filters.append(code)
    filters.extend([
        "sh_avgvol_o200",
        "sh_instown_o50",
        "ta_beta_o0.5",
        "ta_sma20_sa50",
        "ta_sma200_sb50",
        "ta_sma50_sa200",
    ])
    return "https://finviz.com/screener.ashx?v=111&f=" + ",".join(filters) + "&ft=4"


def short_url() -> str:
    filters = ",".join([
        "sh_avgvol_o200",
        "sh_instown_o50",
        "ta_beta_o0.5",
        "ta_sma20_sb50",
        "ta_sma200_sa50",
        "ta_sma50_sb200",
    ])
    return f"https://finviz.com/screener.ashx?v=111&f={filters}&ft=4&o=-volume"


def moving_average_stack(close: list[float], bullish: bool) -> tuple[bool, str]:
    fast = sma(close, 20)[-1] if close else None
    middle = sma(close, 50)[-1] if close else None
    slow = sma(close, 200)[-1] if close else None
    if fast is None or middle is None or slow is None:
        return False, "Hacen falta 200 sesiones para las medias de 20, 50 y 200."
    detail = f"SMA20 {fast:.2f}, SMA50 {middle:.2f}, SMA200 {slow:.2f}"
    if bullish:
        return fast > middle > slow, detail
    return fast < middle < slow, detail


def screen(
    bars: Bars,
    side: str,
    quarterly_eps: list[float] | None = None,
    annual_eps: list[float] | None = None,
    institutional_ownership: float | None = None,
    beta: float | None = None,
    average_days: int = 63,
) -> list[tuple[str, bool, str]]:
    """Chequeos del filtro. El largo lleva EPS. El corto no."""
    prefix = "Smart Picks largo" if side == "long" else "Smart Picks corto"
    checks: list[tuple[str, bool, str]] = []
    average = sma(bars.volume, average_days)[-1] if bars.volume else None
    volume_ok = average is not None and average > MIN_AVG_VOLUME
    checks.append((
        f"{prefix}: volumen promedio mayor a 200.000",
        volume_ok,
        "Sin promedio" if average is None else f"Promedio {average:,.0f}",
    ))
    checks.append((
        f"{prefix}: propiedad institucional mayor a 50%",
        institutional_ownership is not None and institutional_ownership > MIN_INSTITUTIONAL,
        "Sin dato" if institutional_ownership is None else f"{institutional_ownership:.1%}. Finviz pide over 50% y no pone el tope de 90%.",
    ))
    checks.append((
        f"{prefix}: beta mayor a 0.5",
        beta is not None and beta > MIN_BETA,
        "Sin dato" if beta is None else f"Beta {beta:.2f}",
    ))
    stacked, stack_detail = moving_average_stack(bars.close, side == "long")
    order = "SMA20 sobre SMA50 y SMA50 sobre SMA200" if side == "long" else "SMA20 bajo SMA50 y SMA50 bajo SMA200"
    checks.append((f"{prefix}: {order}", stacked, stack_detail))
    if side == "long":
        q_growth = eps_growth(quarterly_eps[0], quarterly_eps[4]) if quarterly_eps and len(quarterly_eps) >= 5 else None
        a_growth = eps_growth(annual_eps[0], annual_eps[1]) if annual_eps and len(annual_eps) >= 2 else None
        checks.append((
            f"{prefix}: EPS del trimestre mayor a 15%",
            q_growth is not None and q_growth > 0.15,
            "Sin datos de EPS" if q_growth is None else f"Crecimiento {q_growth:.1%}",
        ))
        checks.append((
            f"{prefix}: EPS de este año mayor a 25%",
            a_growth is not None and a_growth > 0.25,
            "Sin datos de EPS" if a_growth is None else f"Crecimiento {a_growth:.1%}",
        ))
    return checks
