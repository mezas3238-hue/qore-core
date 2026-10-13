"""Six-root futures M0 source-contract tests: strictly synthetic, no licensed prices."""
from __future__ import annotations

import unittest

from qore.infrastructure.trader_lab import qore_futures_a_m0_native_contract_source_gate_v1 as gate

FAKE_HASH="1"*64


def manifest(**updates):
    m={
        "provider":"SYNTHETIC_TEST_NOT_CME_ENTITLEMENT",
        "dataset_id":"TEST_EXCHANGE_NATIVE_CONTRACT_LEVEL_EOD",
        "licensed_internal_research":False,
        "license_receipt_sha256":FAKE_HASH,
        "original_source_sha256":FAKE_HASH,
        "authentic_exchange_contracts":False,
        "historical_bid_ask_or_fills_supported":False,
        "settlement_publication_asof_documented":False,
        "real_contract_specifications_documented":False,
        "coverage_2012_2024_verified":False,
        "broker_exchange_clearing_cost_schedule_verified":False,
    }
    m.update(updates)
    return m


def leg(root,index,settle="17.50"):
    return {
        "root":root,
        "venue":gate.ROOT_EXCHANGES[root],
        "native_contract_id":f"{root}{'M' if index==0 else 'N'}2020",
        "expiration_month":"2020-06" if index==0 else "2020-07",
        "trade_date":"2020-04-20",
        "settlement_value":settle,
        "settlement_published_at_utc":"2020-04-21T03:30:00Z",
        "volume":105 if index==0 else 15,
        "volume_published_at_utc":"2020-04-21T04:10:00Z",
        "open_interest":3045 if index==0 else 1234,
        "open_interest_published_at_utc":"2020-04-21T06:00:00Z",
        "exchange_first_notice_date":None if root in ("CL","NG") else ("2020-05-01" if index==0 else "2020-06-01"),
        "risk_liquidation_cutoff_date":"2020-05-01" if index==0 else "2020-06-01",
        "last_trade_date":"2020-05-30" if index==0 else "2020-06-30",
        "contract_multiplier":"1000",
        "minimum_tick":"0.01",
        "source_row_sha256":FAKE_HASH,
    }


def valid_envelope():
    return {
        "dataset_manifest":manifest(),
        "decision_at_utc":"2020-04-21T13:30:00Z",
        "sample_curves":[[leg(root,0),leg(root,1)] for root in gate.ROOT_EXCHANGES],
    }


class TestM0NativeContract(unittest.TestCase):
    def test_six_roots_are_fixed_three_sectors(self):
        self.assertEqual(gate.ROOT_EXCHANGES,{
            "CL":"NYMEX","NG":"NYMEX","GC":"COMEX","HG":"COMEX",
            "ZC":"CBOT","ZS":"CBOT",
        })

    def test_synthetic_all_six_pass_but_cannot_certify_data_or_trader(self):
        result=gate.inspect_local_envelope(valid_envelope())
        self.assertEqual(result["sample_leg_count"],12)
        self.assertFalse(result["source_ready_for_prereg"])
        self.assertFalse(result["authentic_entitlement_confirmed_by_QORE"])
        self.assertFalse(result["full_history_PnL_or_Sharpe_calculated"])
        self.assertFalse(result["economic_holdout_opened"])
        self.assertEqual(result["traders_certified"],0)

    def test_self_asserted_license_flags_never_count_as_license_review(self):
        x=valid_envelope()
        x["dataset_manifest"]=manifest(**{
            k:True for k in (
                "licensed_internal_research","authentic_exchange_contracts",
                "historical_bid_ask_or_fills_supported",
                "settlement_publication_asof_documented",
                "real_contract_specifications_documented","coverage_2012_2024_verified",
                "broker_exchange_clearing_cost_schedule_verified",
            )
        })
        result=gate.inspect_local_envelope(x)
        self.assertTrue(result["manifest_claims_complete"])
        self.assertFalse(result["manifest_independent_license_or_raw_custody_validation"])
        self.assertFalse(result["source_ready_for_prereg"])

    def test_negative_wti_price_is_legal_for_contract_deltas_no_log(self):
        a=leg("CL",0,settle="-37.63")
        r=gate.validate_contract_row(a)
        self.assertLess(r.settle,0)
        self.assertEqual(gate.validate_two_pats_native_curve(
            [a,leg("CL",1)],"2020-04-21T13:30:00Z")["PnL_calculated"],False)

    def test_same_day_settlement_signal_fails(self):
        with self.assertRaisesRegex(ValueError,"SAME_DAY_SETTLEMENT"):
            gate.validate_two_pats_native_curve(
                [leg("CL",0),leg("CL",1)],"2020-04-20T23:00:00Z")

    def test_next_day_before_settlement_publication_fails(self):
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_PUBLICATION"):
            gate.validate_two_pats_native_curve(
                [leg("GC",0),leg("GC",1)],"2020-04-21T02:00:00Z")

    def test_oi_late_even_when_settlement_available_fails(self):
        with self.assertRaisesRegex(ValueError,"LOOKAHEAD_PUBLICATION"):
            gate.validate_two_pats_native_curve(
                [leg("GC",0),leg("GC",1)],"2020-04-21T04:30:00Z")

    def test_delivery_first_notice_must_be_avoided(self):
        with self.assertRaisesRegex(ValueError,"ROLL_CUTOFF"):
            gate.validate_two_pats_native_curve(
                [leg("ZC",0),leg("ZC",1)],"2020-05-01T13:00:00Z")

    def test_exchange_notice_may_follow_last_trade_for_energy(self):
        row=leg("CL",0)
        row["exchange_first_notice_date"]="2020-06-01"
        row["last_trade_date"]="2020-05-21"
        row["risk_liquidation_cutoff_date"]="2020-05-20"
        result=gate.validate_contract_row(row)
        self.assertGreater(result.exchange_first_notice,result.last_trade)
        self.assertLess(result.cutoff,result.last_trade)

    def test_broker_risk_cutoff_cannot_follow_last_trade_or_first_notice(self):
        row=leg("CL",0)
        row["risk_liquidation_cutoff_date"]="2020-06-01"
        with self.assertRaisesRegex(ValueError,"RISK_CUTOFF_AFTER_LAST_TRADE"):
            gate.validate_contract_row(row)
        row=leg("GC",0)
        row["risk_liquidation_cutoff_date"]="2020-05-02"
        with self.assertRaisesRegex(ValueError,"RISK_CUTOFF_AFTER_EXCHANGE_NOTICE"):
            gate.validate_contract_row(row)

    def test_bad_root_venue_is_not_proxied(self):
        row=leg("ZC",0)
        row["venue"]="NYMEX"
        with self.assertRaisesRegex(ValueError,"ROOT_VENUE"):
            gate.validate_contract_row(row)

    def test_identical_month_or_contract_cannot_form_curve(self):
        with self.assertRaisesRegex(ValueError,"NOT_TWO_DISTINCT"):
            gate.validate_two_pats_native_curve(
                [leg("HG",0),leg("HG",0)],"2020-04-21T13:30:00Z")

    def test_continuous_reference_not_native(self):
        r=leg("CL",0)
        r["native_contract_id"]="CL_CONT_ADJUSTED"
        with self.assertRaisesRegex(ValueError,"CONTINUOUS_OR_ROOT"):
            gate.validate_contract_row(r)

    def test_all_six_required_and_no_unauthorized_substitution(self):
        x=valid_envelope()
        x["sample_curves"].pop()
        with self.assertRaisesRegex(ValueError,"REQUIRE_SIX"):
            gate.inspect_local_envelope(x)
        y=valid_envelope()
        y["sample_curves"][0][0]["root"]="GC"
        with self.assertRaisesRegex(ValueError,"ROOT_VENUE_MISMATCH"):
            gate.inspect_local_envelope(y)

    def test_cutoff_embargo_any_price_from_2024_09_17_rejected(self):
        row=leg("GC",0)
        row["trade_date"]="2024-09-17"
        with self.assertRaisesRegex(ValueError,"HOLDOUT"):
            gate.validate_contract_row(row)

    def test_invalid_tick_multiplier_and_liquidity(self):
        row=leg("GC",0)
        row["minimum_tick"]="0"
        with self.assertRaisesRegex(ValueError,"DECIMAL_RANGE"):
            gate.validate_contract_row(row)
        row=leg("GC",0)
        row["contract_multiplier"]="NaN"
        with self.assertRaisesRegex(ValueError,"DECIMAL_RANGE"):
            gate.validate_contract_row(row)
        row=leg("GC",0)
        row["volume"]=0
        with self.assertRaisesRegex(ValueError,"UNTRADED_OR_ZERO"):
            gate.validate_two_pats_native_curve(
                [row,leg("GC",1)],"2020-04-21T13:30:00Z")

    def test_no_missing_license_receipt_hash(self):
        m=manifest(license_receipt_sha256="")
        with self.assertRaisesRegex(ValueError,"SHA256_LICENSE"):
            gate.validate_dataset_manifest(m)

    def test_missing_month_series_cannot_get_cash_pnl(self):
        x=leg("CL",0)
        x["settlement_value"]="9999999999999.99"
        self.assertTrue(gate.validate_contract_row(x).settle>0)
        # No return, no synthetic price differencing, no contract change PnL.
        self.assertNotIn("return",gate.validate_two_pats_native_curve(
            [x,leg("CL",1)],"2020-04-21T13:30:00Z"))

if __name__=="__main__":
    unittest.main()
