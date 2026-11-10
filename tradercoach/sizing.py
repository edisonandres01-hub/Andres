"""Tamaño de la posición según la hoja de administración de capital.

La hoja deja como máximo el 30% del portafolio en una posición y muestra
la pérdida máxima como el 2% del portafolio. El número de acciones es el
menor de esos dos límites.
"""

from __future__ import annotations

import math


def position_size(
    portfolio_usd: float,
    price: float,
    stop_distance: float,
    max_position_fraction: float = 0.30,
    max_loss_fraction: float = 0.02,
) -> dict[str, float | int]:
    if portfolio_usd <= 0 or price <= 0 or stop_distance <= 0:
        return {
            "shares": 0,
            "invested": 0.0,
            "risk_usd": 0.0,
            "max_position_usd": 0.0,
            "max_loss_usd": 0.0,
        }
    max_position_usd = portfolio_usd * max_position_fraction
    max_loss_usd = portfolio_usd * max_loss_fraction
    by_capital = math.floor(max_position_usd / price)
    by_risk = math.floor(max_loss_usd / stop_distance)
    shares = max(0, min(by_capital, by_risk))
    return {
        "shares": shares,
        "invested": round(shares * price, 2),
        "risk_usd": round(shares * stop_distance, 2),
        "max_position_usd": round(max_position_usd, 2),
        "max_loss_usd": round(max_loss_usd, 2),
    }
