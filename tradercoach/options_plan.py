"""Compra de opciones para expresar una señal, lecciones 34 y 35.

El call se compra con expectativa alcista. El put se compra si se espera
una caída, o como cobertura. En la compra, la pérdida máxima es la prima.
La lección 34 también explica la venta: ahí se cobra la prima y la pérdida
no queda limitada a ese cobro. Este papel no vende opciones.

La lección 35 no fija un porcentaje de distancia ni un número de días.
En sus ejemplos, con la acción en 525 eligieron el call de junio strike 600
a 1.10, y con la acción en 354 el call de junio strike 400 a 1.05. Los dos
strikes están por encima del precio. El bot compra el strike fuera del dinero
más cercano al precio, en el vencimiento que Yahoo muestra al abrir la cadena.
La ganancia del ejemplo, si el precio llega al objetivo, es
(objetivo - strike) x 100 - prima x 100 para el call, y al revés para el put.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class OptionTicket:
    symbol: str
    right: str
    expiration: str
    strike: float
    premium: float
    contracts: int
    max_loss_usd: float
    stock_price: float
    target: float | None
    payoff_at_target: float | None
    note: str

    def as_dict(self) -> dict:
        controlled = self.contracts * 100 * self.stock_price
        return {
            "simbolo": self.symbol,
            "tipo": self.right,
            "vencimiento": self.expiration,
            "strike": self.strike,
            "prima": round(self.premium, 4),
            "contratos": self.contracts,
            "perdida_maxima_usd": round(self.max_loss_usd, 2),
            "precio_accion": round(self.stock_price, 4),
            "prima_contra_accion": None if self.stock_price == 0 else round(self.premium / self.stock_price, 6),
            "capital_en_prima_usd": round(self.max_loss_usd, 2),
            "acciones_controladas": self.contracts * 100,
            "capital_en_acciones_usd": round(controlled, 2),
            "ganancia_si_llega_al_objetivo_usd": None if self.payoff_at_target is None else round(self.payoff_at_target, 2),
            "nota": self.note,
        }


def contract_quantity(premium: float, max_loss_usd: float) -> int:
    if premium <= 0 or max_loss_usd <= 0:
        return 0
    return max(0, math.floor(max_loss_usd / (premium * 100)))


def payoff_at_target(right: str, strike: float, premium: float, target: float, contracts: int) -> float:
    """La cuenta de la lección 35, multiplicada por los contratos."""
    if right == "call":
        per_contract = ((target - strike) * 100) - (premium * 100)
    else:
        per_contract = ((strike - target) * 100) - (premium * 100)
    return per_contract * contracts


def choose_contract(
    symbol: str,
    side: str,
    spot: float,
    calls: list[dict],
    puts: list[dict],
    max_loss_usd: float,
    target: float | None = None,
) -> OptionTicket | None:
    chain = calls if side == "long" else puts
    right = "call" if side == "long" else "put"
    usable = [item for item in chain if item.get("premium") and item["premium"] > 0 and item.get("strike")]
    if side == "long":
        usable = [item for item in usable if float(item["strike"]) > spot]
    else:
        usable = [item for item in usable if float(item["strike"]) < spot]
    if not usable:
        return None
    selected = min(usable, key=lambda item: (abs(float(item["strike"]) - spot), item["expiration"]))
    contracts = contract_quantity(float(selected["premium"]), max_loss_usd)
    debit = contracts * float(selected["premium"]) * 100
    payoff = None
    if target is not None and contracts:
        payoff = payoff_at_target(right, float(selected["strike"]), float(selected["premium"]), target, contracts)
    if contracts:
        note = (
            "Compra. La pérdida máxima es la prima y cabe en el 2% del portafolio. "
            "El strike es el fuera de dinero más cercano al precio. "
            "Los ejemplos de la lección 35 usaron strikes más alejados: 525 a 600, y 354 a 400. "
            "Eso no es un porcentaje fijo."
        )
    else:
        note = "La prima de un solo contrato ya supera el 2% del portafolio."
    return OptionTicket(
        symbol=symbol,
        right=right,
        expiration=str(selected["expiration"]),
        strike=float(selected["strike"]),
        premium=float(selected["premium"]),
        contracts=contracts,
        max_loss_usd=debit,
        stock_price=spot,
        target=target,
        payoff_at_target=payoff,
        note=note,
    )
