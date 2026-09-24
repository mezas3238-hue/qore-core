from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2 import (
    CoreStackV2Runtime,
    MarketEvent,
    freeze_facts,
)


NOW = datetime(2026, 9, 23, 20, 0, 1, tzinfo=UTC)


def _event(event_id: str, sequence: int, seconds_ago: int) -> MarketEvent:
    at = NOW - timedelta(seconds=seconds_ago)
    return MarketEvent(
        event_id=event_id,
        market="NAS100",
        event_type="STRUCTURE_CHANGE",
        source_at=at,
        observed_at=at,
        sequence=sequence,
        complete=True,
        timeframe_seconds=None,
        facts=freeze_facts(
            {
                "market_state": "ACTIVE",
                "structure_state": f"S{sequence}",
            }
        ),
    )


@dataclass(slots=True)
class RecordingConsumer:
    trader_id: str
    markets: tuple[str, ...]
    snapshot_ids: list[str] = field(default_factory=list)

    def consume(self, snapshot: object) -> None:
        self.snapshot_ids.append(getattr(snapshot, "snapshot_id"))


@dataclass(slots=True)
class FailingConsumer:
    trader_id: str = "BROKEN_SHADOW"
    markets: tuple[str, ...] = ("NAS100",)

    def consume(self, snapshot: object) -> None:
        _ = snapshot
        raise RuntimeError("injected adapter failure")


def test_runtime_updates_once_and_fans_out_same_snapshot() -> None:
    first = RecordingConsumer("VT31", ("NAS100",))
    second = RecordingConsumer("CAPITALIZER_SHADOW", ("NAS100",))
    runtime = CoreStackV2Runtime(consumers=(first, second))

    result = runtime.ingest(
        _event("e1", 1, 0),
        generated_at=NOW,
    )

    assert result.fanout_complete is True
    assert len(result.deliveries) == 2
    assert first.snapshot_ids == [result.snapshot.snapshot_id]
    assert second.snapshot_ids == [result.snapshot.snapshot_id]


def test_consumer_failure_is_explicit_and_isolated() -> None:
    healthy = RecordingConsumer("VT31", ("NAS100",))
    broken = FailingConsumer()
    runtime = CoreStackV2Runtime(consumers=(broken, healthy))

    result = runtime.ingest(
        _event("e1", 1, 0),
        generated_at=NOW,
    )

    assert result.fanout_complete is False
    assert [item.delivered for item in result.deliveries] == [False, True]
    assert healthy.snapshot_ids == [result.snapshot.snapshot_id]
    assert "RuntimeError:injected adapter failure" == result.deliveries[0].error


def test_restart_rebuild_is_deterministic() -> None:
    runtime = CoreStackV2Runtime()
    runtime.ingest(_event("e1", 1, 1), generated_at=NOW)
    before = runtime.ingest(_event("e2", 2, 0), generated_at=NOW).snapshot
    checkpoint = runtime.checkpoint("NAS100")

    restored = CoreStackV2Runtime.from_checkpoint(checkpoint)
    after = restored.rebuild(market="NAS100", generated_at=NOW)

    assert restored.checkpoint("NAS100").fingerprint() == checkpoint.fingerprint()
    assert after == before
    assert after.fingerprint() == before.fingerprint()


def test_market_subscription_isolation() -> None:
    other = RecordingConsumer("OTHER_MARKET", ("XAUUSD",))
    runtime = CoreStackV2Runtime(consumers=(other,))
    result = runtime.ingest(_event("e1", 1, 0), generated_at=NOW)

    assert result.deliveries == ()
    assert result.fanout_complete is True
    assert other.snapshot_ids == []
