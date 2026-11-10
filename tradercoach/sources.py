"""Dónde dice el curso que se valida cada chequeo.

Las direcciones de Nasdaq y Yahoo salen de la hoja «IPG fundamental» del
Power Pack. El gráfico, las medias, el RSI, los soportes y el GAP de SPY
se revisan en Interactive Brokers, que es la plataforma de las lecciones
de gráficos, órdenes y de la técnica GAP.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from tradercoach.smart_picks import SECTOR_TRACKER, long_url, short_url


@dataclass(frozen=True)
class Access:
    check: str
    strategy: str
    source: str
    course: str
    read: str
    rule: str
    url: str | None

    def as_dict(self) -> dict:
        return {
            "chequeo": self.check,
            "estrategia": self.strategy,
            "fuente": self.source,
            "donde_en_el_curso": self.course,
            "que_leer": self.read,
            "regla": self.rule,
            "url": self.url,
        }


def web_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().replace(".", "-")
    if not cleaned or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for character in cleaned):
        raise ValueError(f"Símbolo no válido: {symbol}")
    return cleaned


def accesses(symbol: str) -> list[Access]:
    ticker = web_symbol(symbol)
    nasdaq = f"https://www.nasdaq.com/market-activity/stocks/{ticker.lower()}/earnings"
    statistics = f"https://finance.yahoo.com/quote/{ticker}/key-statistics?p={ticker}"
    holders = f"https://finance.yahoo.com/quote/{ticker}/holders?p={ticker}"
    history = f"https://finance.yahoo.com/quote/{ticker}/history?p={ticker}"
    options = f"https://finance.yahoo.com/quote/{ticker}/options?p={ticker}"
    spy_history = "https://finance.yahoo.com/quote/SPY/history?p=SPY"
    ib = "https://www.interactivebrokers.com/sso/Login"
    course = "https://inviertaparaganar.mykajabi.com/products/tradercoach-4-vip-platinum"
    network = "https://inviertaparaganar.ning.com/"
    return [
        Access(
            "EPS trimestral y EPS anual",
            "Factor X7 largo",
            "Nasdaq",
            "Hoja IPG fundamental del Power Pack. La ruta escrita en la hoja es www.nasdaq.com/symbol/TICKER/revenue-eps. Esa ruta ya no abre; la página vigente de resultados es la de abajo. Lección 6 y lección 14.",
            "EPS del trimestre contra el mismo trimestre del año anterior, y EPS del año contra el año previo.",
            "Trimestre mayor a 15% (preferible mayor a 30%). Año mayor a 25% (preferible mayor a 50%).",
            nasdaq,
        ),
        Access(
            "Oferta contra demanda y volumen promedio",
            "Factor X7 largo, y el volumen del cruce en largo y en corto",
            "Yahoo Finance, Key Statistics",
            "Hoja IPG fundamental: finance.yahoo.com/quote/TICKER/key-statistics?p=TICKER. Videos de Shares Outstanding, Average Vol y Beta.",
            "Shares outstanding y average volume de 3 meses. Beta, si quieres el dato del video extra.",
            "Oferta/demanda = acciones en circulación / volumen promedio de 3 meses. Más pequeño es mejor. El volumen del día de la señal debe superar ese promedio.",
            statistics,
        ),
        Access(
            "Propiedad institucional",
            "Factor X7 largo",
            "Yahoo Finance, Holders",
            "Hoja IPG fundamental: finance.yahoo.com/quote/TICKER/holders?p=TICKER. Lección 8, soporte institucional, y el resumen de la lección 14.",
            "Institutional ownership, el porcentaje que tienen las instituciones.",
            "Mayor a 50% y menor a 90%.",
            holders,
        ),
        Access(
            "Líderes, productos y servicios",
            "Factor X7 largo",
            "Revisión tuya",
            "Lección 14, bloque de análisis fundamental. El curso no da una página.",
            "Si la empresa tiene productos y líderes que reconoces como exitosos.",
            "Sin número. El bot no lo marca hasta que lo confirmas con --leader.",
            None,
        ),
        Access(
            "Tendencia de 3 meses, medias, volumen y RSI",
            "Factor X7 largo y corto",
            "Interactive Brokers",
            "Lecciones de gráficos, soporte y resistencia, RSI y análisis técnico. El resumen está en la lección 14. La plataforma de práctica del curso es Interactive Brokers.",
            f"Gráfico diario de {ticker} y de SPY. Medias de 5 y de 10, volumen, RSI de 14 y la pendiente de unos 3 meses.",
            "Largo: SPY y la acción alcistas 3 meses, SMA 5 cruza sobre SMA 10, volumen sobre la media de 50 barras, RSI 14 menor a 70. Corto: las dos tendencias bajistas, SMA 10 cruza sobre SMA 5, volumen sobre esa media, RSI mayor a 30. En el gráfico también va el ATR 14. StochRSI y RVI están en la plantilla y quedan ocultos.",
            ib,
        ),
        Access(
            "Puntos pivote diarios y semanales",
            "Stop y objetivo del Factor X7",
            "Interactive Brokers, indicador Pivot Points, y el histórico para calcularlos",
            "Lección 18. El gráfico del curso es el de Interactive Brokers. Esta página deja el OHLC por escrito.",
            f"Diario: high, low y close de ayer de {ticker}. Semanal: high, low y close de la semana anterior. También las medias de 5 y de 10.",
            "P = (H + L + C) / 3. R1 = (P x 2) - L. R2 = P + (H - L). S1 = (P x 2) - H. S2 = P - (H - L). El nivel funciona como soporte o resistencia según dónde esté el precio. El pivote es el nivel más importante. El stop y el objetivo se apoyan en esos niveles, con relación de al menos 2 a 1.",
            history,
        ),
        Access(
            "Smart Picks, filtro para largos",
            "Lista previa al Factor X7 largo",
            "Finviz",
            "Video Smart Picks filtro para largos. El sector del ejemplo era Technology. No queda fijo: se toma del Sector Tracker.",
            "EPS trimestre contra trimestre over 15%, EPS de este año over 25%, volumen promedio over 200K, institucional over 50%, beta over 0.5, SMA20 sobre SMA50, SMA50 sobre SMA200.",
            "Esos filtros, más el sector líder del día. El tope institucional de 90% es del Factor X7, no de este filtro.",
            long_url(),
        ),
        Access(
            "Smart Picks, filtro para cortos",
            "Lista previa al Factor X7 corto",
            "Finviz",
            "Video Smart Picks filtro para cortos.",
            "Volumen promedio over 200K, institucional over 50%, beta over 0.5, SMA20 bajo SMA50, SMA200 sobre SMA50 y SMA50 bajo SMA200. Ordenado por volumen. Sin EPS y sin sector.",
            "El corto del Factor X7 sigue sin pedir EPS. Este filtro sí pide volumen, beta, instituciones y la pila de medias invertida.",
            short_url(),
        ),
        Access(
            "Sector líder",
            "Sector que se agrega al filtro de largos",
            "Select Sector SPDRs, Sector Tracker",
            "Video Smart Picks, Sector Tracker. La lección 36 pide definir a qué sectores les das prioridad. La tabla Sectores Ferrari de esa clase es un ejemplo, no una lista permanente.",
            "El sector que lidera en el plazo que estés mirando, y sus componentes. En el video abren el sector y ordenan el cambio porcentual.",
            "El código de ese sector se agrega al filtro de largos. El ejemplo grabado usó Technology.",
            SECTOR_TRACKER,
        ),
        Access(
            "GAP de SPY",
            "Técnica GAP de SPY",
            "Interactive Brokers y el histórico de SPY",
            "Lecciones 22, 23 y 24, más la hoja GAP del Power Pack.",
            "Open, high, low y close de ayer, y la apertura de hoy, del símbolo SPY.",
            "Si hoy abre arriba del cierre de ayer, el lado es corto; si abre abajo, es largo. Probabilidad mayor a 70% y hueco entre 20% y 40% del rango de ayer. Objetivo: cierre de ayer. Stop: 30% de ese rango.",
            spy_history,
        ),
        Access(
            "Precio de la opción",
            "Compra de call si la señal es larga, compra de put si es corta",
            "Yahoo Finance, pestaña Options",
            "Lecciones 34 y 35, y el video Cómo encontrar el precio de las opciones. La página que abre el video es finance.yahoo.com/quote/MSFT/options. El ejercicio de la lección 34 pide comparar el precio de la acción con el del contrato.",
            f"En {ticker}: vencimiento del menú, strike, last price, bid y ask. Calls arriba y puts abajo.",
            "La compra del call limita la pérdida a la prima. La compra del put también. La venta cobra la prima y la pérdida no queda limitada a ese cobro; el papel no vende. Los ejemplos de la lección 35 usaron un call de junio por encima del precio: acción 525, strike 600 a 1.10; acción 354, strike 400 a 1.05. Si el precio llega al objetivo, la cuenta del call es (objetivo - strike) x 100 menos la prima x 100.",
            options,
        ),
        Access(
            "Análisis de las operaciones",
            "Revisión de la cuenta demo",
            "Diario del bot y la red privada",
            "Lección 27. El ejercicio pide los últimos 30 días de la demo, ejemplos de cuándo usaste el estado mental de trader y cuándo no, y tres pasos para las próximas operaciones.",
            "Disciplina con el plan y el diario. Paciencia: entrar con la señal y salir en el stop o en el objetivo. Objetividad. Expectativas 60-40, 50-50 o 40-60.",
            "No cambia la señal de entrada. El comando analisis resume el diario de los últimos 30 días.",
            network,
        ),
        Access(
            "10 mandamientos",
            "Antes de operar",
            "La lección 36 y el diario",
            "Lección 36. El ejercicio pide escribirlos y tenerlos a la vista.",
            "SPY a 12 y a 3 meses. Dirección del día. Sectores prioritarios. Primero las operaciones abiertas. Diario y plan.",
            "El bot imprime la lista en el comando analisis. No sustituye el repaso.",
            course,
        ),
        Access(
            "Hoja Power Pack",
            "EPS, tamaño de posición y GAP",
            "Curso TraderCoach 4",
            "Video Extra PowerPack, dentro del producto. El archivo es Power_Pack_Invierta_Para_Ganar_para_alumnos.xls.",
            "Hojas IPG fundamental, Admon. capital y GAP.",
            "Ahí están las fórmulas que el bot replica.",
            course,
        ),
        Access(
            "Compartir la operación de práctica",
            "Después de abrir la operación en demo",
            "Red privada Invierta Para Ganar",
            "Ejercicio de la lección 14.",
            "El comentario sobre cómo te sentiste al abrir la operación con las reglas.",
            "No cambia la señal.",
            network,
        ),
    ]


def render_html(symbol: str, items: list[Access]) -> str:
    ticker = web_symbol(symbol)
    rows = []
    for item in items:
        link = "Sin página fija en el curso."
        if item.url:
            safe = html.escape(item.url, quote=True)
            link = f'<a href="{safe}">{safe}</a>'
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.check)}</td>"
            f"<td>{html.escape(item.strategy)}</td>"
            f"<td>{html.escape(item.source)}</td>"
            f"<td>{html.escape(item.rule)}</td>"
            f"<td>{html.escape(item.read)}</td>"
            f"<td>{link}</td>"
            "</tr>"
        )
    body = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Validación {html.escape(ticker)}</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem; color: #1c1c1c; }}
    h1 {{ font-size: 1.6rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #ccc; text-align: left; vertical-align: top; padding: 0.6rem; }}
    a {{ color: #0b4f8a; }}
  </style>
</head>
<body>
  <h1>Dónde validar {html.escape(ticker)} según TraderCoach 4</h1>
  <p>Cada fila es un chequeo del curso y la página donde se lee. El corto del Factor X7 no usa EPS. El filtro Smart Picks de cortos sí pide volumen, beta e instituciones.</p>
  <table>
    <thead>
      <tr><th>Chequeo</th><th>Estrategia</th><th>Fuente</th><th>Regla</th><th>Qué mirar</th><th>Acceso</th></tr>
    </thead>
    <tbody>
      {body}
    </tbody>
  </table>
</body>
</html>
"""
