from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.ctrader_demo_boundary_account import (
    BoundaryAccountSampler,
    BoundaryAccountSnapshotError,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState


def _state(observed_at: datetime) -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal("100000"),
        equity=Decimal("100000"),
        margin=Decimal("0"),
        free_margin=Decimal("100000"),
        observed_at=observed_at,
    )


def test_boundary_capture_is_shared_and_never_prearm() -> None:
    calls: list[datetime] = []

    def read_account() -> CTraderDemoAccountState:
        observed_at = datetime.now(UTC)
        calls.append(observed_at)
        return _state(observed_at)

    sampler = BoundaryAccountSampler(read_account)
    boundary_at = datetime.now(UTC) + timedelta(milliseconds=30)
    first = sampler.arm(boundary_at)
    second = sampler.arm(boundary_at)

    assert first is second
    snapshot = sampler.resolve(
        boundary_at,
        boundary_at + timedelta(seconds=1),
    )

    assert snapshot.observed_at >= boundary_at
    assert len(calls) == 1


def test_boundary_capture_rejects_preboundary_evidence() -> None:
    boundary_at = datetime.now(UTC)
    sampler = BoundaryAccountSampler(lambda: _state(boundary_at - timedelta(milliseconds=1)))

    with pytest.raises(
        BoundaryAccountSnapshotError,
        match="predates boundary",
    ):
        sampler.resolve(
            boundary_at,
            boundary_at + timedelta(seconds=1),
        )


def test_boundary_capture_rejects_postdeadline_evidence() -> None:
    boundary_at = datetime.now(UTC)
    deadline_at = boundary_at + timedelta(seconds=1)
    sampler = BoundaryAccountSampler(lambda: _state(deadline_at + timedelta(milliseconds=1)))

    with pytest.raises(
        BoundaryAccountSnapshotError,
        match="completed after boundary deadline",
    ):
        sampler.resolve(boundary_at, deadline_at)
