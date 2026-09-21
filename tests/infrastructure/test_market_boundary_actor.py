from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from qore.infrastructure.market_boundary_actor import (
    MarketBoundaryJob,
    ResidentMarketActorPool,
    evaluate_market_boundaries,
)


def test_all_market_actors_enter_strategy_before_any_finishes() -> None:
    entered = 0
    lock = threading.Lock()
    all_entered = threading.Event()

    def evaluator(name: str):  # type: ignore[no-untyped-def]
        def run() -> tuple[None, str]:
            nonlocal entered
            with lock:
                entered += 1
                if entered == 5:
                    all_entered.set()
            assert all_entered.wait(timeout=1)
            return None, f"{name}-abstain"

        return run

    jobs = tuple(
        MarketBoundaryJob(
            identity=f"TRADER_{index}",
            symbol=symbol,
            evaluate=evaluator(symbol),
        )
        for index, symbol in enumerate(("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY"))
    )
    results = evaluate_market_boundaries(jobs)

    assert entered == 5
    assert tuple(item.identity for item in results) == tuple(item.identity for item in jobs)
    assert all(item.error is None for item in results)
    assert all(item.signal is None for item in results)


def test_market_actor_failure_is_isolated_from_siblings() -> None:
    def fail() -> tuple[None, str]:
        raise RuntimeError("market-local failure")

    jobs = (
        MarketBoundaryJob("A", "XAUUSD", lambda: (None, "abstain")),
        MarketBoundaryJob("B", "EURUSD", fail),
    )
    values = iter(
        datetime(2026, 9, 21, 13, 0, tzinfo=UTC) + timedelta(milliseconds=index)
        for index in range(8)
    )
    results = evaluate_market_boundaries(jobs, clock=lambda: next(values))

    assert results[0].reason == "abstain"
    assert results[0].error is None
    assert isinstance(results[1].error, RuntimeError)


def test_resident_actor_starts_before_later_market_is_submitted() -> None:
    first_started = threading.Event()
    release_first = threading.Event()

    def first() -> tuple[None, str]:
        first_started.set()
        assert release_first.wait(timeout=1)
        return None, "first"

    with ResidentMarketActorPool(max_workers=2) as actors:
        actors.submit(MarketBoundaryJob("first", "GBPUSD", first))
        assert first_started.wait(timeout=1)
        actors.submit(MarketBoundaryJob("second", "XAUUSD", lambda: (None, "second")))
        release_first.set()
        results = actors.results()

    assert [item.identity for item in results] == ["first", "second"]
