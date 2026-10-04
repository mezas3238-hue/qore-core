from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from qore.infrastructure.cibo_portfolio_engine_capability_sensor import (
    measure_portfolio_engine_capability,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    CompoundPortfolioShadowDecision,
)
from tests.infrastructure.test_cibo_full_economic_digital_twin import (
    T0,
    _position_competition_twin,
)


def _shadow(*, release: bool) -> CompoundPortfolioShadowDecision:
    return CompoundPortfolioShadowDecision(
        signal_fingerprint="superior-new",
        trader_id="R34_XAUUSD",
        decision_at=T0,
        open_position_count=1,
        allocation_multiplier=1,
        allocation_expected_net_utility_usd=Decimal("2"),
        position_competition_observed=True,
        fits_without_release=not release,
        release_proposed=release,
        proposed_released_stop_risk_usd=(
            Decimal("1") if release else Decimal("0")
        ),
        proposed_released_margin_usd=(
            Decimal("2") if release else Decimal("0")
        ),
        net_incremental_utility_usd=Decimal("1"),
        admit_opportunity=True,
    )


def _marked_twin():
    twin = _position_competition_twin(
        continuation_value=Decimal("0.5"),
        headroom_risk=Decimal("1"),
        headroom_margin=Decimal("10"),
    )
    position = replace(
        twin.positions[0],
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        current_mark_price=Decimal("100.6"),
        market_state_observed_at=T0 - timedelta(minutes=1),
        mark_to_market_identified=True,
        continuation_value_identified=True,
        releasable=True,
    )
    return replace(twin, positions=(position,))


def test_portfolio_capability_stays_zero_when_release_is_shadow_only() -> None:
    report = measure_portfolio_engine_capability(
        twin=_marked_twin(),
        shadow_decisions=(_shadow(release=True),),
    )

    assert report.continuation_efficiency == Decimal("1")
    assert report.release_execution_efficiency == Decimal("1")
    assert report.shadow_actuation_efficiency == Decimal("0")
    assert report.portfolio_capability_efficiency == Decimal("0")
    assert report.primary_blocker == (
        "SHADOW_RELEASE_REQUIRES_EXECUTABLE_SETTLEMENT_EVIDENCE"
    )


def test_portfolio_keep_path_can_be_complete_without_release_mutation() -> None:
    report = measure_portfolio_engine_capability(
        twin=_marked_twin(),
        shadow_decisions=(_shadow(release=False),),
    )

    assert report.continuation_efficiency == Decimal("1")
    assert report.release_execution_efficiency == Decimal("1")
    assert report.shadow_actuation_efficiency == Decimal("1")
    assert report.portfolio_capability_efficiency == Decimal("1")
    assert report.primary_blocker == "NONE"
