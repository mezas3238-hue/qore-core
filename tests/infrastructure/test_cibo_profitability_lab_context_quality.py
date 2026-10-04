from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_profitability_lab_context_quality import (
    ContextQualityDisposition,
    evaluate_context_quality,
)

T0 = datetime(2020, 1, 2, 12, 0, tzinfo=UTC)


def _opportunity(
    trader: TraderLineage,
    context: tuple[tuple[str, str], ...],
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=f"signal-{trader.value}",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
        decision_context=context,
    )


def test_context_quality_abstains_on_any_cross_holdout_adverse_context() -> None:
    decision = evaluate_context_quality(
        opportunity=_opportunity(
            TraderLineage.R43_GBPUSD,
            (
                ("ctx_strategy_projected_r_bucket", "q1:<=0.5"),
                ("ctx_strategy_target_distance_range_bucket", "q3:<=2.0"),
                ("target_route", "OTHER"),
            ),
        ),
        decision_at=T0,
    )

    assert decision.disposition is ContextQualityDisposition.ABSTAIN
    assert decision.matched_rule_ids == ("LOW_PROJECTED_R_BUCKET",)
    assert decision.outcome_used is False
    assert decision.identity_predicate_used is False
    assert decision.certification_claimed is False


def test_context_quality_allows_clean_context() -> None:
    decision = evaluate_context_quality(
        opportunity=_opportunity(
            TraderLineage.VT31_NAS100,
            (
                ("ctx_strategy_projected_r_bucket", "q5:>2.5"),
                ("ctx_strategy_target_distance_range_bucket", "q4:<=4.0"),
                ("target_route", "OTHER"),
            ),
        ),
        decision_at=T0,
    )

    assert decision.disposition is ContextQualityDisposition.ALLOW
    assert decision.matched_rule_ids == ()


def test_context_quality_is_universal_not_trader_identity_specific() -> None:
    context = (
        ("ctx_strategy_projected_r_bucket", "q4:<=2.5"),
        ("ctx_strategy_target_distance_range_bucket", "q1:<=0.5"),
        ("target_route", "OTHER"),
    )
    left = evaluate_context_quality(
        opportunity=_opportunity(TraderLineage.R43_GBPUSD, context),
        decision_at=T0,
    )
    right = evaluate_context_quality(
        opportunity=_opportunity(TraderLineage.VT08_FOREX, context),
        decision_at=T0,
    )

    assert left.disposition is ContextQualityDisposition.ABSTAIN
    assert right.disposition is ContextQualityDisposition.ABSTAIN
    assert left.matched_rule_ids == right.matched_rule_ids
