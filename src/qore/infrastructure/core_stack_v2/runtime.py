"""Event-driven single-update runtime for QORE CORE STACK V2 shadow research."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from qore.infrastructure.core_stack_v2.contracts import (
    CoreHypothesis,
    CoreSnapshot,
    MarketEvent,
    PortfolioIntent,
)
from qore.infrastructure.core_stack_v2.engine import CoreStackConfig, build_snapshot


class SnapshotConsumer(Protocol):
    @property
    def trader_id(self) -> str: ...

    @property
    def markets(self) -> tuple[str, ...]: ...

    def consume(self, snapshot: CoreSnapshot) -> None: ...


@dataclass(frozen=True, slots=True)
class SnapshotDelivery:
    trader_id: str
    snapshot_id: str
    delivered: bool
    error: str | None


@dataclass(frozen=True, slots=True)
class CoreRuntimeResult:
    snapshot: CoreSnapshot
    deliveries: tuple[SnapshotDelivery, ...]
    fanout_complete: bool


@dataclass(frozen=True, slots=True)
class CoreRuntimeCheckpoint:
    market: str
    events: tuple[MarketEvent, ...]

    def __post_init__(self) -> None:
        if not self.market:
            raise ValueError("checkpoint market must be non-empty")
        if any(event.market != self.market for event in self.events):
            raise ValueError("checkpoint cannot mix markets")

    def fingerprint(self) -> str:
        material = {
            "market": self.market,
            "events": [event.fingerprint() for event in self.events],
        }
        raw = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


class CoreStackV2Runtime:
    """Update Shared Core once, then fan out the same immutable snapshot."""

    def __init__(
        self,
        *,
        consumers: tuple[SnapshotConsumer, ...] = (),
        config: CoreStackConfig | None = None,
    ) -> None:
        self._consumers = consumers
        self._config = config or CoreStackConfig()
        self._events_by_market: dict[str, list[MarketEvent]] = {}

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: CoreRuntimeCheckpoint,
        *,
        consumers: tuple[SnapshotConsumer, ...] = (),
        config: CoreStackConfig | None = None,
    ) -> CoreStackV2Runtime:
        runtime = cls(consumers=consumers, config=config)
        runtime._events_by_market[checkpoint.market] = list(checkpoint.events)
        return runtime

    def checkpoint(self, market: str) -> CoreRuntimeCheckpoint:
        return CoreRuntimeCheckpoint(
            market=market,
            events=tuple(self._events_by_market.get(market, ())),
        )

    def rebuild(
        self,
        *,
        market: str,
        generated_at: datetime,
        hypotheses: tuple[CoreHypothesis, ...] = (),
        portfolio_intents: tuple[PortfolioIntent, ...] = (),
        cross_market_facts: dict[str, str] | None = None,
    ) -> CoreSnapshot:
        events = tuple(self._events_by_market.get(market, ()))
        if not events:
            raise ValueError("cannot rebuild a market without retained events")
        return build_snapshot(
            events=events,
            generated_at=generated_at,
            hypotheses=hypotheses,
            portfolio_intents=portfolio_intents,
            cross_market_facts=cross_market_facts,
            config=self._config,
        )

    def ingest(
        self,
        event: MarketEvent,
        *,
        generated_at: datetime,
        hypotheses: tuple[CoreHypothesis, ...] = (),
        portfolio_intents: tuple[PortfolioIntent, ...] = (),
        cross_market_facts: dict[str, str] | None = None,
    ) -> CoreRuntimeResult:
        retained = self._events_by_market.setdefault(event.market, [])
        retained.append(event)
        snapshot = build_snapshot(
            events=tuple(retained),
            generated_at=generated_at,
            hypotheses=hypotheses,
            portfolio_intents=portfolio_intents,
            cross_market_facts=cross_market_facts,
            config=self._config,
        )

        deliveries: list[SnapshotDelivery] = []
        for consumer in self._consumers:
            if event.market not in consumer.markets:
                continue
            try:
                consumer.consume(snapshot)
            except Exception as exc:
                deliveries.append(
                    SnapshotDelivery(
                        trader_id=consumer.trader_id,
                        snapshot_id=snapshot.snapshot_id,
                        delivered=False,
                        error=f"{type(exc).__name__}:{exc}",
                    )
                )
            else:
                deliveries.append(
                    SnapshotDelivery(
                        trader_id=consumer.trader_id,
                        snapshot_id=snapshot.snapshot_id,
                        delivered=True,
                        error=None,
                    )
                )

        return CoreRuntimeResult(
            snapshot=snapshot,
            deliveries=tuple(deliveries),
            fanout_complete=all(item.delivered for item in deliveries),
        )
