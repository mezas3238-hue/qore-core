"""No-network tests for owner-defined 33-universe and safe broker preflight."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    GROUPS, M5_10Y, M5_7Y, M1_10Y, inventory, universe,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    _ic_markets_label, classify_accounts, match_catalog, select_complete_credential_bundle,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    _ReadOnlyIcMarketsHistoryClient, _history_scope_allowed,
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

    def test_optional_broker_short_title_needs_second_stage_proof(self):
        account = acc(broker="")
        self.assertEqual(classify_accounts([account], 0), (50, None))
        with self.assertRaisesRegex(ValueError, "REQUIRE_EXACT_ONE"):
            classify_accounts([account, acc(id=51, broker="")], 0)

    def test_optional_broker_unlabeled_not_selected_over_known_ic_markets(self):
        value = classify_accounts([
            acc(id=50, broker=""),
            acc(id=52, broker="IC Markets"),
        ], 0)
        self.assertEqual(value, (52, "IC Markets"))

    def test_spoofed_broker_name_rejected(self):
        for label in ("Not IC Markets", "My IC Markets", "another broker"):
            self.assertFalse(_ic_markets_label(label))
        for label in ("IC Markets", "ICMarkets", "IC Markets Global"):
            self.assertTrue(_ic_markets_label(label))

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

    def test_history_client_accepts_view_scope_without_trading_permission(self):
        self.assertTrue(_history_scope_allowed(0))
        self.assertTrue(_history_scope_allowed(1))
        for unsafe in (None, -1, 2, True, "0"):
            self.assertFalse(_history_scope_allowed(unsafe))
        self.assertNotIn("ProtoOANewOrderReq", _ReadOnlyIcMarketsHistoryClient.connect_and_authenticate.__code__.co_consts)

    def test_refresh_is_denied_in_research_only_adapter(self):
        # No SDK session instantiated; the override is synchronous and pure.
        result = _ReadOnlyIcMarketsHistoryClient._refresh_tokens(None)
        self.assertIn("REAUTH_REQUIRED", str(result.error))

    def test_mixed_oauth_bundles_refused(self):
        # Both incomplete even though their union would be complete.
        with patch.dict("os.environ", {
            "QORE_CTRADER_DEMO_CLIENT_ID": "a",
            "QORE_CTRADER_DEMO_CLIENT_SECRET": "b",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN": "",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN": "",
            "QORE_CTRADER_CLIENT_ID": "",
            "QORE_CTRADER_CLIENT_SECRET": "",
            "QORE_CTRADER_ACCESS_TOKEN": "c",
            "QORE_CTRADER_REFRESH_TOKEN": "d",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "NO_COMPLETE_CTRADER_OAUTH_BUNDLE"):
                select_complete_credential_bundle()

    def test_complete_demo_bundle_wins_as_single_grant(self):
        with patch.dict("os.environ", {
            "QORE_CTRADER_DEMO_CLIENT_ID": "demo-id",
            "QORE_CTRADER_DEMO_CLIENT_SECRET": "demo-secret",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN": "demo-access",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN": "demo-refresh",
            "QORE_CTRADER_CLIENT_ID": "generic-id",
            "QORE_CTRADER_CLIENT_SECRET": "generic-secret",
            "QORE_CTRADER_ACCESS_TOKEN": "generic-access",
            "QORE_CTRADER_REFRESH_TOKEN": "generic-refresh",
        }, clear=True):
            self.assertEqual(select_complete_credential_bundle(), "DEMO_ALIAS_BUNDLE")
            import os
            self.assertEqual(os.environ["QORE_CTRADER_ACCESS_TOKEN"], "demo-access")
            self.assertEqual(os.environ["QORE_CTRADER_CLIENT_ID"], "demo-id")

    def test_unknown_symbol_not_autoadmitted(self):
        with self.assertRaisesRegex(ValueError, "UNIVERSE33_OUT_OF_SCOPE"):
            require_capture_candidate("BTCUSD", {"BTCUSD"})

    def test_inactive_exact_symbol_not_eligible(self):
        outcome = match_catalog([SimpleNamespace(symbolName="NZDUSD",symbolId=99,enabled=False)])
        self.assertNotIn("NZDUSD", outcome["available_exact"])


if __name__ == "__main__":
    unittest.main()
