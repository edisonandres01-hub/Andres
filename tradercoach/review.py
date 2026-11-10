"""Análisis de operaciones de la lección 27 y los 10 mandamientos de la 36.

La lección 27 no agrega un filtro de entrada. Pide revisar los últimos
30 días de la cuenta demo, entrar solo con la señal y salir en el stop
o en el objetivo, y tener presente que un resultado 60-40, 50-50 o 40-60
cabe en lo que el curso llama expectativas realistas.
"""

from __future__ import annotations

import datetime as dt

from tradercoach.indicators import sma, trend_aligned

MENTAL_STATE = (
    "Disciplina: seguir el plan y usar el diario.",
    "Paciencia: entrar con la señal y salir en el stop o en el objetivo.",
    "Objetividad: ni tan contento al ganar, ni tan triste al perder.",
    "Expectativas realistas: el curso marca como posibles 60-40, 50-50 y 40-60.",
)

IMPULSE_STEPS = (
    "Identificar el trigger, por ejemplo aburrimiento, una noticia o un amigo.",
    "Invocar ese trigger estando concentrado.",
    "Practicar mentalmente la conducta nueva.",
)

PLAN_STEPS = (
    "Entrar en un estado de alta energía.",
    "Practicar y visualizar el plan del día, con charla interna positiva.",
    "Volver a ese estado si ves que estás por equivocarte.",
)

COMMANDMENTS = (
    "Revisar qué hizo SPY en los últimos 12 meses y en los últimos 3.",
    "Definir hacia dónde harás trading. En la clase, la brújula estaba alcista y proponían comprar con el Factor X7. Eso era el momento de esa grabación.",
    "Definir a qué sectores les das prioridad. La diapositiva muestra un ejemplo, Sectores Ferrari: bancos, préstamos, telecomunicaciones, acero e industrial. No es una lista fija. El sector del filtro largo sale del Sector Tracker.",
    "Revisar primero las operaciones abiertas y después las señales nuevas.",
    "Elevar la energía todos los días.",
    "Invertir primero en ti.",
    "Hacer la hora IPG cada día.",
    "Usar siempre el diario. La experiencia hace al maestro.",
    "Triángulo de la prosperidad: aprender y hacer, manejar los recursos, y calidad en lo que haces.",
    "Respetar siempre el plan de trading.",
)


def spy_compass(close: list[float]) -> dict:
    """Mandamiento 1: qué hizo SPY en 12 meses y en 3 meses."""
    if trend_aligned(close, 63, True):
        three = "alcista"
    elif trend_aligned(close, 63, False):
        three = "bajista"
    else:
        three = "sin tendencia clara de 3 meses"
    twelve = "sin 12 meses de datos"
    if len(close) > 252:
        direction = "alcista" if close[-1] > close[-253] else "bajista"
        average = sma(close, 252)[-1]
        if average is None:
            twelve = direction
        elif close[-1] > average:
            twelve = f"{direction}, sobre la media de 252 sesiones"
        else:
            twelve = f"{direction}, bajo la media de 252 sesiones"
    return {
        "tres_meses": three,
        "doce_meses": twelve,
        "nota": "La brújula de la lección 36 se define con esto. En la grabación estaba alcista y proponían comprar con el Factor X7. No es una orden permanente de solo largos.",
    }


def _parse_day(value: str) -> dt.date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def review_trades(rows: list[dict], today: dt.date, window_days: int = 30) -> dict:
    start = today - dt.timedelta(days=window_days)
    recent = []
    for row in rows:
        day = _parse_day(str(row.get("fecha", "")))
        if day is not None and start <= day <= today:
            recent.append(row)
    wins = [row for row in recent if row.get("evento") == "objetivo"]
    stops = [row for row in recent if row.get("evento") == "stop"]
    contrary = [row for row in recent if row.get("evento") == "senal contraria"]
    opened = [row for row in recent if row.get("evento") == "apertura"]
    decided = len(wins) + len(stops)
    win_rate = (len(wins) / decided) if decided else None
    inside_band = None if win_rate is None else 0.40 <= win_rate <= 0.60
    if win_rate is None:
        expectation = "Todavía no hay cierres en stop u objetivo dentro de estos 30 días."
    elif inside_band:
        expectation = "El porcentaje de aciertos está entre 40% y 60%, el rango que la lección marca como posible."
    else:
        expectation = "El porcentaje de aciertos quedó fuera de 40% a 60%. La lección pide tener claro que 60-40, 50-50 y 40-60 son escenarios posibles."
    return {
        "desde": start.isoformat(),
        "hasta": today.isoformat(),
        "aperturas": len(opened),
        "objetivos": len(wins),
        "stops": len(stops),
        "cruces_contrarios": len(contrary),
        "aciertos": None if win_rate is None else round(win_rate, 4),
        "dentro_de_40_a_60": inside_band,
        "expectativa": expectation,
        "nota_salida": (
            "La lección 27 pide salir en el stop o en el objetivo. "
            "El Factor X7, además, cierra si las medias se cruzan al revés."
        ),
        "estado_mental": list(MENTAL_STATE),
        "reducir_impulso": list(IMPULSE_STEPS),
        "seguir_el_plan": list(PLAN_STEPS),
        "mandamientos": list(COMMANDMENTS),
    }
