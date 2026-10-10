"""Integrated CIBO Soberano Native MAX -> four engines -> physical QDLE P0 tests.

All tests are deliberately synthetic and prohibit LIVE/real MT5 assertions.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.cibo_native_sovereign_qdle import (
    CiboSovereignQdleBridgeError,
    apply_native_qdle_risk_cap,
    bind_native_max_receipt,
)
from qore.infrastructure.cibo_p0_native_cognitive_management import native_sensor_management_plan
from qore.infrastructure.cibo_native_mode_authority import SOURCE as NATIVE_SOURCE, native_mode_from_json
from qore.infrastructure.cibo_sovereign_integration import administer_native_cibo_qdle_shadow
from qore.infrastructure.cibo_trade_ops_director import Stage
from qore.infrastructure.qore_dynamic_lot_engine import QDLE, QDLEIntent
from test_cibo_p0_native_cognitive_management import native_row
from test_cibo_sovereign_integration_p0 import T, cibo, observation, qdle, valued_state


def native(confidence=85, disposition="COGNITIVE_BLOCK"):
    r=native_row(confidence=confidence, disposition=disposition)
    r.update(signal_fingerprint="signal-A", trader_id="trader-A",
             decided_at=T.isoformat())
    # Synthetic *test* native instruction: same canonical sealed schema that
    # genuine CIBO Native MAX publishes from typed cognition in production.
    # This fixture is not an authenticated source or proof of a real order.
    import hashlib
    import json
    plan = native_sensor_management_plan(r)
    fields = dict(
        signal_fingerprint=r["signal_fingerprint"],
        trader_id=r["trader_id"],
        decided_at=r["decided_at"],
        semantic_digest=r["semantic_digest"],
        mode=plan["mode"],
        requested_risk_fraction_of_nav=plan["requested_risk_fraction_of_current_qore_nav"],
        exit_policy=[[k, v] for k,v in plan["exit_policy_SHADOW"].items()],
        calibration_confidence=int(confidence),
        abstention_required=False,
        scenario_count=4,
        producer=NATIVE_SOURCE,
        qdle_lot_authority_only=True,
        broker_execution_authorized=False,
    )
    digest = "sha256:" + hashlib.sha256(
        json.dumps(fields,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    r["native_mode_instruction"] = dict(fields, decision_digest=digest)
    return r


class TestCiboNativeSovereignQdleP0(unittest.TestCase):
    def _run(self, confidence=85, *, old_gate="COGNITIVE_BLOCK",
             cibo_instruction=None, observed=None):
        with tempfile.TemporaryDirectory() as tmp:
            engine=qdle(Path(tmp)/"qdle.sqlite")
            return administer_native_cibo_qdle_shadow(
                state=valued_state(),
                native_receipt=native(confidence, old_gate),
                cibo=cibo_instruction if cibo_instruction is not None else cibo(),
                observation=observed if observed is not None else observation(),
                qdle=engine, event_id="sovereign-funded", at=T,
                broker_min_lot=D(".01"), broker_lot_step=D(".01"),
            )

    def test_native_mode_instruction_roundtrip_and_tamper_protection(self):
        direct = native(85)
        parsed = native_mode_from_json(direct["native_mode_instruction"])
        self.assertEqual(parsed.mode, "ATTACK")
        self.assertEqual(parsed.as_json(), direct["native_mode_instruction"])
        corrupt = dict(direct)
        corrupt["native_mode_instruction"] = dict(
            direct["native_mode_instruction"], mode="BANK"
        )
        with self.assertRaises(ValueError):
            bind_native_max_receipt(
                native_receipt=corrupt, cibo=cibo(), observation=observation(),
            )
        no_instruction = dict(direct)
        del no_instruction["native_mode_instruction"]
        legacy = bind_native_max_receipt(
            native_receipt=no_instruction, cibo=cibo(), observation=observation(),
        )
        self.assertFalse(legacy["native_runtime_mode_instruction_consumed"])

    def test_native_evidence_controls_real_physical_qdle_lot(self):
        results=[self._run(level) for level in (20,55,85)]
        self.assertEqual([r.funding.receipt.lots for r in results],
                         [D("0"),D(".01"),D(".02")])
        self.assertEqual([r.native_mode for r in results],
                         ["BANK","MEDIUM","ATTACK"])
        self.assertEqual([r.native_risk_request_usd for r in results],
                         [D(".75"),D("1.5"),D("3")])
        self.assertEqual([r.funding.state.stage for r in results],
                         [Stage.UNFUNDABLE, Stage.ECONOMICALLY_FUNDED,
                          Stage.ECONOMICALLY_FUNDED])
        for result in results:
            self.assertEqual(result.funding.state.filled_lots, D(0))
            self.assertFalse(result.real_mt5_fill_proven)
            self.assertFalse(result.live_authorized)
            self.assertFalse(result.funding.real_mt5_fill_proven)
            self.assertEqual(len(result.prepared.votes),4)
            self.assertTrue(result.cognitive_risk_reaches_physical_qdle)
            self.assertLessEqual(result.funding.receipt.all_in_risk_usd,
                                 result.native_risk_request_usd)

    def test_legacy_cognitive_capital_blocks_are_not_admission_gates(self):
        result=[self._run(old_gate=x) for x in (
            "COGNITIVE_BLOCK","CAPITAL_BLOCK","RISK_REVIEW_READY")]
        self.assertEqual([r.funding.receipt.lots for r in result],
                         [D(".02")]*3)
        self.assertTrue(all(r.funding.state.stage is Stage.ECONOMICALLY_FUNDED
                            for r in result))

    def test_explicit_cibo_sovereign_budget_and_lane_still_bind(self):
        result=self._run(85,cibo_instruction=cibo(risk="1.5"))
        self.assertEqual(result.funding.receipt.lots,D(".01"))
        self.assertEqual(result.native_risk_request_usd,D("1.5"))
        self.assertEqual(result.funding.receipt.source_lane,"SOVEREIGN_BANK")
        zero=self._run(85,cibo_instruction=cibo(risk="0"))
        self.assertEqual(zero.funding.receipt.lots,D(0))
        self.assertEqual(zero.funding.state.stage,Stage.UNFUNDABLE)

    def test_native_causality_epoch_identity_and_digest_failure_is_terminal(self):
        row=native()
        row["signal_fingerprint"]="different"
        with self.assertRaisesRegex(CiboSovereignQdleBridgeError,"identity"):
            bind_native_max_receipt(native_receipt=row,cibo=cibo(),
                                    observation=observation())
        row=native()
        row["decided_at"]=(T+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(CiboSovereignQdleBridgeError,"future"):
            bind_native_max_receipt(native_receipt=row,cibo=cibo(),
                                    observation=observation())
        row=native()
        row["semantic_digest"]="sha256:invalid"
        with self.assertRaisesRegex(CiboSovereignQdleBridgeError,"provenance"):
            bind_native_max_receipt(native_receipt=row,cibo=cibo(),
                                    observation=observation())
        row=native()
        row["outcome_used_for_predecision"]=True
        with self.assertRaisesRegex(CiboSovereignQdleBridgeError,"provenance"):
            bind_native_max_receipt(native_receipt=row,cibo=cibo(),
                                    observation=observation())

    def test_no_cibo_instruction_or_incomplete_economic_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(CiboSovereignQdleBridgeError,"instruction"):
                administer_native_cibo_qdle_shadow(
                    state=valued_state(),native_receipt=native(),
                    cibo=None, observation=observation(),
                    qdle=qdle(Path(tmp)/"broker.sqlite"),
                    event_id="no-authority",at=T,
                    broker_min_lot=D(".01"),broker_lot_step=D(".01"))
        with self.assertRaises(ValueError):
            self._run(observed=observation(broker_fees_complete=False))
        with self.assertRaises(ValueError):
            self._run(cibo_instruction=cibo(source_lane="PORTFOLIO_CUSHION"))

    def test_trader_control_cashflows_cannot_activate_compound_loss_haircut(self):
        from qore.infrastructure.cibo_four_motor_policy import ReconciledQoreCashflow
        from test_cibo_sovereign_integration_p0 import SHA
        old_losses = (ReconciledQoreCashflow(
            "REPLAY_SETTLED:old-trader-control",
            T-timedelta(seconds=1), D("-1"), SHA, True,
        ),)
        with self.assertRaisesRegex(CiboSovereignQdleBridgeError, "CONTROL cashflow"):
            self._run(observed=observation(reconciled_cashflows=old_losses))
        managed_losses = (ReconciledQoreCashflow(
            "CIBO_MANAGED_SETTLED:authentic-test",
            T-timedelta(seconds=1), D("-1"), SHA, True,
        ),)
        output = self._run(observed=observation(reconciled_cashflows=managed_losses))
        self.assertIn(output.funding.state.stage, (Stage.ECONOMICALLY_FUNDED,Stage.UNFUNDABLE))

    def test_cognitive_cap_cannot_increase_any_original_motor_budget(self):
        plan=native_sensor_management_plan(native(85))
        original=self._run(85,cibo_instruction=cibo(risk="1.5")).prepared.intent
        limited=apply_native_qdle_risk_cap(intent=original,qore_nav_usd=D("60"),
                                           native_plan=plan)
        self.assertLessEqual(limited.requested_risk_usd,original.requested_risk_usd)
        self.assertLessEqual(limited.sizing_cap_usd,original.sizing_cap_usd)
        self.assertLessEqual(limited.cibo_compound_cap_usd,original.cibo_compound_cap_usd)
        with self.assertRaisesRegex(CiboSovereignQdleBridgeError,"research plan"):
            apply_native_qdle_risk_cap(
                intent=original,qore_nav_usd=D("60"),
                native_plan=dict(plan,native_disposition_used_for_policy=True))


if __name__=="__main__":
    unittest.main()
