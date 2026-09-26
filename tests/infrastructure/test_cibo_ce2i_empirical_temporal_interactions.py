from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_empirical_temporal_interactions import (
    HistoricalTemporalCompetitionPrior,
    build_historical_temporal_interactions,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)


WINDOW_START = datetime(2021, 9, 23, 5, tzinfo=UTC)
WINDOW_END = datetime(2022, 6, 29, 9, tzinfo=UTC)
DECISION = datetime(2026, 9, 26, 18, tzinfo=UTC)


def _candidate(
    fingerprint: str,
    trader: TraderLineage,
) -> CapitalOpportunityCandidate:
    return CapitalOpportunityCandidate(
        signal_fingerprint=fingerprint,
        trader_id=trader,
        qore_symbol=fingerprint.upper(),
        provider_symbol=fingerprint.upper(),
        expected_net_value_usd=Decimal("10"),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        expected_capital_minutes=Decimal("30"),
        concentration_group="TEST",
        concentration_risk_usd=Decimal("5"),
    )


def _prior(
    left: TraderLineage,
    right: TraderLineage,
    *,
    overlap: int,
) -> HistoricalTemporalCompetitionPrior:
    ordered = sorted((left, right), key=lambda trader: trader.value)
    return HistoricalTemporalCompetitionPrior(
        left_trader=ordered[0],
        right_trader=ordered[1],
        overlap_pairs=overlap,
        total_cross_trader_overlap_pairs=250,
        observed_window_start=WINDOW_START,
        observed_window_end=WINDOW_END,
        evidence_id="phase19:36262706237:18dfde3b",
    )


def test_competition_share_uses_only_observed_cross_trader_overlap_mass() -> None:
    prior = _prior(
        TraderLineage.R38_GBPJPY,
        TraderLineage.R42_AUDJPY,
        overlap=30,
    )
    assert prior.competition_share == Decimal("0.12")


def test_historical_pair_prior_maps_to_current_fingerprints() -> None:
    left = _candidate("new-gbpjpy", TraderLineage.R38_GBPJPY)
    right = _candidate("new-audjpy", TraderLineage.R42_AUDJPY)

    result = build_historical_temporal_interactions(
        candidates=(right, left),
        priors=(_prior(left.trader_id, right.trader_id, overlap=30),),
        decision_as_of=DECISION,
    )

    assert len(result) == 1
    assert {
        result[0].left_signal_fingerprint,
        result[0].right_signal_fingerprint,
    } == {"new-gbpjpy", "new-audjpy"}
    assert result[0].temporal_overlap == Decimal("0.12")
    assert result[0].factor_overlap == Decimal(0)
    assert result[0].observed_abs_correlation == Decimal(0)
    assert result[0].hedge_offset == Decimal(0)


def test_missing_pair_evidence_is_not_inferred() -> None:
    candidates = (
        _candidate("eur", TraderLineage.R38_EURUSD),
        _candidate("nas", TraderLineage.VT31_NAS100),
    )
    result = build_historical_temporal_interactions(
        candidates=candidates,
        priors=(
            _prior(
                TraderLineage.R38_GBPJPY,
                TraderLineage.R42_AUDJPY,
                overlap=30,
            ),
        ),
        decision_as_of=DECISION,
    )
    assert result == ()


def test_same_trader_pair_does_not_receive_cross_trader_prior() -> None:
    candidates = (
        _candidate("eur-a", TraderLineage.R38_EURUSD),
        _candidate("eur-b", TraderLineage.R38_EURUSD),
    )
    result = build_historical_temporal_interactions(
        candidates=candidates,
        priors=(),
        decision_as_of=DECISION,
    )
    assert result == ()


def test_future_or_same_instant_prior_is_rejected_as_noncausal() -> None:
    prior = HistoricalTemporalCompetitionPrior(
        left_trader=TraderLineage.R38_EURUSD,
        right_trader=TraderLineage.VT31_NAS100,
        overlap_pairs=5,
        total_cross_trader_overlap_pairs=250,
        observed_window_start=WINDOW_START,
        observed_window_end=DECISION,
        evidence_id="bad-future",
    )
    with pytest.raises(CiboCapitalManagementError, match="predate"):
        build_historical_temporal_interactions(
            candidates=(
                _candidate("eur", TraderLineage.R38_EURUSD),
                _candidate("nas", TraderLineage.VT31_NAS100),
            ),
            priors=(prior,),
            decision_as_of=DECISION,
        )


def test_duplicate_prior_pair_fails_closed() -> None:
    prior = _prior(
        TraderLineage.R38_EURUSD,
        TraderLineage.VT31_NAS100,
        overlap=5,
    )
    with pytest.raises(CiboCapitalManagementError, match="duplicate"):
        build_historical_temporal_interactions(
            candidates=(
                _candidate("eur", TraderLineage.R38_EURUSD),
                _candidate("nas", TraderLineage.VT31_NAS100),
            ),
            priors=(prior, prior),
            decision_as_of=DECISION,
        )
