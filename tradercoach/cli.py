"""Línea de comandos del bot de simulación."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import webbrowser
from pathlib import Path

from tradercoach.factor_x7 import evaluate_stock
from tradercoach.ib_chart import TWS_TEMPLATE, layout
from tradercoach.gap_spy import evaluate_gap
from tradercoach.options_plan import choose_contract
from tradercoach.paper import append_journal, load_state, mark_to_market, save_state
from tradercoach.review import review_trades, spy_compass
from tradercoach.sources import accesses, render_html

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | None) -> dict:
    config_path = Path(path) if path else ROOT / "config.example.yaml"
    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError:
        return _parse_simple_yaml(text)
    return yaml.safe_load(text)


def _parse_scalar(value: str):
    if value in ("null", "Null", "~"):
        return None
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def _parse_simple_yaml(text: str) -> dict:
    """Lee el config de ejemplo si PyYAML no está instalado."""
    root: dict = {}
    stack: list[tuple[int, object, dict | None, str | None]] = [(-1, root, None, None)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        _, container, parent, parent_key = stack[-1]
        if line.startswith("- "):
            if isinstance(container, dict):
                container = []
                if parent is not None and parent_key is not None:
                    parent[parent_key] = container
                stack[-1] = (stack[-1][0], container, parent, parent_key)
            container.append(_parse_scalar(line[2:].strip()))
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if not isinstance(container, dict):
            continue
        if value == "":
            child: dict = {}
            container[key.strip()] = child
            stack.append((indent, child, container, key.strip()))
        else:
            container[key.strip()] = _parse_scalar(value)
    return root


def _print(title: str, payload: dict) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_demo(_: argparse.Namespace) -> None:
    """El ejemplo numérico que quedó guardado en la hoja del GAP."""
    plan = evaluate_gap(
        prev_open=200,
        prev_high=215,
        prev_low=190,
        prev_close=218,
        today_open=175.38,
        session=dt.date(2026, 11, 9),
        portfolio_usd=45_000,
        budget_usd=45_000,
        max_position_fraction=1.0,
        max_loss_fraction=1.0,
    )
    _print("Ejemplo de la hoja GAP de SPY (no se opera: fallan los dos filtros)", plan.as_dict())
    passing = evaluate_gap(
        prev_open=95,
        prev_high=100,
        prev_low=80,
        prev_close=90,
        today_open=84,
        session=dt.date(2026, 10, 8),
        portfolio_usd=10_000,
    )
    _print("Ejemplo construido para mostrar un GAP que sí calza en los filtros", passing.as_dict())


def command_gap(args: argparse.Namespace) -> None:
    from tradercoach.data import download_history

    config = load_config(args.config)
    gap_config = config["gap"]
    symbol = gap_config.get("symbol", "SPY")
    history = download_history(symbol, period="1mo")
    if len(history) < 2:
        raise SystemExit(f"No hay dos sesiones de {symbol}.")
    session = history.dates[-1]
    portfolio = float(config["portfolio_usd"])
    plan = evaluate_gap(
        prev_open=history.open[-2],
        prev_high=history.high[-2],
        prev_low=history.low[-2],
        prev_close=history.close[-2],
        today_open=history.open[-1],
        session=session,
        portfolio_usd=portfolio,
        budget_usd=gap_config.get("budget_usd"),
        max_position_fraction=float(config["max_position_fraction"]),
        max_loss_fraction=float(config["max_loss_fraction"]),
        min_probability=float(gap_config["min_probability"]),
        gap_range_min=float(gap_config["gap_range_min"]),
        gap_range_max=float(gap_config["gap_range_max"]),
        stop_range_fraction=float(gap_config["stop_range_fraction"]),
    )
    _print(f"GAP de {symbol}", plan.as_dict())


def command_scan(args: argparse.Namespace) -> None:
    from tradercoach.data import download_fundamentals, download_history, option_chain

    config = load_config(args.config)
    symbols = args.symbols or config["watchlist"]
    portfolio = float(config["portfolio_usd"])
    spy = download_history("SPY")
    _print("Brújula de SPY, mandamiento 1", spy_compass(spy.close))
    plans = []
    for symbol in symbols:
        try:
            history = download_history(symbol)
            fundamentals = download_fundamentals(symbol)
        except Exception as error:
            print(f"{symbol}: no se pudo leer ({error})")
            continue
        if args.leader:
            fundamentals.leader_confirmed = True
        plan = evaluate_stock(
            symbol,
            history,
            spy,
            fundamentals,
            portfolio_usd=portfolio,
            max_position_fraction=float(config["max_position_fraction"]),
            max_loss_fraction=float(config["max_loss_fraction"]),
            min_reward_risk=float(config["min_reward_risk"]),
            signal_max_age_days=int(config["signal_max_age_days"]),
            trend_days=int(config["trend_days"]),
            rsi_period=int(config["rsi_period"]),
            swing_lookback=int(config["swing_lookback"]),
            max_supply_demand_days=config.get("max_supply_demand_days"),
        )
        payload = plan.as_dict()
        if args.instrument in ("options", "both") and plan.side in ("long", "short"):
            try:
                calls, puts = option_chain(symbol)
                ticket = choose_contract(
                    symbol,
                    plan.side,
                    plan.entry,
                    calls,
                    puts,
                    portfolio * float(config["max_loss_fraction"]),
                    target=plan.target,
                )
                payload["opcion"] = None if ticket is None else ticket.as_dict()
            except Exception as error:
                payload["opcion"] = {"error": str(error)}
        plans.append(payload)
        state = "OPERABLE" if plan.tradable else "no"
        print(f"{symbol:6} {plan.side:5} {state:8} {plan.reason}")
        if plan.stop is not None and plan.target is not None:
            stop_at = plan.pivots.get("stop_nivel") or "pivote"
            target_at = plan.pivots.get("objetivo_nivel") or "objetivo"
            print(f"       stop {plan.stop:.2f} en {stop_at}; objetivo {plan.target:.2f} en {target_at}")
    if args.show_all:
        _print("Detalle", {"planes": plans})
    else:
        operable = [item for item in plans if item["operable"]]
        _print("Señales operables", {"planes": operable})


def command_paper(args: argparse.Namespace) -> None:
    from tradercoach.data import download_fundamentals, download_history

    config = load_config(args.config)
    journal = ROOT / config["journal_csv"]
    state_path = ROOT / config["state_json"]
    state = load_state(state_path)
    today = dt.date.today().isoformat()
    print("Primero se revisan las operaciones abiertas. Después se buscan señales nuevas.")
    portfolio = float(config["portfolio_usd"])
    spy = download_history("SPY")
    still_open = []
    for position in state["positions"]:
        history = download_history(position["simbolo"])
        closed = mark_to_market(position, history)
        if closed:
            closed["fecha"] = today
            append_journal(journal, closed)
            print(f"Cierre simulado {position['simbolo']} por {closed['evento']} en {closed['precio']}")
        else:
            still_open.append(position)
    open_symbols = {item["simbolo"] for item in still_open}
    for symbol in config["watchlist"]:
        if symbol in open_symbols:
            continue
        history = download_history(symbol)
        fundamentals = download_fundamentals(symbol)
        plan = evaluate_stock(
            symbol,
            history,
            spy,
            fundamentals,
            portfolio_usd=portfolio,
            max_position_fraction=float(config["max_position_fraction"]),
            max_loss_fraction=float(config["max_loss_fraction"]),
            min_reward_risk=float(config["min_reward_risk"]),
            signal_max_age_days=int(config["signal_max_age_days"]),
            trend_days=int(config["trend_days"]),
            rsi_period=int(config["rsi_period"]),
            swing_lookback=int(config["swing_lookback"]),
            max_supply_demand_days=config.get("max_supply_demand_days"),
        )
        if not plan.tradable:
            continue
        position = {
            "simbolo": symbol,
            "lado": plan.side,
            "entrada": plan.entry,
            "stop": plan.stop,
            "objetivo": plan.target,
            "acciones": plan.shares,
            "abierta": today,
        }
        still_open.append(position)
        append_journal(journal, {
            "fecha": today,
            "simbolo": symbol,
            "evento": "apertura",
            "lado": plan.side,
            "precio": plan.entry,
            "acciones": plan.shares,
            "stop": plan.stop,
            "objetivo": plan.target,
            "nota": plan.reason,
        })
        print(f"Apertura simulada {symbol} {plan.side} {plan.shares} @ {plan.entry:.2f}")
    state["positions"] = still_open
    save_state(state_path, state)
    print(f"Posiciones simuladas abiertas: {len(still_open)}. Diario: {journal}")


def command_review(args: argparse.Namespace) -> None:
    import csv

    config = load_config(args.config)
    journal = ROOT / config["journal_csv"]
    rows = []
    if journal.exists():
        with journal.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    report = review_trades(rows, dt.date.today())
    _print("Análisis de operaciones, lección 27", report)


def command_template(_: argparse.Namespace) -> None:
    _print("Plantilla Factor X7 de Interactive Brokers", layout())
    print("En TWS: gráfico, clic derecho, Plantillas, y elige factor X7.")
    print(f"Archivo: {TWS_TEMPLATE}")


def command_sources(args: argparse.Namespace) -> None:
    items = accesses(args.symbol)
    print(f"Validación de {args.symbol.strip().upper()} según el curso\n")
    for number, item in enumerate(items, start=1):
        print(f"{number}. {item.check} — {item.strategy}")
        print(f"   Fuente: {item.source}")
        print(f"   Curso: {item.course}")
        print(f"   Mirar: {item.read}")
        print(f"   Regla: {item.rule}")
        print(f"   Acceso: {item.url or 'sin página fija'}")
        print()
    if args.html or args.open:
        destination = ROOT / "data" / f"accesos-{args.symbol.strip().upper().replace('.', '-')}.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_html(args.symbol, items), encoding="utf-8")
        print(f"Página de accesos: {destination}")
        if args.open:
            webbrowser.open(destination.resolve().as_uri())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulador de las reglas de TraderCoach 4. No envía órdenes.")
    parser.add_argument("--config", help="Ruta a config.yaml. Si se omite, usa config.example.yaml.")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Muestra el ejemplo numérico de la hoja del GAP.")
    demo.set_defaults(func=command_demo)
    gap = sub.add_parser("gap", help="Evalúa el GAP de SPY con la última sesión.")
    gap.set_defaults(func=command_gap)
    scan = sub.add_parser("scan", help="Busca señales del Factor X7 en la lista.")
    scan.add_argument("--symbols", nargs="*", help="Símbolos a revisar, en lugar de la lista del config.")
    scan.add_argument("--instrument", choices=("shares", "options", "both"), default="shares")
    scan.add_argument("--leader", action="store_true", help="Marca como confirmado el chequeo cualitativo de líderes y productos.")
    scan.add_argument("--show-all", action="store_true", help="Imprime también las acciones que no dieron señal.")
    scan.set_defaults(func=command_scan)
    paper = sub.add_parser("paper", help="Actualiza el diario simulado. No opera en un bróker.")
    paper.set_defaults(func=command_paper)
    review = sub.add_parser("analisis", help="Revisa el diario de los últimos 30 días, lección 27, y lista los mandamientos.")
    review.set_defaults(func=command_review)
    template = sub.add_parser("plantilla", help="Muestra el gráfico Factor X7 que se carga en TWS.")
    template.set_defaults(func=command_template)
    sources = sub.add_parser("fuentes", help="Muestra dónde validar un símbolo según el curso.")
    sources.add_argument("symbol", help="Símbolo, por ejemplo AAPL.")
    sources.add_argument("--html", action="store_true", help="Escribe data/accesos-SIMBOLO.html con los enlaces.")
    sources.add_argument("--abrir", dest="open", action="store_true", help="Crea el HTML y lo abre en el navegador.")
    sources.set_defaults(func=command_sources)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
