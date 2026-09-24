"""Independent resident-market analysis scheduling for critical boundaries.

The scheduler coordinates pure, preprepared strategy evaluation only. Broker
mutations remain outside this module and must pass through the runtime's single
QORE Risk arbiter and single MT5 writer.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class MarketBoundaryJob:
    identity: str
    symbol: str
    evaluate: Callable[[], tuple[Any | None, str]]


@dataclass(frozen=True, slots=True)
class MarketBoundaryResult:
    identity: str
    symbol: str
    strategy_started_at: datetime
    strategy_finished_at: datetime
    signal: Any | None
    reason: str | None
    error: Exception | None

    @property
    def strategy_latency_ms(self) -> int:
        return int((self.strategy_finished_at - self.strategy_started_at).total_seconds() * 1000)


class ResidentMarketActorPool:
    """Run each market as soon as its own boundary snapshot is available."""

    def __init__(
        self,
        *,
        max_workers: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if max_workers <= 0:
            raise ValueError("market actor worker count must be positive")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="qore-market-actor",
        )
        self._futures: dict[str, Future[MarketBoundaryResult]] = {}
        self._delivered: set[str] = set()

    def __enter__(self) -> ResidentMarketActorPool:
        return self

    def __exit__(self, *_: object) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)

    def submit(self, job: MarketBoundaryJob) -> None:
        if job.identity in self._futures:
            raise ValueError(f"duplicate market boundary job:{job.identity}")
        self._futures[job.identity] = self._executor.submit(
            _evaluate_job,
            job,
            self._clock,
        )

    def ready_results(self) -> tuple[MarketBoundaryResult, ...]:
        """Return newly completed market results without blocking siblings."""

        ready: list[MarketBoundaryResult] = []
        for identity, future in self._futures.items():
            if identity in self._delivered or not future.done():
                continue
            ready.append(future.result())
            self._delivered.add(identity)
        return tuple(ready)

    def pending_identities(self) -> tuple[str, ...]:
        return tuple(
            identity for identity in self._futures if identity not in self._delivered
        )

    def submitted_identities(self) -> tuple[str, ...]:
        return tuple(self._futures)

    def results(self) -> tuple[MarketBoundaryResult, ...]:
        return tuple(future.result() for future in self._futures.values())


def _evaluate_job(
    job: MarketBoundaryJob,
    clock: Callable[[], datetime],
) -> MarketBoundaryResult:
    started = clock().astimezone(UTC)
    try:
        signal, reason = job.evaluate()
    except Exception as error:
        return MarketBoundaryResult(
            identity=job.identity,
            symbol=job.symbol,
            strategy_started_at=started,
            strategy_finished_at=clock().astimezone(UTC),
            signal=None,
            reason=None,
            error=error,
        )
    return MarketBoundaryResult(
        identity=job.identity,
        symbol=job.symbol,
        strategy_started_at=started,
        strategy_finished_at=clock().astimezone(UTC),
        signal=signal,
        reason=reason,
        error=None,
    )


def evaluate_market_boundaries(
    jobs: Sequence[MarketBoundaryJob],
    *,
    clock: Callable[[], datetime] | None = None,
) -> tuple[MarketBoundaryResult, ...]:
    """Start all prepared market analyses independently at one release point."""

    if not jobs:
        return ()
    identities = tuple(job.identity for job in jobs)
    if len(set(identities)) != len(identities):
        raise ValueError("market boundary job identities must be unique")
    now = clock or (lambda: datetime.now(UTC))
    ready = threading.Barrier(len(jobs) + 1)

    def evaluate(job: MarketBoundaryJob) -> MarketBoundaryResult:
        ready.wait()
        return _evaluate_job(job, now)

    with ThreadPoolExecutor(
        max_workers=len(jobs),
        thread_name_prefix="qore-market-actor",
    ) as executor:
        futures = tuple(executor.submit(evaluate, job) for job in jobs)
        ready.wait()
        results = tuple(future.result() for future in futures)
    return results
