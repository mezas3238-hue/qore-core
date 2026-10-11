"""Only the physically witnessed source-market clock may alter epistemic status."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from test_capitalizer_a1_native_nine_market_epistemic_inputs_v1 import (
    _observations,
)

from qore.infrastructure.trader_lab import (
    capitalizer_a1_native_source_session_clock_attestation_v1 as clock,
)
from qore.infrastructure.trader_lab.capitalizer_a1_native_clock_bound_perception_v2 import (
    bind_source_clocks_to_perceptions,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerPerceptionStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
)

T = datetime(2026, 1, 5, 10, tzinfo=UTC)


def _clock() -> clock.A1V49SourceClockEvidence:
    return clock.A1V49SourceClockEvidence(
        source_opportunity_id="SOURCE:EURUSD:ORIGINAL",
        symbol="EURUSD",
        source_session=CapitalizerSession.LONDON,
        source_operating_date="2026-01-05",
        observed_at=T.isoformat(),
        m1_opened_at=(T-timedelta(minutes=1)).isoformat(),
        new_york_local_time="2026-01-05T05:00:00-05:00",
        new_york_utc_offset_minutes=-300,
        qore_bucket_reconfirmed=clock.ClockAttestationStatus.QORE_BUCKET_RECONFIRMED,
        local_operating_day_reconfirmed=True,
        within_qore_research_session=True,
        remaining_session_seconds=3 * 3600 + 30 * 60,
        methodology_window_resolution=CapitalizerSourceSessionResolution.OUTSIDE,
        methodology_window_id="ICT_LONDON_KILLZONE_0200_0500_NY",
    )


def test_only_proven_source_market_clock_becomes_degraded_never_good() -> None:
    result = bind_source_clocks_to_perceptions(
        observations=_observations(), source_clocks=(_clock(),),
    )
    states = {p.symbol: p.assessment for p in result.perceptions}
    assert states["EURUSD"].status is CapitalizerPerceptionStatus.DEGRADED
    assert set(states["EURUSD"].reasons) == {
        "QUOTE_NOT_FRESH", "MICROSTRUCTURE_INCOMPLETE",
    }
    assert all(
        states[s].status is CapitalizerPerceptionStatus.BAD
        for s in states if s != "EURUSD"
    )
    assert result.source_clock_ids == ("SOURCE:EURUSD:ORIGINAL",)
    assert result.verified_source_market_clocks == ("EURUSD",)
    assert not result.author_killzone_attested
    assert not result.all_quotes_attested
    assert not result.full_master_frame_executed
    assert all(x.family_id is None for x in result.native.regimes)


def test_missing_clock_never_promotes_perceptions_for_any_market() -> None:
    result = bind_source_clocks_to_perceptions(
        observations=_observations(), source_clocks=(),
    )
    assert not result.verified_source_market_clocks
    assert all(
        p.assessment.status is CapitalizerPerceptionStatus.BAD
        for p in result.perceptions
    )


def test_clock_without_matching_exact_native_source_bar_rejected() -> None:
    for witness in (
        replace(_clock(), observed_at=(T-timedelta(minutes=1)).isoformat(),
                m1_opened_at=(T-timedelta(minutes=2)).isoformat()),
        replace(_clock(), symbol="UNIVERSE_OUTSIDE"),
    ):
        with pytest.raises(ValueError, match="clock|outside|physically"):
            bind_source_clocks_to_perceptions(
                observations=_observations(), source_clocks=(witness,),
            )
    with pytest.raises(ValueError, match="exact timezone-aware closed bar"):
        replace(_clock(), m1_opened_at=(T-timedelta(minutes=2)).isoformat())
    with pytest.raises(ValueError, match="duplicated"):
        bind_source_clocks_to_perceptions(
            observations=_observations(), source_clocks=(_clock(), _clock()),
        )


def test_bars_incomplete_do_not_forge_clock_and_no_trade_veto_introduced() -> None:
    with pytest.raises(ValueError, match="physically closed"):
        bind_source_clocks_to_perceptions(
            observations=_observations(incomplete="EURUSD"),
            source_clocks=(_clock(),),
        )
    conflicted = replace(
        _clock(),
        qore_bucket_reconfirmed=clock.ClockAttestationStatus.QORE_BUCKET_CONTRADICTED,
        within_qore_research_session=False,
        local_operating_day_reconfirmed=False,
    )
    result = bind_source_clocks_to_perceptions(
        observations=_observations(), source_clocks=(conflicted,),
    )
    by = {p.symbol: p for p in result.perceptions}
    assert by["EURUSD"].assessment.status is CapitalizerPerceptionStatus.BAD
    assert not result.verified_source_market_clocks
    assert not result.live_authorized
