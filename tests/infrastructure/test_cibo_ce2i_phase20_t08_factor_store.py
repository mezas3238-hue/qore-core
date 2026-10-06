from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_MARKET_SYMBOLS,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_store import (
    DurableT08FactorEvidenceError,
    DurableT08FactorEvidenceStore,
    T08FinalizedBoundaryOpen,
    build_delayed_t08_factor_snapshot,
    causal_t08_factor_return_history,
)

BASE = datetime(2026, 9, 29, 0, tzinfo=UTC)
PRICES = {
    "AUDJPY": Decimal("100"),
    "EURUSD": Decimal("1.10"),
    "GBPJPY": Decimal("190"),
    "GBPUSD": Decimal("1.25"),
    "NAS100": Decimal("20000"),
    "XAUUSD": Decimal("3800"),
}


def _opens(
    *,
    boundary_at: datetime,
    scale: Decimal = Decimal(1),
    finalized: bool = True,
) -> tuple[T08FinalizedBoundaryOpen, ...]:
    return tuple(
        T08FinalizedBoundaryOpen(
            qore_symbol=symbol,
            boundary_at=boundary_at,
            open_price=PRICES[symbol] * scale,
            observed_at=(
                boundary_at
                + timedelta(seconds=3, milliseconds=index * 20)
            ),
            evidence_ref=(
                f"finalized-m5:{boundary_at.isoformat()}:{symbol}"
            ),
            finalized=finalized,
        )
        for index, symbol in enumerate(FROZEN_T08_MARKET_SYMBOLS)
    )


def test_delayed_full_universe_snapshot_is_causal_not_sla_bound() -> None:
    snapshot = build_delayed_t08_factor_snapshot(
        provider_key="fundednext-mt5-observational",
        boundary_opens=_opens(boundary_at=BASE),
    )

    assert snapshot.market_at == BASE
    assert snapshot.observed_at > BASE + timedelta(seconds=3)
    assert snapshot.complete_frozen_universe is True
    assert snapshot.snapshot_id.startswith("sha256:")
    assert all(item.price_at == BASE for item in snapshot.marks)
    assert all(item.observed_at > BASE for item in snapshot.marks)


def test_delayed_snapshot_rejects_unfinalized_source_open() -> None:
    with pytest.raises(
        DurableT08FactorEvidenceError,
        match="finalized source opens",
    ):
        build_delayed_t08_factor_snapshot(
            provider_key="provider",
            boundary_opens=_opens(
                boundary_at=BASE,
                finalized=False,
            ),
        )


def test_delayed_snapshot_rejects_missing_market() -> None:
    with pytest.raises(
        DurableT08FactorEvidenceError,
        match="exact frozen universe",
    ):
        build_delayed_t08_factor_snapshot(
            provider_key="provider",
            boundary_opens=_opens(boundary_at=BASE)[:-1],
        )


def test_durable_store_is_append_only_and_chain_verified(tmp_path) -> None:
    store = DurableT08FactorEvidenceStore(tmp_path / "t08-factors.json")
    first = build_delayed_t08_factor_snapshot(
        provider_key="provider",
        boundary_opens=_opens(boundary_at=BASE),
    )
    second = build_delayed_t08_factor_snapshot(
        provider_key="provider",
        boundary_opens=_opens(
            boundary_at=BASE + timedelta(hours=1),
            scale=Decimal("1.01"),
        ),
    )

    book = store.append(first, expected_generation=0)
    assert book.generation == 1
    same = store.append(first, expected_generation=1)
    assert same == book
    book = store.append(second, expected_generation=1)

    reloaded = store.load()
    assert reloaded == book
    assert reloaded.generation == 2
    assert len(reloaded.snapshots) == 2
    assert reloaded.chain_sha256.startswith("sha256:")


def test_store_rejects_conflicting_same_provider_boundary(tmp_path) -> None:
    store = DurableT08FactorEvidenceStore(tmp_path / "t08-factors.json")
    first = build_delayed_t08_factor_snapshot(
        provider_key="provider",
        boundary_opens=_opens(boundary_at=BASE),
    )
    changed = tuple(
        (
            T08FinalizedBoundaryOpen(
                qore_symbol=item.qore_symbol,
                boundary_at=item.boundary_at,
                open_price=(
                    item.open_price + Decimal("1")
                    if item.qore_symbol == "NAS100"
                    else item.open_price
                ),
                observed_at=item.observed_at,
                evidence_ref=item.evidence_ref + ":changed",
                finalized=True,
            )
        )
        for item in _opens(boundary_at=BASE)
    )
    conflict = build_delayed_t08_factor_snapshot(
        provider_key="provider",
        boundary_opens=changed,
    )

    store.append(first, expected_generation=0)
    with pytest.raises(
        DurableT08FactorEvidenceError,
        match="conflicting snapshot",
    ):
        store.append(conflict, expected_generation=1)


def test_history_excludes_snapshot_not_known_by_decision(tmp_path) -> None:
    store = DurableT08FactorEvidenceStore(tmp_path / "t08-factors.json")
    boundaries = (BASE, BASE + timedelta(hours=1), BASE + timedelta(hours=2))
    book = store.load()
    for index, boundary in enumerate(boundaries):
        snapshot = build_delayed_t08_factor_snapshot(
            provider_key="provider",
            boundary_opens=_opens(
                boundary_at=boundary,
                scale=Decimal(1) + Decimal(index) / Decimal("100"),
            ),
        )
        book = store.append(
            snapshot,
            expected_generation=book.generation,
        )

    second_known_at = book.snapshots[1].observed_at
    before_third_known = book.snapshots[2].observed_at - timedelta(microseconds=1)

    first_history = causal_t08_factor_return_history(
        book,
        known_by=second_known_at,
    )
    second_history = causal_t08_factor_return_history(
        book,
        known_by=before_third_known,
    )

    assert len(first_history) == 1
    assert len(second_history) == 1
    assert first_history[0].known_at == second_known_at
    assert second_history[0].known_at == second_known_at
