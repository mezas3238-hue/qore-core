from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedCe2iEvidenceBundle,
    AdvancedToolDisposition,
    CapitalVelocityEvidence,
    CapitalVelocityPolicy,
    ConvexExposureEvidence,
    ConvexInstrumentEvidence,
    FactorExposure,
    HedgedExposureEvidence,
    HedgeInstrumentEvidence,
    MarginEfficiencyEvidence,
    MarginExpression,
    PortfolioNettingEvidence,
    RiskEfficiencyCandidate,
    RiskEfficiencyEvidence,
    StructuralLeverageEvidence,
    assert_complete_advanced_ce2i_surface,
    evaluate_advanced_ce2i_surface,
    evaluate_capital_velocity,
    evaluate_convex_exposure,
    evaluate_hedged_exposure,
    evaluate_margin_efficiency,
    evaluate_portfolio_netting,
    evaluate_risk_efficiency,
    evaluate_structural_leverage,
)


_NOW = datetime(2026, 9, 27, 20, tzinfo=UTC)


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="signal-001",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("3800"),
        stop_loss=Decimal("3790"),
        take_profit=Decimal("3820"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("25"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
    )


def test_t02_requires_verified_oos_structure_and_preserves_stop_geometry() -> None:
    evidence = StructuralLeverageEvidence(
        evidence_id="t02-oos",
        structural_invalidation_id="r34-stop-v1",
        observed_at=_NOW,
        sample_size=80,
        baseline_stop_rate=Decimal("0.44"),
        candidate_stop_rate=Decimal("0.35"),
        baseline_tail_loss_r=Decimal("1.00"),
        candidate_tail_loss_r=Decimal("0.90"),
        released_risk_capacity_usd=Decimal("2"),
        protected_capacity_usd=Decimal("1"),
        evidence_oos=True,
        structural_stop_verified=True,
        stop_geometry_unchanged=True,
    )
    decision = evaluate_structural_leverage(
        opportunity=_opportunity(),
        evidence=evidence,
        current_volume=Decimal("0.01"),
        maximum_additional_volume=Decimal("0.20"),
    )

    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.approved_volume > Decimal("0.01")

    invalid = StructuralLeverageEvidence(
        evidence_id="t02-invalid",
        structural_invalidation_id="r34-stop-v1",
        observed_at=_NOW,
        sample_size=80,
        baseline_stop_rate=Decimal("0.44"),
        candidate_stop_rate=Decimal("0.35"),
        baseline_tail_loss_r=Decimal("1.00"),
        candidate_tail_loss_r=Decimal("0.90"),
        released_risk_capacity_usd=Decimal("2"),
        protected_capacity_usd=Decimal("1"),
        evidence_oos=True,
        structural_stop_verified=True,
        stop_geometry_unchanged=False,
    )
    rejected = evaluate_structural_leverage(
        opportunity=_opportunity(),
        evidence=invalid,
        current_volume=Decimal("0.01"),
        maximum_additional_volume=Decimal("0.20"),
    )
    assert rejected.disposition is AdvancedToolDisposition.FAIL_CLOSED


def test_t03_selects_only_verified_equivalent_lower_margin_expression() -> None:
    decision = evaluate_margin_efficiency(
        MarginEfficiencyEvidence(
            evidence_id="t03",
            observed_at=_NOW,
            baseline_expression_id="spot",
            expressions=(
                MarginExpression(
                    expression_id="spot",
                    normalized_exposure=Decimal("100"),
                    stop_risk_usd=Decimal("10"),
                    margin_usd=Decimal("50"),
                    all_in_cost_usd=Decimal("2"),
                    executable=True,
                    economics_verified=True,
                ),
                MarginExpression(
                    expression_id="equivalent",
                    normalized_exposure=Decimal("100"),
                    stop_risk_usd=Decimal("10"),
                    margin_usd=Decimal("30"),
                    all_in_cost_usd=Decimal("2"),
                    executable=True,
                    economics_verified=True,
                ),
            ),
        )
    )

    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.selected_id == "equivalent"
    assert decision.released_capacity_usd == Decimal("20")


def test_t04_requires_strict_oos_risk_efficiency_without_worse_tail() -> None:
    decision = evaluate_risk_efficiency(
        RiskEfficiencyEvidence(
            evidence_id="t04",
            observed_at=_NOW,
            baseline_candidate_id="baseline",
            candidates=(
                RiskEfficiencyCandidate(
                    candidate_id="baseline",
                    expected_net_output_usd=Decimal("20"),
                    true_stop_risk_usd=Decimal("10"),
                    p95_drawdown_usd=Decimal("12"),
                    tail_loss_usd=Decimal("15"),
                    margin_usd=Decimal("30"),
                    sample_size=100,
                    evidence_oos=True,
                ),
                RiskEfficiencyCandidate(
                    candidate_id="efficient",
                    expected_net_output_usd=Decimal("24"),
                    true_stop_risk_usd=Decimal("8"),
                    p95_drawdown_usd=Decimal("11"),
                    tail_loss_usd=Decimal("14"),
                    margin_usd=Decimal("30"),
                    sample_size=100,
                    evidence_oos=True,
                ),
            ),
        )
    )

    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.selected_id == "efficient"
    assert decision.score == Decimal("3")


def test_t08_uses_verified_stable_factor_offsets_and_caps_credit() -> None:
    decision = evaluate_portfolio_netting(
        PortfolioNettingEvidence(
            evidence_id="t08",
            observed_at=_NOW,
            correlation_state_id="corr-v1",
            correlation_stable=True,
            factor_map_verified=True,
            maximum_credit_fraction=Decimal("0.50"),
            exposures=(
                FactorExposure(
                    position_id="p1",
                    factor_id="USD",
                    signed_risk_usd=Decimal("10"),
                ),
                FactorExposure(
                    position_id="p2",
                    factor_id="USD",
                    signed_risk_usd=Decimal("-6"),
                ),
            ),
        )
    )

    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.released_capacity_usd == Decimal("8")


def test_t10_uses_oos_output_per_capital_minute_without_worse_tail() -> None:
    decision = evaluate_capital_velocity(
        CapitalVelocityEvidence(
            evidence_id="t10",
            observed_at=_NOW,
            baseline_policy_id="baseline",
            policies=(
                CapitalVelocityPolicy(
                    policy_id="baseline",
                    realized_net_output_usd=Decimal("20"),
                    capital_minutes=Decimal("100"),
                    p95_drawdown_usd=Decimal("10"),
                    tail_loss_usd=Decimal("12"),
                    sample_size=100,
                    evidence_oos=True,
                ),
                CapitalVelocityPolicy(
                    policy_id="faster",
                    realized_net_output_usd=Decimal("22"),
                    capital_minutes=Decimal("80"),
                    p95_drawdown_usd=Decimal("10"),
                    tail_loss_usd=Decimal("11"),
                    sample_size=100,
                    evidence_oos=True,
                ),
            ),
        )
    )

    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.selected_id == "faster"
    assert decision.score == Decimal("0.275")


def test_t16_abstains_without_certified_hedge_and_applies_positive_net_transfer() -> None:
    none = evaluate_hedged_exposure(
        HedgedExposureEvidence(
            evidence_id="t16-none",
            observed_at=_NOW,
            instruments=(),
        )
    )
    assert none.disposition is AdvancedToolDisposition.ABSTAIN
    assert none.reason == "NO_CERTIFIED_HEDGE_INSTRUMENT"

    applied = evaluate_hedged_exposure(
        HedgedExposureEvidence(
            evidence_id="t16",
            observed_at=_NOW,
            instruments=(
                HedgeInstrumentEvidence(
                    instrument_id="hedge-1",
                    target_factor_id="USD",
                    correlation_abs=Decimal("0.90"),
                    correlation_stability=Decimal("0.85"),
                    gross_risk_reduction_usd=Decimal("20"),
                    basis_risk_usd=Decimal("4"),
                    hedge_cost_usd=Decimal("2"),
                    margin_usd=Decimal("3"),
                    instrument_certified=True,
                    execution_supported=True,
                ),
            ),
        )
    )
    assert applied.disposition is AdvancedToolDisposition.APPLIED
    assert applied.released_capacity_usd == Decimal("14")


def test_t17_never_invents_convexity_without_certified_instrument() -> None:
    none = evaluate_convex_exposure(
        ConvexExposureEvidence(
            evidence_id="t17-none",
            observed_at=_NOW,
            available_limited_downside_capacity_usd=Decimal("20"),
            instruments=(),
        )
    )
    assert none.disposition is AdvancedToolDisposition.ABSTAIN
    assert none.reason == "NO_CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT"

    applied = evaluate_convex_exposure(
        ConvexExposureEvidence(
            evidence_id="t17",
            observed_at=_NOW,
            available_limited_downside_capacity_usd=Decimal("20"),
            instruments=(
                ConvexInstrumentEvidence(
                    instrument_id="convex-1",
                    bounded_downside_usd=Decimal("10"),
                    premium_and_cost_usd=Decimal("2"),
                    expected_upside_usd=Decimal("12"),
                    pricing_fresh=True,
                    settlement_certified=True,
                    execution_supported=True,
                    instrument_certified=True,
                ),
            ),
        )
    )
    assert applied.disposition is AdvancedToolDisposition.APPLIED
    assert applied.selected_id == "convex-1"


def test_full_advanced_surface_fails_closed_when_enabled_evidence_is_missing() -> None:
    assert_complete_advanced_ce2i_surface()
    decisions = evaluate_advanced_ce2i_surface(
        enabled_tools=("T02", "T03", "T04", "T08", "T10", "T16", "T17"),
        opportunity=_opportunity(),
        evidence=AdvancedCe2iEvidenceBundle(),
    )

    assert tuple(item.tool_code for item in decisions) == (
        "T02",
        "T03",
        "T04",
        "T08",
        "T10",
        "T16",
        "T17",
    )
    assert all(
        item.disposition is AdvancedToolDisposition.FAIL_CLOSED
        for item in decisions
    )
