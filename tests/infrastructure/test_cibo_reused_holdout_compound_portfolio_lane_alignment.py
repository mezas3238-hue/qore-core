from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_capital_science_runtime_bridge import (
    CapitalScienceKnownOpportunity,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    _known_options_with_current_geometry,
)


NOW = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


def _option(option_id: str) -> CapitalScienceKnownOpportunity:
    return CapitalScienceKnownOpportunity(
        option_id=option_id,
        trader_id="R34_XAUUSD",
        qore_symbol="XAUUSD",
        known_at=NOW,
        earliest_action_at=NOW,
        expires_at=NOW + timedelta(minutes=30),
        requested_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("4"),
        margin_usd=Decimal("8"),
        evidence_sha256="sha256:" + "a" * 64,
        expected_net_value_usd=Decimal("1.25"),
        expected_capital_minutes=Decimal("20"),
    )


def test_current_epoch_option_tracks_resized_geometry_and_economics() -> None:
    current = _option("signal-current")
    peer = _option("signal-peer")

    updated = _known_options_with_current_geometry(
        (current, peer),
        signal_fingerprint="signal-current",
        stop_risk_usd=Decimal("2"),
        margin_usd=Decimal("4"),
        provider_cost_usd=Decimal("0.50"),
        expected_net_value_usd=Decimal("0.80"),
        expected_capital_minutes=Decimal("12"),
    )

    current_updated = next(
        item for item in updated if item.option_id == "signal-current"
    )
    peer_updated = next(item for item in updated if item.option_id == "signal-peer")

    assert current_updated.requested_capital_usd == Decimal("2.50")
    assert current_updated.stop_risk_usd == Decimal("2")
    assert current_updated.margin_usd == Decimal("4")
    assert current_updated.expected_net_value_usd == Decimal("0.80")
    assert current_updated.expected_capital_minutes == Decimal("12")
    assert peer_updated == peer
