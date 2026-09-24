from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from threading import Lock


@dataclass(frozen=True, slots=True)
class DemoTradeRegistryEntry:
    trader: str
    signal_fingerprint: str
    request_id: str
    client_order_id: str
    provider_order_ref: str
    qore_symbol: str
    requested_volume: str
    requested_stop_risk: str
    submitted_at: str
    expires_at: str
    position_id: int | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "trader": self.trader,
            "signal_fingerprint": self.signal_fingerprint,
            "request_id": self.request_id,
            "client_order_id": self.client_order_id,
            "provider_order_ref": self.provider_order_ref,
            "qore_symbol": self.qore_symbol,
            "requested_volume": self.requested_volume,
            "requested_stop_risk": self.requested_stop_risk,
            "submitted_at": self.submitted_at,
            "expires_at": self.expires_at,
            "position_id": self.position_id,
        }


class CTraderDemoTradeRegistry:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._entries = self._load()

    def _load(self) -> dict[str, DemoTradeRegistryEntry]:
        if not self._path.exists():
            return {}
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return {
            item["client_order_id"]: DemoTradeRegistryEntry(**item)
            for item in raw.get("entries", ())
        }

    def entries(self) -> tuple[DemoTradeRegistryEntry, ...]:
        with self._lock:
            return tuple(self._entries[key] for key in sorted(self._entries))

    def register(self, entry: DemoTradeRegistryEntry) -> None:
        with self._lock:
            current = self._entries.get(entry.client_order_id)
            if current is not None and current != entry:
                if (
                    current.trader != entry.trader
                    or current.signal_fingerprint != entry.signal_fingerprint
                    or current.provider_order_ref != entry.provider_order_ref
                ):
                    raise RuntimeError("cTrader DEMO registry identity conflict")
                if current.position_id is not None and entry.position_id is None:
                    entry = current
            next_entries = dict(self._entries)
            next_entries[entry.client_order_id] = entry
            self._commit(next_entries)
            self._entries = next_entries

    def bind_position(self, client_order_id: str, position_id: int) -> DemoTradeRegistryEntry:
        if position_id <= 0:
            raise ValueError("position_id must be positive")
        with self._lock:
            current = self._entries[client_order_id]
            if current.position_id is not None and current.position_id != position_id:
                raise RuntimeError("cTrader DEMO registry position conflict")
            updated = replace(current, position_id=position_id)
            next_entries = dict(self._entries)
            next_entries[client_order_id] = updated
            self._commit(next_entries)
            self._entries = next_entries
            return updated

    def entries_by_position(
        self,
        position_id: int,
    ) -> tuple[DemoTradeRegistryEntry, ...]:
        with self._lock:
            matches = [
                item
                for item in self._entries.values()
                if item.position_id == position_id
            ]
        return tuple(
            sorted(
                matches,
                key=lambda item: (
                    datetime.fromisoformat(item.submitted_at),
                    item.client_order_id,
                ),
            )
        )

    def by_position(self, position_id: int) -> DemoTradeRegistryEntry | None:
        """Return the stable primary leg for a broker position.

        A cTrader netting account can aggregate several legitimate CIBO
        submissions into one position id.  Keep all legs in the registry and
        expose the earliest leg as the canonical management identity.
        """
        matches = self.entries_by_position(position_id)
        return matches[0] if matches else None

    def latest_for_trader(self, trader: str) -> DemoTradeRegistryEntry | None:
        with self._lock:
            matches = [item for item in self._entries.values() if item.trader == trader]
        if not matches:
            return None
        return max(matches, key=lambda item: datetime.fromisoformat(item.submitted_at))

    def _commit(self, entries: dict[str, DemoTradeRegistryEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=f".{self._path.name}.", suffix=".tmp", dir=self._path.parent)
        tmp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(
                    {"schema": "qore.ctrader-demo.trade-registry.v1", "entries": [entries[k].as_json() for k in sorted(entries)]},
                    stream,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self._path)
        finally:
            if tmp.exists():
                tmp.unlink()
