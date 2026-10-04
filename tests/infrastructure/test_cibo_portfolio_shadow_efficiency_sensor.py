from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_portfolio_shadow_efficiency_sensor import (
    measure_portfolio_shadow_efficiency,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    CompoundPortfolioShadowDecision,
)


NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _decision(
    *,
    release: bool,
    open_positions: int = 1,
    incremental: str = "1",
) -> CompoundPortfolioShadowDecision:
    return CompoundPortfolioShadowDecision(
        signal_fingerprint="signal-release" if release else "signal-keep",
        trader_id="R34_XAUUSD",
        decision_at=NOW,
        open_position_count=open_positions,
        allocation_multiplier=1,
        allocation_expected_net_utility_usd=Decimal("2"),
        position_competition_observed=open_positions > 0,
        fits_without_release=not release,
        release_proposed=release,
        proposed_released_stop_risk_usd=(
            Decimal("1") if release else Decimal("0")
        ),
        proposed_released_margin_usd=(
            Decimal("2") if release else Decimal("0")
        ),
        net_incremental_utility_usd=Decimal(incremental),
        admit_opportunity=True,
    )


def test_portfolio_shadow_sensor_exposes_release_surface() -> None:
    report = measure_portfolio_shadow_efficiency(
        (
            _decision(release=True, incremental="1.5"),
            _decision(release=False, incremental="0.7"),
        )
    )

    assert report.decision_count == 2
    assert report.open_position_competition_count == 2
    assert report.release_proposal_count == 1
    assert report.cumulative_proposed_released_stop_risk_usd == Decimal("1")
    assert report.cumulative_proposed_released_margin_usd == Decimal("2")
    assert report.cumulative_net_incremental_utility_usd == Decimal("2.2")
    assert report.shadow_actuation_rate == Decimal("0.5")
    assert (
        report.primary_blocker
        == "SHADOW_RELEASE_REQUIRES_EXECUTABLE_SETTLEMENT_EVIDENCE"
    )


def test_portfolio_shadow_sensor_separates_no_competition() -> None:
    report = measure_portfolio_shadow_efficiency(
        (_decision(release=False, open_positions=0),)
    )

    assert report.open_position_competition_count == 0
    assert report.release_proposal_count == 0
    assert report.primary_blocker == "NO_OPEN_POSITION_COMPETITION"
