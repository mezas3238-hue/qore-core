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

from qore.infrastructure.account_wide_risk import AccountWideRiskError
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
    Path(__file__).parents[1] / "fixtures" / "vt31_nas100_20260922_1426.json.gz"
)
_INCIDENT_20260923_FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "vt31_nas100_20260923_1416.json.gz"
)


def _load_bars(path: Path) -> tuple[OhlcSnapshot, ...]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["schema"] == "qore.vt31.live_replay.v1"
    bars = []
    for item in payload["bars"]:
        opened = datetime.fromisoformat(item["opened_at"]).astimezone(UTC)
        bars.append(
            OhlcSnapshot(
                snapshot_id=MarketDataSnapshotId(
                    uuid5(NAMESPACE_URL, f"qore:vt31:nas100:m1:{opened.isoformat()}")
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


@pytest.fixture(scope="module")
def incident_bars() -> tuple[OhlcSnapshot, ...]:
    return _load_bars(_FIXTURE)


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


def test_stale_single_is_released_without_false_close_but_virtual_oco_remains(
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
    assert result_reason == "STALE_SINGLE_BASKET_RELEASED"
    state = store.load()
    fingerprint = basket.candidates[0].signal_fingerprint
    assert state.virtual_basket is None
    assert fingerprint not in state.closed_signal_fingerprints
    assert fingerprint not in state.processed_baskets

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


def test_deadline_failure_releases_immediate_candidate_for_retry(
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
    fingerprint = basket.candidates[0].signal_fingerprint
    assert state.virtual_basket is None
    assert fingerprint not in state.closed_signal_fingerprints
    assert fingerprint not in state.processed_baskets


def test_stale_boot_risk_failure_does_not_consume_signal(
    incident_bars: tuple[OhlcSnapshot, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basket, reason, _, _, _ = _evaluate_pair(incident_bars)
    assert basket is not None
    assert reason == "AUTHORIZED_SCOUT"
    store = Vt31Nas100LiveStateStore(tmp_path / "stale-risk.json")
    store.mark_basket(basket)

    def stale(**_kwargs: object) -> None:
        raise AccountWideRiskError("boot reconciliation snapshot is stale")

    monkeypatch.setattr(adapter, "_authorize_and_check", stale)
    with pytest.raises(AccountWideRiskError, match="snapshot is stale"):
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
    fingerprint = basket.candidates[0].signal_fingerprint
    assert state.virtual_basket is None
    assert fingerprint not in state.closed_signal_fingerprints
    assert fingerprint not in state.processed_baskets


def test_owner_incident_20260923_1416_replays_bit_exact() -> None:
    bars = _load_bars(_INCIDENT_20260923_FIXTURE)
    full, full_reason, resident, resident_reason, _ = _evaluate_pair(bars)
    assert resident == full
    assert resident_reason == full_reason == "AUTHORIZED_SECONDARY"
    assert resident is not None
    assert resident.basket_id == (
        "c6e343e233b6f3f153f107e7c73f816"
        "f33353e60020832bc155ab2fec08c584f"
    )
    assert resident.tier == "SECONDARY"
    assert len(resident.candidates) == 1
    candidate = resident.candidates[0]
    assert candidate.candidate_id == "vt31-cc6ad8cd3eb79ea6cc00c038"
    assert candidate.signal_fingerprint == (
        "cc6ad8cd3eb79ea6cc00c038ac067952"
        "0ef5c4c2404c6160c8081f69f361e749"
    )
    assert candidate.side == "long"
    assert candidate.family == "breaker"
    assert candidate.entry_price == "30426.23"
    assert candidate.stop_loss == "30411.45"
    assert candidate.expires_at == "2026-09-23T15:00:00+00:00"


def test_owner_incident_20260923_reaches_shadow_order_check_without_send(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from qore.infrastructure.account_wide_risk import AccountRiskSnapshot
    from qore.infrastructure.account_wide_risk_ledger import (
        DurableAccountWideRiskEngine,
        DurableAccountWideRiskLedger,
    )
    from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
    from qore.infrastructure.fundednext_stellar_instant import (
        StellarInstantAccountSnapshot,
        evaluate_stellar_instant_budget,
    )

    bars = _load_bars(_INCIDENT_20260923_FIXTURE)
    _, _, basket, reason, _ = _evaluate_pair(bars)
    assert basket is not None and reason == "AUTHORIZED_SECONDARY"
    order = basket.candidates[0]
    fixed = datetime(2026, 9, 23, 14, 16, 1, 700000, tzinfo=UTC)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return fixed if tz is None else fixed.astimezone(tz)

    monkeypatch.setattr(adapter, "datetime", FrozenDateTime)
    spec = Mt5SymbolSpecification(
        provider_symbol="NDX100",
        bid=Decimal("30445.80"),
        ask=Decimal("30446.00"),
        spread_points=Decimal("20"),
        digits=2,
        point=Decimal("0.01"),
        contract_size=Decimal("10"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("0.1"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("40"),
        volume_step=Decimal("0.01"),
        minimum_stop_distance_points=Decimal("0"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("100"),
        trade_enabled=True,
        session_open=True,
        observed_at=fixed,
    )
    checks: list[object] = []

    class Gateway:
        has_unresolved_mutations = False

        def read_symbol(self, _symbol: str, *, now: datetime) -> Mt5SymbolSpecification:
            return spec

        def shadow_check(self, submission: object, *, now: datetime) -> object:
            checks.append(submission)
            return SimpleNamespace(broker_valid=True, reason="mt5-order-check-ok", retcode=0)
    provider = evaluate_stellar_instant_budget(
        StellarInstantAccountSnapshot(
            initial_balance=Decimal("2000"),
            balance=Decimal("2000"),
            equity=Decimal("2000"),
            highest_closed_balance=Decimal("2000"),
            previous_active_mll=Decimal("1880"),
        )
    )
    snapshot = AccountRiskSnapshot(
        account_binding_id="f" * 64,
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("2000"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("60"),
        provider_budget=provider,
        reconciled_at=fixed,
    )
    risk = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "incident-risk.json")
    )
    store = Vt31Nas100LiveStateStore(tmp_path / "incident-state.json")
    events: list[dict[str, object]] = []
    adapter._authorize_and_check(
        order=order,
        trigger_at=datetime(2026, 9, 23, 14, 16, tzinfo=UTC),
        mode="shadow",
        gateway=Gateway(),
        risk=risk,
        snapshot=snapshot,
        account_equity=Decimal("2000"),
        store=store,
        log=events.append,
    )

    sizing = next(event for event in events if event["event"] == "VT31_BROKER_SIZING")
    assert sizing["candidate_id"] == "vt31-cc6ad8cd3eb79ea6cc00c038"
    assert sizing["requested_risk_usd"] == "6.03024"
    assert sizing["requested_volume"] == "0.04"
    assert sizing["broker_minimum_volume"] == "0.04"
    assert len(checks) == 1
    assert any(event["event"] == "VT31_ORDER_CHECK" for event in events)
    assert any(event["event"] == "VT31_NAS100_SHADOW_PASS" for event in events)
    assert store.load().pending_broker_order is None
