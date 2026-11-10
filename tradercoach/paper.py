"""Diario y posiciones simuladas. No hay conexión con un bróker."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from tradercoach.bars import Bars
from tradercoach.factor_x7 import contrary_exit


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"positions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def append_journal(path: Path, row: dict) -> None:
    _ensure_parent(path)
    fields = [
        "fecha",
        "simbolo",
        "evento",
        "lado",
        "precio",
        "acciones",
        "stop",
        "objetivo",
        "nota",
    ]
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new_file:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def mark_to_market(position: dict, bars: Bars) -> dict | None:
    """Cierra en stop, objetivo o señal contraria. Devuelve la fila del diario si cierra."""
    side = position["lado"]
    low = bars.low[-1]
    high = bars.high[-1]
    close = bars.close[-1]
    stop = float(position["stop"])
    target = float(position["objetivo"])
    if side == "long":
        if low <= stop:
            return _close_row(position, stop, "stop")
        if high >= target:
            return _close_row(position, target, "objetivo")
    else:
        if high >= stop:
            return _close_row(position, stop, "stop")
        if low <= target:
            return _close_row(position, target, "objetivo")
    if contrary_exit(bars, side):
        return _close_row(position, close, "senal contraria")
    return None


def _close_row(position: dict, price: float, event: str) -> dict:
    return {
        "fecha": "",
        "simbolo": position["simbolo"],
        "evento": event,
        "lado": position["lado"],
        "precio": round(price, 4),
        "acciones": position["acciones"],
        "stop": position["stop"],
        "objetivo": position["objetivo"],
        "nota": "Cierre simulado. No se envió ninguna orden.",
    }
