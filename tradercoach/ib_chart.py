"""Gráfico Factor X7 tal como queda guardado en la plantilla de TWS.

El archivo no trae condiciones de orden. Trae el gráfico: velas de la
sesión regular, ChartTrader para poner la orden a mano, y estos estudios.
StochRSI y RVI están en el archivo y quedan ocultos. La ventana guardada
en x7.tpl es de 161 horas con la barra en automático.
"""

from __future__ import annotations

from pathlib import Path

SMA_FAST = 5
SMA_SLOW = 10
RSI_LENGTH = 14
ATR_LENGTH = 14
VOLUME_SMA_LENGTH = 50
RVI_DEVIATION = 10
RVI_EMA = 14
STOCH_RSI_LENGTH = 14
WINDOW_COUNT = 161
WINDOW_UNIT = "hours"
TWS_TEMPLATE = Path(r"C:\Jts\charts\factor X7.tpl")

VISIBLE = (
    "Velas, coloreadas por cierre contra apertura, solo horario regular.",
    "SMA 5 sobre el precio.",
    "SMA 10 sobre el precio.",
    "RSI 14 en su propio panel.",
    "Media del volumen de 50 barras.",
    "ATR 14.",
    "ChartTrader abierto, para escribir la orden a mano.",
    "Cierre previo, zona de cotización y etiqueta de la orden.",
    "Sin ajuste por dividendos.",
)

HIDDEN = (
    "StochRSI 14, oculto.",
    "RVI con desviación 10 y EMA 14, oculto.",
)


def layout() -> dict:
    return {
        "archivo": str(TWS_TEMPLATE),
        "ventana": f"{WINDOW_COUNT} {WINDOW_UNIT}",
        "barra": "automática",
        "sesion": "solo horario regular",
        "enrutamiento": "SMART",
        "estudios_visibles": list(VISIBLE),
        "estudios_ocultos": list(HIDDEN),
        "nota": (
            "La plantilla no envía la orden. ChartTrader es el panel para "
            "colocarla a mano en la cuenta demo. El bot sigue en papel."
        ),
    }
