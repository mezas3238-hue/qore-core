from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase19_interaction_evidence import (
    Phase19TemporalOverlapAtlas,
    Phase19TraderPairOverlap,
    project_phase19_temporal_overlap_evidence,
)


PAIR_COUNTS = (
    (TraderLineage.R34_XAUUSD, TraderLineage.R38_EURUSD, 15),
    (TraderLineage.R34_XAUUSD, TraderLineage.R38_GBPJPY, 16),
    (TraderLineage.R34_XAUUSD, TraderLineage.R42_AUDJPY, 19),
    (TraderLineage.R34_XAUUSD, TraderLineage.R43_GBPUSD, 22),
    (TraderLineage.R34_XAUUSD, TraderLineage.VT08_FOREX, 3),
    (TraderLineage.R34_XAUUSD, TraderLineage.VT31_NAS100, 6),
    (TraderLineage.R38_EURUSD, TraderLineage.R38_GBPJPY, 17),
    (TraderLineage.R38_EURUSD, TraderLineage.R42_AUDJPY, 14),
    (TraderLineage.R38_EURUSD, TraderLineage.R43_GBPUSD, 22),
    (TraderLineage.R38_EURUSD, TraderLineage.VT08_FOREX, 2),
    (TraderLineage.R38_EURUSD, TraderLineage.VT31_NAS100, 0),
    (TraderLineage.R38_GBPJPY, TraderLineage.R42_AUDJPY, 30),
    (TraderLineage.R38_GBPJPY, TraderLineage.R43_GBPUSD, 17),
    (TraderLineage.R38_GBPJPY, TraderLineage.VT08_FOREX, 7),
    (TraderLineage.R38_GBPJPY, TraderLineage.VT31_NAS100, 5),
    (TraderLineage.R42_AUDJPY, TraderLineage.R43_GBPUSD, 19),
    (TraderLineage.R42_AUDJPY, TraderLineage.VT08_FOREX, 8),
    (TraderLineage.R42_AUDJPY, TraderLineage.VT31_NAS100, 13),
    (TraderLineage.R43_GBPUSD, TraderLineage.VT08_FOREX, 8),
    (TraderLineage.R43_GBPUSD, TraderLineage.VT31_NAS100, 3),
    (TraderLineage.VT08_FOREX, TraderLineage.VT31_NAS100, 4),
)


def _atlas() -> Phase19TemporalOverlapAtlas:
    return Phase19TemporalOverlapAtlas(
        source_evidence_id=(
            "github-actions:phase19:10912847765:"
            "sha256:208d5ca523735273e9f40026bab1a0da041147a610f7c3af50d82c9873ff4072"
        ),
        common_window_start=datetime(2021, 9, 23, 5, 0, tzinfo=UTC),
        common_window_end=datetime(2022, 6, 29, 9, 0, tzinfo=UTC),
        total_cross_trader_overlap_pairs=250,
        pair_overlaps=tuple(
            Phase19TraderPairOverlap(
                left_trader=left,
                right_trader=right,
                overlapping_pairs=count,
            )
            for left, right, count in PAIR_COUNTS
        ),
    )


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
        margin_usd=Decimal("8"),
        expected_capital_minutes=Decimal("10"),
        concentration_group="TEST",
        concentration_risk_usd=Decimal("4"),
    )


def test_phase19_atlas_binds_complete_empirical_pair_matrix() -> None:
    atlas = _atlas()

    assert atlas.total_cross_trader_overlap_pairs == 250
    assert len(atlas.pair_overlaps) == 21
    assert atlas.overlap_count(
        TraderLineage.R38_GBPJPY,
        TraderLineage.R42_AUDJPY,
    ) == 30
    assert atlas.overlap_share(
        TraderLineage.R38_GBPJPY,
        TraderLineage.R42_AUDJPY,
    ) == Decimal("0.12")
    assert atlas.overlap_share(
        TraderLineage.R38_EURUSD,
        TraderLineage.VT31_NAS100,
    ) == Decimal(0)


def test_phase19_projection_adds_observational_temporal_edges_only() -> None:
    evidence = project_phase19_temporal_overlap_evidence(
        candidates=(
            _candidate("gbpjpy", TraderLineage.R38_GBPJPY),
            _candidate("audjpy", TraderLineage.R42_AUDJPY),
            _candidate("xauusd", TraderLineage.R34_XAUUSD),
        ),
        atlas=_atlas(),
    )

    by_pair = {
        item.unordered_key: item
        for item in evidence
    }
    strongest = by_pair[("audjpy", "gbpjpy")]
    assert strongest.temporal_overlap == Decimal("0.12")
    assert strongest.factor_overlap == Decimal(0)
    assert strongest.observed_abs_correlation == Decimal(0)
    assert strongest.same_provider_group is False
    assert strongest.hedge_offset == Decimal(0)


def test_phase19_zero_historical_pair_creates_no_temporal_edge() -> None:
    evidence = project_phase19_temporal_overlap_evidence(
        candidates=(
            _candidate("eurusd", TraderLineage.R38_EURUSD),
            _candidate("nas100", TraderLineage.VT31_NAS100),
        ),
        atlas=_atlas(),
    )

    assert evidence == ()


def test_phase19_atlas_fails_closed_on_pair_population_or_total_drift() -> None:
    atlas = _atlas()

    with pytest.raises(CiboCapitalManagementError, match="complete seven-Trader"):
        Phase19TemporalOverlapAtlas(
            source_evidence_id=atlas.source_evidence_id,
            common_window_start=atlas.common_window_start,
            common_window_end=atlas.common_window_end,
            total_cross_trader_overlap_pairs=250,
            pair_overlaps=atlas.pair_overlaps[:-1],
        )

    with pytest.raises(CiboCapitalManagementError, match="overlap total drift"):
        Phase19TemporalOverlapAtlas(
            source_evidence_id=atlas.source_evidence_id,
            common_window_start=atlas.common_window_start,
            common_window_end=atlas.common_window_end,
            total_cross_trader_overlap_pairs=249,
            pair_overlaps=atlas.pair_overlaps,
        )


def test_phase19_projection_rejects_unsupported_or_duplicate_candidates() -> None:
    atlas = _atlas()
    duplicate = _candidate("dup", TraderLineage.R38_EURUSD)

    with pytest.raises(CiboCapitalManagementError, match="duplicate candidate"):
        project_phase19_temporal_overlap_evidence(
            candidates=(duplicate, duplicate),
            atlas=atlas,
        )

    with pytest.raises(CiboCapitalManagementError, match="outside CMA portfolio"):
        project_phase19_temporal_overlap_evidence(
            candidates=(
                _candidate("index", TraderLineage.VT08_INDEX),
            ),
            atlas=atlas,
        )
