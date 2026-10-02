"""Boundary-timed cTrader DEMO account snapshots."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from datetime import UTC, datetime, timedelta
from threading import Lock, Timer

from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState


class BoundaryAccountSnapshotError(RuntimeError):
    """Account evidence was not captured inside its boundary contract."""


class BoundaryAccountSampler:
    """Capture one broker account snapshot per boundary, concurrently."""

    __slots__ = ("_clock", "_futures", "_lock", "_reader")

    def __init__(
        self,
        reader: Callable[[], CTraderDemoAccountState],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._reader = reader
        self._clock = clock or (lambda: datetime.now(UTC))
        self._futures: dict[datetime, Future[CTraderDemoAccountState]] = {}
        self._lock = Lock()

    def arm(self, boundary_at: datetime) -> Future[CTraderDemoAccountState]:
        self._validate_time(boundary_at, "boundary_at")
        with self._lock:
            existing = self._futures.get(boundary_at)
            if existing is not None:
                return existing
            self._prune(boundary_at)
            future: Future[CTraderDemoAccountState] = Future()
            self._futures[boundary_at] = future
            delay = max(
                0.0,
                (boundary_at - self._clock()).total_seconds(),
            )
            timer = Timer(delay, self._capture, args=(future,))
            timer.name = "qore-ctrader-demo-boundary-account"
            timer.daemon = True
            timer.start()
            return future

    def resolve(
        self,
        boundary_at: datetime,
        deadline_at: datetime,
    ) -> CTraderDemoAccountState:
        self._validate_time(boundary_at, "boundary_at")
        self._validate_time(deadline_at, "deadline_at")
        if deadline_at <= boundary_at:
            raise BoundaryAccountSnapshotError("account snapshot deadline must follow boundary")
        future = self.arm(boundary_at)
        remaining = max(0.0, (deadline_at - self._clock()).total_seconds())
        try:
            snapshot = future.result(timeout=remaining)
        except FutureTimeoutError as error:
            raise BoundaryAccountSnapshotError(
                "account snapshot unavailable within boundary deadline"
            ) from error
        if snapshot.observed_at < boundary_at:
            raise BoundaryAccountSnapshotError("account snapshot predates boundary")
        if snapshot.observed_at > deadline_at:
            raise BoundaryAccountSnapshotError("account snapshot completed after boundary deadline")
        return snapshot

    def _capture(self, future: Future[CTraderDemoAccountState]) -> None:
        try:
            snapshot = self._reader()
        except Exception as error:
            future.set_exception(error)
        else:
            future.set_result(snapshot)

    def _prune(self, boundary_at: datetime) -> None:
        cutoff = boundary_at - timedelta(minutes=10)
        for key, future in tuple(self._futures.items()):
            if key < cutoff and future.done():
                del self._futures[key]

    @staticmethod
    def _validate_time(value: datetime, name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise BoundaryAccountSnapshotError(f"{name} must be timezone-aware")
