"""Synthetic H4 carry gate tests; no real forward prices or economic outcomes."""
import copy
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_fx_carry_pit_gate_v1 as fx


def specimen():
    quotes=[]
    for i,sym in enumerate(fx.FX28):
        # Deliberately artificial spot/forward quote premiums, never broker data
        carry=(i-14)*0.00012
        quotes.append({
            "symbol":sym,
            "observed_at_utc":"2022-06-30T22:00:00+00:00",
            "received_at_utc":"2022-06-30T22:00:01+00:00",
            "decision_at_utc":"2022-07-01T00:10:00+00:00",
            "maturity_utc":"2022-08-01T00:00:00+00:00",
            "spot_bid":"1.09995",
            "spot_ask":"1.10005",
            "forward_bid":str(1.1*(1-carry)-0.00005),
            "forward_ask":str(1.1*(1-carry)+0.00005),
            "tenor":"1M",
            "quote_basis":"QUOTE_PER_ONE_BASE",
            "provider_id":"SYNTHETIC_UNIT_TEST_NOT_MARKET_DATA",
            "source_evidence_sha256":"a"*64,
            "license_read_authorized":True,
        })
    return {
        "schema":fx.SCHEMA,
        "quotes":quotes,
        "source_license_scope":"PRIVATE_RESEARCH_READ_ONLY",
    }


class H4CarryPIT(unittest.TestCase):
    def test_frozen_eight_currencies_28_crosses(self):
        fx.validate_universe()
        self.assertEqual(len(fx.FX28),28)
        self.assertEqual(len(fx.CURRENCIES),8)
        self.assertEqual(len({frozenset((s[:3],s[3:])) for s in fx.FX28}),28)

    def test_unavailable_real_rates_never_marked_zero_or_backtest(self):
        report=fx.preflight()
        self.assertEqual(report["status"],"BLOCKED_NO_AUTHENTIC_PIT_CARRY_SOURCE")
        self.assertEqual(report["verified_historical_one_month_forward_quote_sets_28_of_28"],0)
        self.assertIsNone(report["claimed_sharpe"])
        self.assertFalse(report["monthly_portfolio_backtest_executed"])

    def test_pit_complete_rank_top6_bottom6_and_currency_exposure(self):
        q=fx.rank_one_month(specimen())
        self.assertEqual(q["input_quotes_seen"],28)
        self.assertEqual(q["long_6_pairs"],list(reversed(fx.FX28[-6:])))
        self.assertEqual(q["short_6_pairs"],list(reversed(fx.FX28[:6])))
        self.assertEqual(len(q["long_6_pairs"]),6)
        self.assertEqual(len(q["short_6_pairs"]),6)
        self.assertAlmostEqual(sum(q["nominal_base_quote_currency_exposure"].values()),0.)
        self.assertFalse(q["FX_carry_economic_backtest_performed"])
        self.assertFalse(q["source_origin_authenticated_by_external_license_holder"])
        self.assertFalse(q["broker_net_authorized"])

    def test_reject_fake_F_from_spot_only(self):
        q=specimen()
        for record in q["quotes"]:
            del record["forward_bid"]
        with self.assertRaisesRegex(ValueError,"PIT_ROW_SCHEMA_EXACT"):
            fx.rank_one_month(q)

    def test_reject_missing_one_pair(self):
        q=specimen()
        q["quotes"].pop()
        with self.assertRaisesRegex(ValueError,"MISSING_SOME_OF_28"):
            fx.rank_one_month(q)

    def test_reject_duplicate_pair_instead_of_backfill(self):
        q=specimen()
        q["quotes"][3]=dict(q["quotes"][2])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OR_MISSING"):
            fx.rank_one_month(q)

    def test_reject_quote_arriving_after_decision(self):
        q=specimen()
        q["quotes"][1]["received_at_utc"]="2022-07-02T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD"):
            fx.rank_one_month(q)

    def test_reject_stale_data(self):
        q=specimen()
        for item in q["quotes"]:
            item["observed_at_utc"]="2022-06-18T22:00:00+00:00"
            item["received_at_utc"]="2022-06-18T22:00:01+00:00"
        with self.assertRaisesRegex(ValueError,"STALE"):
            fx.rank_one_month(q)

    def test_reject_embargo_decision_date(self):
        q=specimen()
        for item in q["quotes"]:
            item["observed_at_utc"]="2024-09-17T22:00:00+00:00"
            item["received_at_utc"]="2024-09-17T22:00:01+00:00"
            item["decision_at_utc"]="2024-09-18T00:10:00+00:00"
            item["maturity_utc"]="2024-10-18T00:10:00+00:00"
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_OR_INVALID_HOLDOUT"):
            fx.rank_one_month(q)

    def test_reject_untested_current_broker_swap_as_quote(self):
        q=specimen()
        q["quotes"][0]["tenor"]="OVERNIGHT"
        with self.assertRaisesRegex(ValueError,"BAD_ORIENTATION_OR_TENOR"):
            fx.rank_one_month(q)

    def test_reject_bad_forward_spread_and_maturity(self):
        q=specimen()
        q["quotes"][5]["forward_ask"]="0.5"
        with self.assertRaisesRegex(ValueError,"NEGATIVE_QUOTED_SPREAD"):
            fx.rank_one_month(q)
        q=specimen()
        q["quotes"][5]["maturity_utc"]="2022-07-04T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError,"MATURITY_NOT_1M"):
            fx.rank_one_month(q)

    def test_reject_unlicensed_or_unknown_provider(self):
        q=specimen()
        q["quotes"][3]["license_read_authorized"]=False
        with self.assertRaisesRegex(ValueError,"LICENSE_NOT_VERIFIED"):
            fx.rank_one_month(q)
        q=specimen()
        q["quotes"][3]["source_evidence_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_EVIDENCE_SHA_MISSING"):
            fx.rank_one_month(q)

    def test_reject_non_utc_or_corrupt_quote(self):
        q=specimen()
        q["quotes"][4]["observed_at_utc"]="2022-06-30T22:00:00+02:00"
        with self.assertRaisesRegex(ValueError,"TIMESTAMP_MUST_BE_UTC"):
            fx.rank_one_month(q)
        q=specimen()
        q["quotes"][4]["spot_bid"]="NaN"
        with self.assertRaisesRegex(ValueError,"NONPOSITIVE_OR_NONFINITE"):
            fx.rank_one_month(q)

    def test_gate_never_exports_raw_rates(self):
        with tempfile.TemporaryDirectory() as p:
            import json
            out=Path(p)/"gate.json"
            out.write_text(json.dumps(fx.preflight()))
            result=json.loads(out.read_text())
            self.assertNotIn("quotes",result)
            self.assertNotIn("forward_bid",result)
            self.assertFalse(result["holdout_opened"])


if __name__=="__main__":
    unittest.main()
