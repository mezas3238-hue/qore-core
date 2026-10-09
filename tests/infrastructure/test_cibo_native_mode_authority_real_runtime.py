"""Real Native MAX (not a forged sensor row) issues CIBO-owned QDLE mode.

Tests cognition decision-to-instruction origin, provenance, serialization and
per-signal sovereignty without running MT5 or mutating broker equity.
"""
from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal as D

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import TraderOpportunityEnvelope
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState, CorrelationState, LiquidityState,
    ProviderCondition, VolatilityState,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    run_native_maximum_intelligence,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)
from qore.infrastructure.cibo_native_mode_authority import (
    CiboNativeModeError, FRACTIONS, SOURCE,
    issue_native_sovereign_mode_instruction, native_mode_from_json,
)

AT = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _native():
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="native-real-max-r34",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=D("100"),
        stop_loss=D("99"),
        take_profit=D("103"),
        stop_loss_per_volume=D("10"),
        margin_per_volume=D("20"),
        volume_step=D(".01"),
        minimum_volume=D(".01"),
        maximum_volume=D("10"),
        decision_context=tuple(
            (f"ctx_native_{i:02d}", f"value-{i:02d}") for i in range(30)
        ),
    )
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=D(".10"),
        margin_utilization=D(".10"),
        drawdown_utilization=D(".05"),
        opportunity_count=1,
        position_path_adverse=False,
        evidence_stale=False,
    )
    consultation = consult_cibo_economic_faculties(
        decision_at=AT, opportunities=(opportunity,), regime_state=regime,
    )
    actual = run_native_maximum_intelligence(
        consultation=consultation, opportunities=(opportunity,),
        target=opportunity, regime_state=regime,
    )
    return opportunity, actual


class RealNativeModeAuthorityTest(unittest.TestCase):
    def test_actual_native_max_cognition_issues_bank_medium_or_attack_to_qdle(self):
        opportunity, actual = _native()
        emitted = issue_native_sovereign_mode_instruction(
            episode=actual.cognitive_episode,
            signal_fingerprint=opportunity.signal_fingerprint,
            trader_id=opportunity.trader_id.value,
            decided_at=AT,
            semantic_digest=actual.semantic_digest,
        )
        self.assertIn(emitted.mode, ("BANK", "MEDIUM", "ATTACK"))
        self.assertEqual(emitted.requested_risk_fraction_of_nav, FRACTIONS[emitted.mode])
        self.assertEqual(emitted.signal_fingerprint, opportunity.signal_fingerprint)
        self.assertEqual(emitted.trader_id, opportunity.trader_id.value)
        self.assertEqual(emitted.producer, SOURCE)
        self.assertTrue(emitted.qdle_lot_authority_only)
        self.assertFalse(emitted.broker_execution_authorized)
        self.assertEqual(emitted.scenario_count, 4)
        self.assertEqual(emitted.calibration_confidence,
                         actual.cognitive_episode.calibration.confidence_band)
        self.assertEqual(native_mode_from_json(emitted.as_json()), emitted)

    def test_native_cognitive_mode_source_seal_prevents_backdoor_attack_upscale(self):
        opportunity, actual = _native()
        inst = issue_native_sovereign_mode_instruction(
            episode=actual.cognitive_episode,
            signal_fingerprint=opportunity.signal_fingerprint,
            trader_id=opportunity.trader_id.value,
            decided_at=AT,
            semantic_digest=actual.semantic_digest,
        )
        raw = inst.as_json()
        changed = dict(raw, mode="ATTACK" if inst.mode != "ATTACK" else "BANK")
        with self.assertRaises(CiboNativeModeError):
            native_mode_from_json(changed)
        changed = dict(raw, broker_execution_authorized=True)
        with self.assertRaises(CiboNativeModeError):
            native_mode_from_json(changed)
        changed = dict(raw, semantic_digest="sha256:" + "f" * 64)
        with self.assertRaises(CiboNativeModeError):
            native_mode_from_json(changed)


if __name__ == "__main__":
    unittest.main()
