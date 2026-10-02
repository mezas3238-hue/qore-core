from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_cibo_read_only_facts import (
    build_cibo_read_only_shared_facts,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
    TraderSharedOpportunityAssessment,
    TraderSharedOpportunityDisposition,
)

NOW = datetime(2026, 9, 29, 21, 30, tzinfo=UTC)


def _snapshot() -> SharedTraderIntelligenceSnapshot:
    return SharedTraderIntelligenceSnapshot(
        snapshot_id="snapshot-001",
        observed_at=NOW,
        evidence_cutoff_at=NOW - timedelta(seconds=1),
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        market_family="METALS",
        trader_horizon="D1",
        world_state="RISK_ON",
        market_regime="TRENDING",
        macro_regime="DISINFLATIONARY",
        rates_state="FALLING",
        usd_state="WEAKENING",
        liquidity_state="NORMAL",
        volatility_state="NORMAL",
        commodity_state="METALS_FIRM",
        agricultural_state="INSUFFICIENT",
        cross_asset_state="COHERENT",
        relationship_coherence=SharedSupportState.STRONG,
        relationship_stability=SharedSupportState.ELEVATED,
        relationship_age_ms=1_000,
        directional_hypothesis=(
            SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        ),
        continuation_support=SharedSupportState.STRONG,
        reversal_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.LOW,
        positive_tail_support=SharedSupportState.ELEVATED,
        systemic_stress=SharedSupportState.LOW,
        regime_transition_state=SharedRegimeTransitionState.CONTINUATION,
        epistemic_state=SharedEpistemicState.PARTIALLY_KNOWN,
        uncertainty_bps=2500,
        confidence_bps=6500,
        confidence_calibration=(
            SharedConfidenceCalibrationState.UNCALIBRATED
        ),
        calibration_evidence_refs=(),
        data_quality_bps=9900,
        data_freshness_ms=200,
        causal_maturity="TEMPORAL_DEPENDENCY",
        supporting_evidence_refs=("fact:rates", "fact:usd"),
        contradicting_evidence_refs=(),
        missing_evidence=("missing:causal-certification",),
        provenance_refs=("world:001",),
        observation_horizon="H4",
        expected_validity_horizon="2D-5D",
        decay_horizon="24H",
    )


def _assessment(
    disposition: TraderSharedOpportunityDisposition,
    *,
    methodology_validated: bool,
) -> TraderSharedOpportunityAssessment:
    return TraderSharedOpportunityAssessment(
        alert_id="alert-001",
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        assessed_at=NOW,
        disposition=disposition,
        methodology_validated=methodology_validated,
        evidence_refs=("trader:assessment-001",),
    )


def test_valid_trade_can_publish_read_only_shared_facts_to_cibo() -> None:
    facts = build_cibo_read_only_shared_facts(
        facts_id="shared-cibo-facts-001",
        trader_opportunity_id="trader-opportunity-001",
        trader_assessment=_assessment(
            TraderSharedOpportunityDisposition.VALID_TRADE,
            methodology_validated=True,
        ),
        snapshot=_snapshot(),
        built_at=NOW + timedelta(seconds=1),
        evidence_refs=(
            "shared:snapshot-001",
            "trader:assessment-001",
        ),
    )

    assert facts.trader_methodology_validated is True
    assert facts.read_only is True
    assert facts.cibo_may_abstain_or_allocate_zero is True
    assert facts.sizing_authority is False
    assert facts.capital_allocation_authority is False
    assert facts.reserve_authority is False
    assert facts.release_authority is False
    assert facts.compound_authority is False
    assert facts.risk_authority is False
    assert facts.execution_authority is False
    assert len(facts.fingerprint()) == 64


@pytest.mark.parametrize(
    "disposition",
    (
        TraderSharedOpportunityDisposition.WAIT,
        TraderSharedOpportunityDisposition.ABSTAIN,
    ),
)
def test_shared_facts_cannot_reach_cibo_before_valid_trade(
    disposition: TraderSharedOpportunityDisposition,
) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="before Trader validates a trade",
    ):
        build_cibo_read_only_shared_facts(
            facts_id="shared-cibo-facts-001",
            trader_opportunity_id="trader-opportunity-001",
            trader_assessment=_assessment(
                disposition,
                methodology_validated=False,
            ),
            snapshot=_snapshot(),
            built_at=NOW + timedelta(seconds=1),
            evidence_refs=("shared:snapshot-001",),
        )


def test_shared_support_cannot_compel_cibo_capital() -> None:
    facts = build_cibo_read_only_shared_facts(
        facts_id="shared-cibo-facts-001",
        trader_opportunity_id="trader-opportunity-001",
        trader_assessment=_assessment(
            TraderSharedOpportunityDisposition.VALID_TRADE,
            methodology_validated=True,
        ),
        snapshot=_snapshot(),
        built_at=NOW + timedelta(seconds=1),
        evidence_refs=("shared:snapshot-001",),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot compel CIBO capital",
    ):
        replace(facts, cibo_may_abstain_or_allocate_zero=False)


@pytest.mark.parametrize(
    "field_name",
    (
        "sizing_authority",
        "capital_allocation_authority",
        "reserve_authority",
        "release_authority",
        "compound_authority",
        "risk_authority",
        "execution_authority",
    ),
)
def test_shared_cibo_facts_reject_every_downstream_authority(
    field_name: str,
) -> None:
    facts = build_cibo_read_only_shared_facts(
        facts_id="shared-cibo-facts-001",
        trader_opportunity_id="trader-opportunity-001",
        trader_assessment=_assessment(
            TraderSharedOpportunityDisposition.VALID_TRADE,
            methodology_validated=True,
        ),
        snapshot=_snapshot(),
        built_at=NOW + timedelta(seconds=1),
        evidence_refs=("shared:snapshot-001",),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot carry downstream authority",
    ):
        replace(facts, **{field_name: True})


def test_shared_cibo_facts_reject_future_snapshot() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot consume future Shared snapshot",
    ):
        build_cibo_read_only_shared_facts(
            facts_id="shared-cibo-facts-001",
            trader_opportunity_id="trader-opportunity-001",
            trader_assessment=_assessment(
                TraderSharedOpportunityDisposition.VALID_TRADE,
                methodology_validated=True,
            ),
            snapshot=_snapshot(),
            built_at=NOW - timedelta(seconds=1),
            evidence_refs=("shared:snapshot-001",),
        )
