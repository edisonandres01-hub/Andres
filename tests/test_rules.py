import datetime as dt
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tradercoach.bars import Bars
from tradercoach.factor_x7 import Fundamentals, evaluate_stock
from tradercoach.gap_spy import evaluate_gap, zone_probability
from tradercoach.ib_chart import VOLUME_SMA_LENGTH, layout
from tradercoach.indicators import atr, cross_age, eps_growth, floor_pivots
from tradercoach.options_plan import choose_contract, contract_quantity
from tradercoach.review import review_trades
from tradercoach.sizing import position_size
from tradercoach.smart_picks import long_url, short_url
from tradercoach.sources import accesses, web_symbol


class GapSheetExample(unittest.TestCase):
    def test_saved_example_matches_the_spreadsheet(self):
        plan = evaluate_gap(
            prev_open=200,
            prev_high=215,
            prev_low=190,
            prev_close=218,
            today_open=175.38,
            session=dt.date(2026, 11, 9),
            portfolio_usd=45_000,
            budget_usd=45_000,
            max_position_fraction=1,
            max_loss_fraction=1,
        )
        self.assertEqual(plan.side, "long")
        self.assertAlmostEqual(plan.zone_probability, 0.54)
        self.assertAlmostEqual(plan.gap_to_range, 42.62 / 25, places=4)
        self.assertAlmostEqual(plan.probability, 0.58695, places=4)
        self.assertFalse(plan.probability_ok)
        self.assertFalse(plan.size_ok)
        self.assertAlmostEqual(plan.stop, 167.88, places=2)
        self.assertEqual(plan.target, 218)
        self.assertEqual(plan.shares, math.floor(45_000 / 175.38))
        self.assertFalse(plan.tradable)

    def test_gap_down_inside_the_band_can_pass(self):
        plan = evaluate_gap(
            prev_open=95,
            prev_high=100,
            prev_low=80,
            prev_close=90,
            today_open=84,
            session=dt.date(2026, 10, 8),
            portfolio_usd=10_000,
        )
        self.assertEqual(plan.side, "long")
        self.assertAlmostEqual(plan.gap_to_range, 0.30, places=4)
        self.assertAlmostEqual(zone_probability(95, 100, 80, 90, 84), 0.78)
        self.assertTrue(plan.size_ok)
        self.assertTrue(plan.probability_ok)
        self.assertTrue(plan.tradable)
        self.assertAlmostEqual(plan.target, 90)
        self.assertAlmostEqual(plan.stop, 84 - (20 * 0.30), places=4)

    def test_gap_up_is_a_short(self):
        plan = evaluate_gap(
            prev_open=90,
            prev_high=100,
            prev_low=80,
            prev_close=95,
            today_open=101,
            session=dt.date(2026, 10, 8),
            portfolio_usd=10_000,
        )
        self.assertEqual(plan.side, "short")
        self.assertGreater(plan.stop, plan.entry)
        self.assertEqual(plan.target, 95)


class SizingTests(unittest.TestCase):
    def test_sheet_example_uses_thirty_percent_when_risk_fits(self):
        size = position_size(10_000, 18.7, 0.79)
        self.assertEqual(size["shares"], 160)
        self.assertAlmostEqual(size["risk_usd"], 126.4, places=2)
        self.assertAlmostEqual(size["max_loss_usd"], 200)

    def test_wide_stop_is_cut_by_the_two_percent_rule(self):
        size = position_size(10_000, 100, 10)
        self.assertEqual(size["shares"], 20)
        self.assertAlmostEqual(size["risk_usd"], 200)


class FactorTests(unittest.TestCase):
    def test_eps_formula_matches_the_sheet(self):
        self.assertAlmostEqual(eps_growth(0.46, 0.29), 0.586206896551724, places=6)

    def test_cross_age_finds_a_fresh_cross(self):
        fast = [1, 1, 1, 2, 3]
        slow = [2, 2, 2, 2, 2]
        self.assertEqual(cross_age(fast, slow, 1, 2), 0)
        self.assertIsNone(cross_age(fast, slow, -1, 2))

    def test_long_signal_on_a_constructed_series(self):
        stock_close = _long_closes()
        spy_close = [100 + index * 0.4 for index in range(len(stock_close))]
        frame = _ohlcv(stock_close, volume=1_000_000, last_volume=2_000_000)
        spy = _ohlcv(spy_close)
        fundamentals = Fundamentals(
            quarterly_eps=[1.40, 1.20, 1.10, 1.00, 1.00],
            annual_eps=[5.0, 3.0],
            shares_outstanding=50_000_000,
            institutional_ownership=0.62,
            beta=1.1,
            leader_confirmed=True,
        )
        plan = evaluate_stock("TEST", frame, spy, fundamentals, portfolio_usd=100_000, trend_days=63)
        self.assertEqual(plan.side, "long", plan.reason)
        self.assertTrue(plan.tradable, plan.reason)
        self.assertGreaterEqual(plan.reward_risk, 2)
        self.assertLess(plan.stop, plan.entry)
        self.assertGreater(plan.target, plan.entry)
        names = {item.name: item.passed for item in plan.checks}
        self.assertTrue(names["Volumen sobre la media de 50 barras"])
        self.assertIsNotNone(plan.atr)
        self.assertTrue(names["EPS trimestral mayor a 15%"])
        self.assertTrue(names["EPS anual mayor a 25%"])
        self.assertTrue(names["Propiedad institucional entre 50% y 90%"])

    def test_short_does_not_require_fundamentals(self):
        stock_close = _short_closes()
        spy_close = [200 - index * 0.4 for index in range(len(stock_close))]
        frame = _ohlcv(stock_close, volume=1_000_000, last_volume=2_000_000)
        spy = _ohlcv(spy_close)
        plan = evaluate_stock(
            "TEST",
            frame,
            spy,
            Fundamentals(institutional_ownership=0.62, beta=1.1),
            portfolio_usd=100_000,
            trend_days=63,
        )
        self.assertEqual(plan.side, "short", plan.reason)
        self.assertTrue(plan.tradable, plan.reason)
        self.assertFalse(any(item.name.startswith("EPS") for item in plan.checks))
        self.assertFalse(any("EPS" in item.name for item in plan.checks if item.name.startswith("Smart Picks")))
        self.assertTrue(plan.pivots["diarios"]["P"])
        self.assertTrue(plan.pivots["semanales"])

    def test_institutional_band_is_strict(self):
        stock_close = _long_closes()
        frame = _ohlcv(stock_close, last_volume=2_000_000)
        spy = _ohlcv([100 + index * 0.4 for index in range(len(stock_close))])
        too_high = Fundamentals(
            quarterly_eps=[2, 1, 1, 1, 1],
            annual_eps=[4, 2],
            shares_outstanding=10_000_000,
            institutional_ownership=0.90,
        )
        plan = evaluate_stock("TEST", frame, spy, too_high, portfolio_usd=100_000, trend_days=40)
        ownership = next(item for item in plan.checks if "institucional" in item.name)
        self.assertFalse(ownership.passed)


class SourceTests(unittest.TestCase):
    def test_course_pages_use_the_symbol(self):
        self.assertEqual(web_symbol("brk.b"), "BRK-B")
        pages = {item.check: item.url for item in accesses("AAPL")}
        self.assertEqual(
            pages["EPS trimestral y EPS anual"],
            "https://www.nasdaq.com/market-activity/stocks/aapl/earnings",
        )
        self.assertIn("quote/AAPL/key-statistics?p=AAPL", pages["Oferta contra demanda y volumen promedio"])
        self.assertIn("quote/AAPL/holders?p=AAPL", pages["Propiedad institucional"])
        self.assertIn("quote/SPY/history", pages["GAP de SPY"])
        self.assertIsNone(pages["Líderes, productos y servicios"])
        self.assertIn("fa_epsqoq_o15", pages["Smart Picks, filtro para largos"])
        self.assertIn("ta_sma20_sa50", pages["Smart Picks, filtro para largos"])
        self.assertNotIn("sec_technology", pages["Smart Picks, filtro para largos"])
        self.assertIn("o=-volume", pages["Smart Picks, filtro para cortos"])
        self.assertIn("sectorspdrs.com/sectortracker", pages["Sector líder"])


class OptionTests(unittest.TestCase):
    def test_quantity_keeps_premium_inside_the_loss_limit(self):
        self.assertEqual(contract_quantity(2.5, 200), 0)
        self.assertEqual(contract_quantity(1.5, 200), 1)

    def test_long_signal_buys_the_nearest_call(self):
        calls = [
            {"expiration": "2026-12-18", "strike": 90, "premium": 3},
            {"expiration": "2026-12-18", "strike": 100, "premium": 1.2},
            {"expiration": "2026-12-18", "strike": 110, "premium": 0.4},
        ]
        ticket = choose_contract("AAA", "long", 101, calls, [], max_loss_usd=500, target=130)
        self.assertEqual(ticket.right, "call")
        self.assertEqual(ticket.strike, 110)
        self.assertEqual(ticket.contracts, 12)
        self.assertEqual(ticket.payoff_at_target, ((130 - 110) * 100 - 0.4 * 100) * 12)


class LessonRules(unittest.TestCase):
    def test_pivot_example_from_lesson_18(self):
        levels = floor_pivots(120, 90, 100)
        self.assertAlmostEqual(levels["P"], 103.333333, places=4)
        self.assertAlmostEqual(levels["S1"], 86.666666, places=4)
        self.assertAlmostEqual(levels["R1"], 116.666666, places=4)
        self.assertAlmostEqual(levels["S2"], 73.333333, places=4)
        self.assertAlmostEqual(levels["R2"], 133.333333, places=4)

    def test_long_filter_matches_the_video_when_the_sector_is_technology(self):
        url = long_url("XLK")
        self.assertIn("fa_epsqoq_o15,fa_epsyoy_o25,sec_technology,sh_avgvol_o200", url)
        self.assertIn("ta_sma20_sa50,ta_sma200_sb50,ta_sma50_sa200", url)
        self.assertIn("o=-volume", short_url())
        self.assertNotIn("fa_eps", short_url())

    def test_review_counts_a_thirty_day_window(self):
        today = dt.date(2026, 11, 9)
        rows = [
            {"fecha": "2026-11-01", "evento": "objetivo"},
            {"fecha": "2026-11-02", "evento": "stop"},
            {"fecha": "2026-10-01", "evento": "objetivo"},
            {"fecha": "2026-11-03", "evento": "senal contraria"},
        ]
        report = review_trades(rows, today)
        self.assertEqual(report["objetivos"], 1)
        self.assertEqual(report["stops"], 1)
        self.assertEqual(report["cruces_contrarios"], 1)
        self.assertEqual(report["aciertos"], 0.5)
        self.assertTrue(report["dentro_de_40_a_60"])
        self.assertEqual(len(report["mandamientos"]), 10)

    def test_template_uses_the_visible_studies(self):
        chart = layout()
        self.assertEqual(VOLUME_SMA_LENGTH, 50)
        self.assertEqual(chart["ventana"], "161 hours")
        self.assertIn("ATR 14.", chart["estudios_visibles"])
        self.assertTrue(any("oculto" in item for item in chart["estudios_ocultos"]))
        values = atr([10, 12, 11, 13], [9, 10, 10, 11], [9.5, 11, 10.5, 12], period=2)
        self.assertIsNotNone(values[-1])


def _ohlcv(closes: list[float], volume: float = 1_000_000, last_volume: float | None = None) -> Bars:
    opens = []
    highs = []
    lows = []
    volumes = []
    dates = []
    start = dt.date(2024, 1, 2)
    for index, close in enumerate(closes):
        opens.append(close - 0.2)
        highs.append(close + 0.8)
        lows.append(close - 0.8)
        volumes.append(last_volume if last_volume is not None and index == len(closes) - 1 else volume)
        dates.append(start + dt.timedelta(days=index))
    return Bars(dates, opens, highs, lows, list(closes), volumes)


def _long_closes() -> list[float]:
    closes = [100 + index * 0.3 for index in range(220)]
    for _ in range(10):
        closes.append(closes[-1] - 1.0)
    for step in (1.2, 1.6, 2.0, 2.4):
        closes.append(closes[-1] + step)
    return closes


def _short_closes() -> list[float]:
    closes = [200 - index * 0.3 for index in range(220)]
    for _ in range(10):
        closes.append(closes[-1] + 1.0)
    for step in (1.2, 1.6, 2.0, 2.4):
        closes.append(closes[-1] - step)
    return closes


if __name__ == "__main__":
    unittest.main()
