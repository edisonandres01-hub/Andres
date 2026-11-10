"""Serie diaria de precios. No usa pandas."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass
class Bars:
    dates: list[dt.date]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    volume: list[float]

    def __len__(self) -> int:
        return len(self.close)
