"""Causal independently observed structure witnesses are not blanket filters."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    ProofStatus,
    attest_source_sensors,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)


def _m1(
    at: datetime, *,
    open_: str, high: str, low: str, close: str,
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="AUDJPY",
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal(open_), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
        digits=3, volume=None,
    )


def _agg(
    at: datetime, *, minutes: int, open_: str, high: str,
    low: str, close: str, complete: int | None = None,
) -> V48AggregatedBar:
    return V48AggregatedBar(
        opened_at=at, closed_at=at + timedelta(minutes=minutes),
        source=CapitalizerSourceBar(
            open=Decimal(open_), high=Decimal(high),
            low=Decimal(low), close=Decimal(close),
        ),
        minute_count=minutes if complete is None else complete,
    )


def _source() -> V49Opportunity:
    at = datetime(2026, 1, 5, 1, 4, tzinfo=UTC)
    return V49Opportunity(
        symbol="AUDJPY", session="ASIA", operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from="2026-01-05T00:00:00+00:00",
        h1_state_until="2026-01-05T02:00:00+00:00",
        h1_state_basis="CANDLE2_REVERSAL",
        m15_setup_confirmed_at="2026-01-05T01:00:00+00:00",
        m15_protected_swing_price="95",
        m1_trigger_confirmed_at=at.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="101",
        structural_target_witness_price="110",
    )


def _fixtures() -> tuple[
    tuple[CapitalizerM1Bar, ...],
    tuple[V48AggregatedBar, ...],
    tuple[V48AggregatedBar, ...],
]:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    m1 = (
        _m1(at, open_="100", high="101", low="99", close="100"),
        _m1(at + timedelta(minutes=1), open_="100", high="100", low="97", close="99"),
        _m1(at + timedelta(minutes=2), open_="100", high="101", low="98", close="100"),
        _m1(at + timedelta(minutes=3), open_="100", high="102", low="99", close="101"),
    )
    m15 = (
        _agg(at - timedelta(hours=1), minutes=15,
             open_="99", high="101", low="98", close="99"),
        _agg(at - timedelta(minutes=45), minutes=15,
             open_="100", high="101", low="95", close="99"),
        _agg(at - timedelta(minutes=30), minutes=15,
             open_="99", high="101", low="98", close="99"),
        _agg(at - timedelta(minutes=15), minutes=15,
             open_="99", high="102", low="98", close="101"),
    )
    h1 = (_agg(at - timedelta(hours=2), minutes=60,
               open_="95", high="110", low="90", close="100"),)
    return m1, m15, h1


def test_three_market_structure_sources_can_be_independently_attested() -> None:
    m1, m15, h1 = _fixtures()
    report = attest_source_sensors(_source(), m1=m1, m15=m15, h1=h1)
    states = {row.sensor: row.status for row in report.evidence}
    assert states["ACTUAL_M15_STRUCTURE_REVALIDATION"] is ProofStatus.OBSERVED
    assert states["M1_PROTECTED_SWING_ATTESTATION"] is ProofStatus.OBSERVED
    assert states["H1_TARGET_ROOM_R"] is ProofStatus.OBSERVED
    assert states["FULL_COGNITIVE_MASTER_FRAME"] is ProofStatus.NOT_AVAILABLE
    assert report.source_identity_preserved
    assert not report.trader_selected
    assert not report.historical_outcome_visible
    assert all(not x.trading_veto_created and not x.author_fidelity_certified
               for x in report.evidence)


def test_unfinished_partial_h1_does_not_fake_target_confirmation() -> None:
    m1, m15, h1 = _fixtures()
    incomplete = (replace(h1[0], minute_count=59),)
    report = attest_source_sensors(
        _source(), m1=m1, m15=m15, h1=incomplete
    )
    by = {x.sensor: x for x in report.evidence}
    assert by["H1_TARGET_ROOM_R"].status is ProofStatus.NOT_AVAILABLE
    assert by["ACTUAL_M15_STRUCTURE_REVALIDATION"].status is ProofStatus.OBSERVED
    mismatched_m15 = attest_source_sensors(
        replace(_source(), m15_protected_swing_price="96"),
        m1=m1, m15=m15, h1=h1,
    )
    statuses = {x.sensor: x.status for x in mismatched_m15.evidence}
    assert statuses["ACTUAL_M15_STRUCTURE_REVALIDATION"] is ProofStatus.NOT_AVAILABLE
    assert statuses["H1_TARGET_ROOM_R"] is ProofStatus.OBSERVED


def test_native_m1_proof_rejects_future_and_wrong_source_close() -> None:
    m1, m15, h1 = _fixtures()
    future = _m1(
        m1[-1].closed_at, open_="100", high="110",
        low="99", close="109",
    )
    with pytest.raises(ValueError, match="future M1"):
        attest_source_sensors(
            _source(), m1=(*m1, future), m15=m15, h1=h1,
        )
    with pytest.raises(ValueError, match="entry differs"):
        attest_source_sensors(
            replace(_source(), decision_reference_price="102"),
            m1=m1, m15=m15, h1=h1,
        )
