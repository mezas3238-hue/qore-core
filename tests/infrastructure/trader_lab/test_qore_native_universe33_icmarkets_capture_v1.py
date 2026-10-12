"""No-network tests for owner-defined 33-universe and safe broker preflight."""
import unittest
from types import SimpleNamespace

from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    GROUPS, M5_10Y, M5_7Y, M1_10Y, inventory, universe,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    classify_accounts, match_catalog,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    require_capture_candidate,
)


def acc(id=50, live=False, broker="IC Markets", explicit=True):
    item = SimpleNamespace(
        ctidTraderAccountId=id, isLive=live, brokerTitleShort=broker,
    )
    item.HasField = lambda attr: explicit and attr == "isLive"
    return item


class Universe33Tests(unittest.TestCase):
    def test_universe_exact_33_and_no_duplicates(self):
        self.assertEqual(len(universe()), 33)
        self.assertEqual(len(set(universe())), 33)

    def test_cohort_numbers(self):
        self.assertEqual({k: len(v) for k, v in GROUPS.items()}, {
            "indices": 3, "metals": 2, "fx_majors": 7,
            "fx_crosses_minors": 21
        })
        x = inventory()["counts"]
        self.assertEqual(
            (x["verified_m5_10y"], x["verified_m5_7y_partial"],
             x["m5_absent_from_selected_archives"], x["m5_needed_to_reach_10y_target"],
             x["verified_m1_10y"], x["m1_needed_to_reach_10y_target"]),
            (12, 2, 19, 21, 9, 24)
        )

    def test_eurjpy_usdchf_partial_but_not_absent(self):
        self.assertEqual(M5_7Y, frozenset({"EURJPY", "USDCHF"}))
        d = {x["symbol"]: x for x in inventory()["rows"]}
        for symbol in M5_7Y:
            self.assertEqual(d[symbol]["m5_status"], "EXISTING_M5_7Y_PARTIAL")
            self.assertTrue(d[symbol]["requires_m5_capture_or_extension"])

    def test_do_not_recapture_existing_M5(self):
        for symbol in M5_10Y:
            with self.assertRaisesRegex(ValueError, "EXISTING_10Y_M5"):
                require_capture_candidate(symbol, {symbol})

    def test_fx_crosses_not_silently_shrunk(self):
        self.assertEqual(len(GROUPS["fx_crosses_minors"]), 21)
        self.assertEqual(
            len([s for s in GROUPS["fx_crosses_minors"] if s not in M5_10Y and s not in M5_7Y]),
            18
        )

    def test_m1_is_subcohort_of_12(self):
        self.assertEqual(len(M1_10Y), 9)
        self.assertTrue(M1_10Y <= M5_10Y)

    def test_no_live_or_unproven_broker(self):
        for xs in ([acc(live=True)], [acc(broker="Another Broker")],
                   [acc(explicit=False)], [], [acc(), acc(id=51)]):
            with self.subTest(xs=xs):
                with self.assertRaises(ValueError):
                    classify_accounts(xs, 0)

    def test_ic_markets_demo_readonly_scope_accepted(self):
        self.assertEqual(classify_accounts([acc()], 0), (50, "IC Markets"))
        self.assertEqual(classify_accounts([acc(broker="IC Markets Global")], 1),
                         (50, "IC Markets Global"))

    def test_scope_outside_view_or_trade_fails(self):
        for scope in (-1, 2, None, True):
            with self.subTest(scope=scope):
                with self.assertRaises(ValueError):
                    classify_accounts([acc()], scope)

    def test_source_account_no_symbol_alias_automatic(self):
        reported = match_catalog([
            SimpleNamespace(symbolName="NZDUSD",symbolId=99,enabled=True),
            SimpleNamespace(symbolName="USTEC",symbolId=44,enabled=True)
        ])
        self.assertIn("NZDUSD", reported["available_exact"])
        self.assertIn("NAS100", reported["not_listed_or_inactive"])
        require_capture_candidate("NZDUSD", set(reported["available_exact"]))

    def test_duplicate_exact_symbol_is_fatal(self):
        sym = SimpleNamespace(symbolName="NZDUSD", symbolId=3, enabled=True)
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_BROKER_SYMBOL"):
            match_catalog([sym, sym])

    def test_unlisted_symbol_cannot_be_downloaded(self):
        with self.assertRaisesRegex(ValueError, "BROKER_SYMBOL_NOT_EXACT_ENABLED_MATCH"):
            require_capture_candidate("NZDUSD", set())

    def test_unknown_symbol_not_autoadmitted(self):
        with self.assertRaisesRegex(ValueError, "UNIVERSE33_OUT_OF_SCOPE"):
            require_capture_candidate("BTCUSD", {"BTCUSD"})

    def test_inactive_exact_symbol_not_eligible(self):
        outcome = match_catalog([SimpleNamespace(symbolName="NZDUSD",symbolId=99,enabled=False)])
        self.assertNotIn("NZDUSD", outcome["available_exact"])


if __name__ == "__main__":
    unittest.main()
