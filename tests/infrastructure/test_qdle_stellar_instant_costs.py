"""Stellar Instant cost split and JPY conversion: research tariffs, no LIVE."""
import unittest
from decimal import Decimal as D

from qore.infrastructure.qdle_stellar_instant_costs import (
    LEGACY_REPLAY_PROXY, GENERAL_RULES_PER_SIDE, STELLAR_HELP_OPEN_ONLY,
    estimate_per_lot_fees, jpy_quote_pip_value_usd_per_lot,
)


class StellarInstantCostTests(unittest.TestCase):
    def fee(self, symbol, model=STELLAR_HELP_OPEN_ONLY, price="4188.47",
            ndx=None):
        return estimate_per_lot_fees(
            symbol, entry_price=D(price), contract_size=D("100")
            if symbol == "XAUUSD" else D("10") if symbol == "NDX100" else D("100000"),
            model=model, legacy_ndx_fee_usd=ndx,
        )

    def test_forex_open_only_seven_each_symbol(self):
        for symbol in ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD"):
            with self.subTest(symbol=symbol):
                x = self.fee(symbol)
                self.assertEqual(x.opening_usd, D("7"))
                self.assertEqual(x.closing_usd, D("0"))
                self.assertEqual(x.total_usd * D(".01"), D(".07"))
                self.assertFalse(x.actual_mt5_account_verified)

    def test_gbpusd_matches_eurusd_costs_for_all_scenarios_and_5pct_modes(self):
        # A 100K USD-quoted FX lot is $10/pip for both EURUSD and GBPUSD.
        # Both pay the same per-lot tariff; volume and SL still depend on
        # each signal and available QORE risk/capital.
        pip_value_usd = D("100000") * D("0.0001")
        self.assertEqual(pip_value_usd, D("10"))
        for model in (STELLAR_HELP_OPEN_ONLY, GENERAL_RULES_PER_SIDE,
                      LEGACY_REPLAY_PROXY):
            eu = self.fee("EURUSD", model, price="1.11923")
            gb = self.fee("GBPUSD", model, price="1.32254")
            with self.subTest(model=model):
                self.assertEqual((eu.opening_usd, eu.closing_usd),
                                 (gb.opening_usd, gb.closing_usd))
                for budget in (D("0.75"), D("1.50"), D("3.00")):
                    loss_per_lot_to_10pip_stop = D("10") * pip_value_usd
                    self.assertEqual(
                        budget/(loss_per_lot_to_10pip_stop+eu.total_usd),
                        budget/(loss_per_lot_to_10pip_stop+gb.total_usd),
                    )

    def test_index_zero_both_legs(self):
        x = self.fee("NDX100")
        self.assertEqual((x.opening_usd, x.closing_usd), (D(0), D(0)))

    def test_xau_percentage_on_notional_at_open(self):
        x = self.fee("XAUUSD")
        expected = D("4188.47") * D("100") * D("0.000016")
        self.assertEqual(x.opening_usd, expected)
        self.assertEqual(x.closing_usd, D(0))

    def test_general_per_side_is_explicit_sensitivity(self):
        self.assertEqual(self.fee("EURUSD", GENERAL_RULES_PER_SIDE).total_usd, D("14"))
        x = self.fee("XAUUSD", GENERAL_RULES_PER_SIDE)
        self.assertEqual(x.total_usd, 2 * x.opening_usd)

    def test_legacy_20_index_different_from_published_zero(self):
        old = self.fee("NDX100", LEGACY_REPLAY_PROXY, ndx=D("20"))
        new = self.fee("NDX100")
        self.assertEqual(old.total_usd, D("20"))
        self.assertEqual(new.total_usd, D(0))

    def test_legacy_forex_cost_and_split(self):
        x = self.fee("GBPUSD", LEGACY_REPLAY_PROXY)
        self.assertEqual((x.opening_usd, x.closing_usd), (D("7"), D("7")))

    def test_broker_grid_risk_formula(self):
        # 1 pip loss $10/lot on EURUSD with 10 pips stop = $100/l;
        # cost $7 vs $14/lot. Both must enter all-in denominator.
        for mode_cap in (D(".75"), D("1.50"), D("3")):
            old = mode_cap / D("114")
            new = mode_cap / D("107")
            self.assertGreater(new, old)
            self.assertGreaterEqual(new, D(0))

    def test_jpy_conversion_epoch_spot(self):
        pip = jpy_quote_pip_value_usd_per_lot(
            contract_size=D("100000"), usd_jpy=D("158.337"))
        self.assertEqual(pip, D("1000") / D("158.337"))
        self.assertGreater(pip, D("6"))
        self.assertLess(pip, D("7"))

    def test_reject_invalid_tariff_inputs(self):
        with self.assertRaises(ValueError):
            self.fee("NDX100", LEGACY_REPLAY_PROXY)
        with self.assertRaises(ValueError):
            estimate_per_lot_fees("XAUUSD", entry_price=D("-1"),
                                  contract_size=D("100"), model=STELLAR_HELP_OPEN_ONLY)
        with self.assertRaises(ValueError):
            self.fee("UNKNOWN")
        with self.assertRaises(ValueError):
            jpy_quote_pip_value_usd_per_lot(
                contract_size=D("100000"), usd_jpy=D("0"))


if __name__ == "__main__":
    unittest.main()
