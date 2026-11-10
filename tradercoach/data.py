"""Precios y fundamentales desde Yahoo Finance, con la biblioteca estándar."""

from __future__ import annotations

import datetime as dt
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request

from tradercoach.bars import Bars
from tradercoach.factor_x7 import Fundamentals

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={period}"
SUMMARY = (
    "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
    "?modules=earnings,defaultKeyStatistics,majorHoldersBreakdown,incomeStatementHistory"
)
TIMESERIES = (
    "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}"
    "?symbol={symbol}&type=quarterlyDilutedEPS,annualDilutedEPS&period1=946684800&period2={now}"
)


_OPENER = None
_CRUMB = None


def _opener():
    global _OPENER
    if _OPENER is None:
        jar = http.cookiejar.CookieJar()
        _OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return _OPENER


def _read(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with _opener().open(request, timeout=30) as response:
        return response.read()


def _crumb() -> str:
    global _CRUMB
    if _CRUMB:
        return _CRUMB
    try:
        _read("https://fc.yahoo.com")
    except urllib.error.HTTPError:
        pass
    _CRUMB = _read("https://query1.finance.yahoo.com/v1/test/getcrumb").decode().strip()
    return _CRUMB


def _get_json(url: str, authenticated: bool = False) -> dict:
    if authenticated:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}crumb={urllib.parse.quote(_crumb())}"
    return json.loads(_read(url).decode("utf-8"))


def download_history(symbol: str, period: str = "2y") -> Bars:
    payload = _get_json(CHART.format(symbol=symbol, period=period))
    result = payload["chart"]["result"]
    if not result:
        raise RuntimeError(f"No hubo precios para {symbol}.")
    block = result[0]
    timestamps = block.get("timestamp") or []
    quote = block["indicators"]["quote"][0]
    dates: list[dt.date] = []
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[float] = []
    for index, stamp in enumerate(timestamps):
        values = (
            quote["open"][index],
            quote["high"][index],
            quote["low"][index],
            quote["close"][index],
            quote["volume"][index],
        )
        if any(value is None for value in values):
            continue
        dates.append(dt.datetime.fromtimestamp(stamp, dt.timezone.utc).date())
        opens.append(float(values[0]))
        highs.append(float(values[1]))
        lows.append(float(values[2]))
        closes.append(float(values[3]))
        volumes.append(float(values[4]))
    if len(closes) < 2:
        raise RuntimeError(f"No hubo precios para {symbol}.")
    return Bars(dates, opens, highs, lows, closes, volumes)


def _raw(node) -> float | None:
    if isinstance(node, dict) and "raw" in node:
        return float(node["raw"])
    if isinstance(node, (int, float)):
        return float(node)
    return None


def _series_from_timeseries(payload: dict, key: str) -> list[float] | None:
    results = payload.get("timeseries", {}).get("result") or []
    for block in results:
        rows = block.get(key) or []
        dated = []
        for row in rows:
            value = row.get("reportedValue", {}).get("raw")
            stamp = row.get("asOfDate")
            if value is None or stamp is None:
                continue
            dated.append((stamp, float(value)))
        if dated:
            dated.sort(reverse=True)
            return [value for _, value in dated]
    return None


def download_fundamentals(symbol: str) -> Fundamentals:
    quarterly = None
    annual = None
    shares = None
    ownership = None
    try:
        now = int(dt.datetime.now(dt.timezone.utc).timestamp())
        series = _get_json(TIMESERIES.format(symbol=symbol, now=now))
        quarterly = _series_from_timeseries(series, "quarterlyDilutedEPS")
        annual = _series_from_timeseries(series, "annualDilutedEPS")
    except Exception:
        quarterly = None
        annual = None
    try:
        summary = _get_json(SUMMARY.format(symbol=symbol), authenticated=True)
        result = (summary.get("quoteSummary", {}).get("result") or [{}])[0]
    except Exception:
        result = {}
    if quarterly is None:
        history = (((result.get("earnings") or {}).get("earningsChart") or {}).get("quarterly") or [])
        values = []
        for row in reversed(history):
            actual = row.get("actual")
            if isinstance(actual, dict):
                actual = actual.get("raw")
            if actual is not None:
                values.append(float(actual))
        values.reverse()
        quarterly = values or None
    stats = result.get("defaultKeyStatistics") or {}
    holders = result.get("majorHoldersBreakdown") or {}
    shares = _raw(stats.get("sharesOutstanding"))
    ownership = _raw(holders.get("institutionsPercentHeld"))
    beta = _raw(stats.get("beta"))
    return Fundamentals(
        quarterly_eps=quarterly,
        annual_eps=annual,
        shares_outstanding=shares,
        institutional_ownership=ownership,
        beta=beta,
    )


def option_chain(symbol: str) -> tuple[list[dict], list[dict]]:
    """Cadena del vencimiento que Yahoo abre primero en la pestaña Options.

    El video después cambia la fecha en el menú. El ejemplo de la lección 35
    era un vencimiento de junio. El curso no fija una cantidad de días.
    """
    meta_url = f"https://query2.finance.yahoo.com/v7/finance/options/{symbol}"
    listing = _get_json(meta_url, authenticated=True)
    chain = (listing.get("optionChain", {}).get("result") or [{}])[0]
    options = (chain.get("options") or [{}])[0]
    if not options.get("calls") and not options.get("puts") and chain.get("expirationDates"):
        stamp = chain["expirationDates"][0]
        detailed = _get_json(f"{meta_url}?date={stamp}", authenticated=True)
        chain = (detailed.get("optionChain", {}).get("result") or [{}])[0]
        options = (chain.get("options") or [{}])[0]
    stamp = options.get("expirationDate") or (chain.get("expirationDates") or [None])[0]
    if stamp is None:
        return [], []
    expiration = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).date().isoformat()

    def rows(items: list[dict]) -> list[dict]:
        records = []
        for item in items or []:
            bid = float(item.get("bid") or 0)
            ask = float(item.get("ask") or 0)
            last = float(item.get("lastPrice") or 0)
            premium = (bid + ask) / 2 if bid > 0 and ask > 0 else last
            records.append({
                "expiration": expiration,
                "strike": float(item["strike"]),
                "premium": premium,
            })
        return records

    return rows(options.get("calls")), rows(options.get("puts"))
