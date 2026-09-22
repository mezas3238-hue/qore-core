from __future__ import annotations

import gzip
import json
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
import vt31_nas100_runtime_adapter as adapter
from vt31_nas100_live_policy import evaluate_live_basket, prepare_live_context
from vt31_nas100_runtime_adapter import evaluate_boundary

from qore.infrastructure.market_data import MarketDataSnapshotId, OhlcSnapshot
from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    cibo_market_memory_fingerprint,
)
from qore.infrastructure.vt31_nas100_live import (
    _INSTRUMENT,
    _SOURCE,
    _TIMEFRAME_M1,
    Vt31Nas100SlaExpired,
    _evidence_fingerprint,
)
from qore.infrastructure.vt31_nas100_state import Vt31Nas100LiveState, Vt31Nas100LiveStateStore

_FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "vt31_nas100_20260922_1426.json.gz"
)


@pytest.fixture(scope="module")
def incident_bars() -> tuple[OhlcSnapshot, ...]:
    with gzip.open(_FIXTURE, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["schema"] == "qore.vt31.live_replay.v1"
    bars = []
    for item in payload["bars"]:
        opened = datetime.fromisoformat(item["opened_at"]).astimezone(UTC)
        bars.append(
            OhlcSnapshot(
                snapshot_id=MarketDataSnapshotId(
                    uuid5(
                        NAMESPACE_URL,
                        f"qore:vt31:nas100:m1:{opened.isoformat()}",
                    )
                ),
                instrument=_INSTRUMENT,
                source=_SOURCE,
                timeframe=_TIMEFRAME_M1,
                opened_at=opened,
                closed_at=opened + timedelta(minutes=1),
                open=float(item["open"]),
                high=float(item["high"]),
                low=float(item["low"]),
                close=float(item["close"]),
            )
        )
    return tuple(bars)


@cache
def _evaluate_pair(
    bars: tuple[OhlcSnapshot, ...],
) -> tuple[object, str, object, str, float]:
    fingerprint = _evidence_fingerprint(bars)
    full_basket, full_reason = evaluate_live_basket(
        closed_m1=bars,
        evidence_fingerprint=fingerprint,
        live_state=Vt31Nas100LiveState(),
    )
    prefix = bars[:-1]
    prepared = prepare_live_context(
        prefix,
        evidence_fingerprint=_evidence_fingerprint(prefix),
    )
    started = time.perf_counter_ns()
    resident_basket, resident_reason = evaluate_live_basket(
        closed_m1=bars,
        evidence_fingerprint=fingerprint,
        live_state=Vt31Nas100LiveState(),
        prepared_context=prepared,
    )
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return (
        full_basket,
        full_reason,
        resident_basket,
        resident_reason,
        elapsed_ms,
    )


def test_incident_candidate_is_bit_exact_after_resident_repair(
    incident_bars: tuple[OhlcSnapshot, ...],
) -> None:
    cibo_market_memory_fingerprint()
    full, full_reason, resident, resident_reason, elapsed_ms = _evaluate_pair(
        incident_bars
    )
    assert resident == full
    assert resident_reason == full_reason == "AUTHORIZED_SCOUT"
    assert resident is not None
    assert resident.basket_id == (
        "83bdf4cba5d5f40ade721cbce7b5eeae"
        "4792584c7f01524480a7ee625cf46395"
    )
    assert resident.authorized_at == "2026-09-22T14:26:00+00:00"
    assert resident.tier == "SCOUT"
    assert len(resident.candidates) == 1
    candidate = resident.candidates[0]
    assert candidate.signal_fingerprint == (
        "35906f24af2044397324603769f374343c8d0b01e"
        "1ea48538e458b7744ca2fdb"
    )
    assert candidate.candidate_id == "vt31-35906f24af20443973246037"
    assert candidate.side == "short"
    assert candidate.family == "fair-value-gap"
    assert candidate.entry_price == "30655.065"
    assert candidate.stop_loss == "30681.03"
    assert candidate.expires_at == "2026-09-22T15:00:00+00:00"
    assert elapsed_ms < 1000


def test_resident_policy_matches_live_session_prefix_outcomes(
    incident_bars: tuple[OhlcSnapshot, ...],
) -> None:
    cibo_market_memory_fingerprint()
    checked = 0
    for index, bar in enumerate(incident_bars):
        if not (
            datetime(2026, 9, 22, 14, 1, tzinfo=UTC)
            <= bar.closed_at
            <= datetime(2026, 9, 22, 14, 26, tzinfo=UTC)
        ):
            continue
        closed = incident_bars[: index + 1]
        prepared = prepare_live_context(
            closed[:-1],
            evidence_fingerprint=_evidence_fingerprint(closed[:-1]),
        )
        basket, reason = evaluate_live_basket(
            closed_m1=closed,
            evidence_fingerprint=_evidence_fingerprint(closed),
            live_state=Vt31Nas100LiveState(),
            prepared_context=prepared,
        )
        if bar.closed_at < datetime(2026, 9, 22, 14, 26, tzinfo=UTC):
            assert basket is None, bar.closed_at
            assert reason == "NO_AUTHORIZATION", bar.closed_at
        else:
            assert basket is not None
            assert reason == "AUTHORIZED_SCOUT"
        checked += 1
    assert checked == 26


def test_incremental_evidence_digest_matches_full_serialization(
    incident_bars: tuple[OhlcSnapshot, ...],
) -> None:
    from qore.infrastructure.vt31_nas100_live import (
        _evidence_prefix_hasher,
        _finish_evidence_fingerprint,
    )

    prefix = incident_bars[:-1]
    incremental = _finish_evidence_fingerprint(
        _evidence_prefix_hasher(prefix),
        incident_bars[-1],
        has_prefix=True,
    )
    assert incremental == _evidence_fingerprint(incident_bars)


def test_stale_single_is_retired_but_virtual_oco_remains(
    incident_bars: tuple[OhlcSnapshot, ...],
    tmp_path: Path,
) -> None:
    basket, reason, _, resident_reason, _ = _evaluate_pair(incident_bars)
    assert basket is not None
    assert reason == resident_reason == "AUTHORIZED_SCOUT"
    store = Vt31Nas100LiveStateStore(tmp_path / "vt31.json")
    store.mark_basket(basket)
    result, result_reason = evaluate_boundary(
        closed_m1=(),
        evidence_fingerprint="0" * 64,
        store=store,
    )
    assert result is None
    assert result_reason == "STALE_SINGLE_BASKET_RETIRED"
    state = store.load()
    assert state.virtual_basket is None
    assert basket.candidates[0].signal_fingerprint in (
        state.closed_signal_fingerprints
    )


    second = replace(
        basket.candidates[0],
        candidate_id="vt31-second",
        signal_fingerprint="1" * 64,
    )
    oco = replace(basket, candidates=(basket.candidates[0], second))
    store.mark_basket(oco)
    result, result_reason = evaluate_boundary(
        closed_m1=(),
        evidence_fingerprint="0" * 64,
        store=store,
    )
    assert result is None
    assert result_reason == "VIRTUAL_OCO_ACTIVE"
    assert store.load().virtual_basket == oco


def test_deadline_failure_retires_immediate_candidate(
    incident_bars: tuple[OhlcSnapshot, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basket, reason, _, _, _ = _evaluate_pair(incident_bars)
    assert basket is not None
    assert reason == "AUTHORIZED_SCOUT"
    store = Vt31Nas100LiveStateStore(tmp_path / "deadline.json")
    store.mark_basket(basket)

    def expire(**_kwargs: object) -> None:
        raise Vt31Nas100SlaExpired(
            "VT31 SLA_FAIL_CLOSED:before-symbol-read:deadline_exceeded"
        )

    monkeypatch.setattr(adapter, "_authorize_and_check", expire)
    with pytest.raises(Vt31Nas100SlaExpired):
        adapter.submit_single_live(
            basket=basket,
            boundary_at=datetime(2026, 9, 22, 14, 26, tzinfo=UTC),
            gateway=None,
            risk=None,
            snapshot=None,
            account_equity=Decimal("2000"),
            store=store,
            log=lambda _event: None,
        )
    state = store.load()
    assert state.virtual_basket is None
    assert basket.candidates[0].signal_fingerprint in (
        state.closed_signal_fingerprints
    )
