from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.fundednext_position_exit_ledger import (
    JsonFileFundedNextPositionExitLedger,
    PositionExitRecord,
    PositionExitState,
)

_NOW = datetime(2026, 9, 15, 17, 0, tzinfo=UTC)


def _record() -> PositionExitRecord:
    return PositionExitRecord(
        source_client_order_id="qore-source-1",
        provider_position_ref="9001",
        symbol="GBPUSD",
        magic=12345,
        due_at=_NOW,
        state=PositionExitState.ATTEMPT_STARTED,
        transitioned_at=_NOW,
    )


def test_exit_fence_survives_restart_and_becomes_unknown(tmp_path: Path) -> None:
    path = tmp_path / "exits.json"
    ledger = JsonFileFundedNextPositionExitLedger(path)
    ledger.upsert(_record())
    restored = JsonFileFundedNextPositionExitLedger(path)
    restored.mark_interrupted_unknown(now=_NOW + timedelta(seconds=1))
    record = restored.records()[0]
    assert record.state is PositionExitState.OUTCOME_UNKNOWN
    assert restored.has_unresolved is True


def test_definitive_exit_completion_clears_unresolved_fence(tmp_path: Path) -> None:
    ledger = JsonFileFundedNextPositionExitLedger(tmp_path / "exits.json")
    record = _record().transition(
        state=PositionExitState.ACCEPTED,
        transitioned_at=_NOW + timedelta(seconds=1),
        provider_deal_ref="8001",
    )
    ledger.upsert(record)
    assert ledger.has_unresolved is False
