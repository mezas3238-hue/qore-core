"""P0 Native MAX paper manager: sensor causality and no Trader-control leakage."""
from __future__ import annotations

import copy
import unittest

from qore.infrastructure.cibo_p0_native_cognitive_management import (
    NativeCognitiveManagementError, native_sensor_management_plan,
)
from scripts.cibo_p0_native_max_manager_advisory_3368 import (
    NativeManagementEvidenceError, classify_native_advisory,
)


def native_row(*, confidence=85, abstain="False", sufficiency="sufficient",
               disposition="COGNITIVE_BLOCK"):
    def sensor(code, values):
        return {"component_code": code, "native_output_consumed": True,
                "input_metrics": [], "output_metrics": list(values.items())}
    return {
        "signal_fingerprint": "sig-1",
        "trader_id": "trader-1",
        "decided_at": "2022-01-01T10:00:00+00:00",
        "native_maximum_intelligence": True,
        "full_semantics_consumed": True,
        "outcome_used_for_predecision": False,
        "external_ai_call_count": 0,
        "semantic_digest": "sha256:" + "e"*64,
        "capital_disposition": disposition,
        "cognitive_sensors": [
            sensor("CALIBRATION", {
                "confidence_band": str(confidence),
                "abstention_required": abstain,
                "note": "native-causal-state-bounded-confidence"}),
            sensor("REASONING_ROUTING", {"decision": "DEEP_REASONING"}),
            sensor("SCENARIO_ENGINE", {"scenario_count": "4"}),
            sensor("METACOGNITION", {"evidence_sufficiency": sufficiency}),
            sensor("CAUSAL_REASONING", {"status": "SUPPORTED"}),
            sensor("EXECUTIVE_SYNTHESIS", {
                "directive": "CAUTIOUS_MONITOR", "uncertainty": "BOUNDED"}),
        ],
    }


class NativeCognitivePaperManagerTest(unittest.TestCase):
    def test_legacy_blocks_cannot_select_management_mode(self):
        original = {"signal_fingerprint":"sig-1", "trader_id":"trader-1",
                    "market_decision_at":"2022-01-01T10:00:00+00:00"}
        actions=[]
        for old_gate in ("COGNITIVE_BLOCK", "CAPITAL_BLOCK", "RISK_REVIEW_READY"):
            decision = classify_native_advisory(native_row(disposition=old_gate), original)
            self.assertTrue(decision["trader_signal_received"])
            self.assertFalse(decision["admission_gate_applied"])
            self.assertEqual(decision["manager_mode_SHADOW_from_native_cognitive_sensors"], "ATTACK")
            self.assertEqual(decision["manager_risk_fraction_of_nav_SHADOW"], "0.0500")
            actions.append((decision["manager_mode_SHADOW_from_native_cognitive_sensors"],
                            decision["manager_risk_fraction_of_nav_SHADOW"]))
        self.assertEqual(len(set(actions)), 1)

    def test_real_cognitive_sensor_perturbation_changes_qdle_risk_intent(self):
        low=native_sensor_management_plan(native_row(confidence=20))
        medium=native_sensor_management_plan(native_row(confidence=55))
        high=native_sensor_management_plan(native_row(confidence=85))
        self.assertEqual([x["mode"] for x in (low, medium, high)],
                         ["BANK", "MEDIUM", "ATTACK"])
        self.assertEqual([x["requested_risk_fraction_of_current_qore_nav"]
                          for x in (low, medium, high)],
                         ["0.0125", "0.0250", "0.0500"])
        self.assertNotEqual(low["exit_policy_SHADOW"], high["exit_policy_SHADOW"])
        self.assertFalse(high["native_disposition_used_for_policy"])

    def test_causal_native_sensor_risk_changes_real_qdle_physical_quote(self):
        # Same broker price, fees, margin and USD60 NAV; ONLY the native
        # cognitive sensor confidence changes the risk request.
        import tempfile
        from datetime import datetime, timezone
        from decimal import Decimal as D
        from pathlib import Path
        from qore.infrastructure.qore_dynamic_lot_engine import (
            BrokerValuation, QDLE, QDLEAccount, QDLEIntent, QDLESymbol,
        )
        at = datetime(2026, 10, 9, 10, tzinfo=timezone.utc)
        class PaperBroker:
            def value(self, spec, intent, now):
                return BrokerValuation(D("100"), D("1000"), now, "SYNTHETIC_TEST_ONLY")
            def check_volume(self, spec, intent, lots):
                return None
        results = []
        for confidence in (20, 55, 85):
            fraction = D(native_sensor_management_plan(
                native_row(confidence=confidence)
            )["requested_risk_fraction_of_current_qore_nav"])
            cap = D("60") * fraction
            with tempfile.TemporaryDirectory() as td:
                q = QDLE(Path(td) / "physical.sqlite", PaperBroker())
                q.publish_account(QDLEAccount(
                    "paper", "FundedNext", "USD", 1, at, D("2000"), D("2000"),
                    D("1900"), D("60"), D("60"), D("0"), D("60")))
                q.publish_symbol(QDLESymbol(
                    "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"), D("0"),
                    D(".00001"), D("1"), D("100000"), "USD", D("14"),
                    "SYNTHETIC_TEST_ONLY", at))
                instruction = QDLEIntent(
                    request_id=f"sig-{confidence}", trader_id="trader-1",
                    symbol="EURUSD", side="BUY",
                    entry_price=D("1.10000"), stop_price=D("1.09000"),
                    requested_risk_usd=cap, sizing_cap_usd=cap,
                    cibo_compound_cap_usd=cap, portfolio_cap_usd=D("60"),
                    leverage_cap_lots=D("40"), margin_cap_usd=D("1900"),
                    source_lane="SOVEREIGN_BANK", slippage_usd_per_lot=D("0"),
                    expected_account_sequence=1, methodology_min_lots=D(".01"),
                )
                quote = q.reserve_for_trader(instruction, now=at)
                results.append(quote.lots)
                self.assertLessEqual(quote.total_risk_usd, cap)
        self.assertEqual(results, [D("0"), D(".01"), D(".02")])

    def test_cognitive_abstention_is_not_an_admission_veto(self):
        r=native_sensor_management_plan(native_row(
            confidence=90, abstain="True"))
        self.assertEqual(r["mode"], "BANK")
        self.assertEqual(r["requested_risk_fraction_of_current_qore_nav"], "0.0125")
        self.assertFalse(r["exit_policy_actually_executed"])
        self.assertEqual(native_sensor_management_plan(native_row(
            confidence=90, sufficiency="insufficient"))["mode"], "BANK")

    def test_fail_closed_when_sensor_missing_invalid_or_future_outcome_used(self):
        for code in ("CALIBRATION", "METACOGNITION", "CAUSAL_REASONING"):
            with self.subTest(code=code):
                raw=native_row()
                raw["cognitive_sensors"]=[x for x in raw["cognitive_sensors"]
                                          if x["component_code"] != code]
                with self.assertRaises(NativeCognitiveManagementError):
                    native_sensor_management_plan(raw)
        for value in ("NaN","Infinity","101","-1"):
            with self.subTest(confidence=value):
                with self.assertRaises(NativeCognitiveManagementError):
                    native_sensor_management_plan(native_row(confidence=value))
        row=native_row()
        row["outcome_used_for_predecision"]=True
        original={"signal_fingerprint":"sig-1", "trader_id":"trader-1",
                  "market_decision_at":"2022-01-01T10:00:00+00:00"}
        with self.assertRaises(NativeManagementEvidenceError):
            classify_native_advisory(row, original)


if __name__ == "__main__":
    unittest.main()
