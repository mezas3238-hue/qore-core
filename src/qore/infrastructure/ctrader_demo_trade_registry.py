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
    receipt_id: str | None = None
    idempotency_key: str | None = None
    provider_symbol: str | None = None
    side: str | None = None
    entry_type: str | None = None
    intended_entry: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None
    volume_step: str | None = None
    minimum_volume: str | None = None
    stop_loss_per_volume: str | None = None
    margin_per_volume: str | None = None
    requested_at: str | None = None
    minimum_volume_uplifted: bool | None = None
    source_contract_size_units: str | None = None
    ctrader_lot_size_units: str | None = None
    capital_provenance: tuple[tuple[str, str, str], ...] = ()

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
            "receipt_id": self.receipt_id,
            "idempotency_key": self.idempotency_key,
            "provider_symbol": self.provider_symbol,
            "side": self.side,
            "entry_type": self.entry_type,
            "intended_entry": self.intended_entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "volume_step": self.volume_step,
            "minimum_volume": self.minimum_volume,
            "stop_loss_per_volume": self.stop_loss_per_volume,
            "margin_per_volume": self.margin_per_volume,
            "requested_at": self.requested_at,
            "minimum_volume_uplifted": self.minimum_volume_uplifted,
            "source_contract_size_units": self.source_contract_size_units,
            "ctrader_lot_size_units": self.ctrader_lot_size_units,
            "capital_provenance": [
                {
                    "source_kind": source_kind,
                    "source_id": source_id,
                    "amount_usd": amount_usd,
                }
                for source_kind, source_id, amount_usd in self.capital_provenance
            ],
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
            item["client_order_id"]: _entry_from_json(item)
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
        fd, name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
        )
        tmp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(
                    {
                        "schema": "qore.ctrader-demo.trade-registry.v2",
                        "entries": [
                            entries[key].as_json()
                            for key in sorted(entries)
                        ],
                    },
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



def _entry_from_json(value: object) -> DemoTradeRegistryEntry:
    if not isinstance(value, dict):
        raise RuntimeError("cTrader DEMO registry entry must be object")
    provenance_raw = value.get("capital_provenance", ())
    if not isinstance(provenance_raw, (list, tuple)):
        raise RuntimeError("cTrader DEMO registry provenance must be sequence")
    provenance: list[tuple[str, str, str]] = []
    for item in provenance_raw:
        if not isinstance(item, dict):
            raise RuntimeError("cTrader DEMO registry provenance row invalid")
        provenance.append(
            (
                str(item["source_kind"]),
                str(item["source_id"]),
                str(item["amount_usd"]),
            )
        )
    return DemoTradeRegistryEntry(
        trader=str(value["trader"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        request_id=str(value["request_id"]),
        client_order_id=str(value["client_order_id"]),
        provider_order_ref=str(value["provider_order_ref"]),
        qore_symbol=str(value["qore_symbol"]),
        requested_volume=str(value["requested_volume"]),
        requested_stop_risk=str(value["requested_stop_risk"]),
        submitted_at=str(value["submitted_at"]),
        expires_at=str(value["expires_at"]),
        position_id=(
            None
            if value.get("position_id") is None
            else int(str(value["position_id"]))
        ),
        receipt_id=(
            None if value.get("receipt_id") is None else str(value["receipt_id"])
        ),
        idempotency_key=(
            None
            if value.get("idempotency_key") is None
            else str(value["idempotency_key"])
        ),
        provider_symbol=(
            None
            if value.get("provider_symbol") is None
            else str(value["provider_symbol"])
        ),
        side=None if value.get("side") is None else str(value["side"]),
        entry_type=(
            None
            if value.get("entry_type") is None
            else str(value["entry_type"])
        ),
        intended_entry=(
            None
            if value.get("intended_entry") is None
            else str(value["intended_entry"])
        ),
        stop_loss=(
            None if value.get("stop_loss") is None else str(value["stop_loss"])
        ),
        take_profit=(
            None
            if value.get("take_profit") is None
            else str(value["take_profit"])
        ),
        volume_step=(
            None
            if value.get("volume_step") is None
            else str(value["volume_step"])
        ),
        minimum_volume=(
            None
            if value.get("minimum_volume") is None
            else str(value["minimum_volume"])
        ),
        stop_loss_per_volume=(
            None
            if value.get("stop_loss_per_volume") is None
            else str(value["stop_loss_per_volume"])
        ),
        margin_per_volume=(
            None
            if value.get("margin_per_volume") is None
            else str(value["margin_per_volume"])
        ),
        requested_at=(
            None
            if value.get("requested_at") is None
            else str(value["requested_at"])
        ),
        minimum_volume_uplifted=(
            None
            if value.get("minimum_volume_uplifted") is None
            else bool(value["minimum_volume_uplifted"])
        ),
        source_contract_size_units=(
            None
            if value.get("source_contract_size_units") is None
            else str(value["source_contract_size_units"])
        ),
        ctrader_lot_size_units=(
            None
            if value.get("ctrader_lot_size_units") is None
            else str(value["ctrader_lot_size_units"])
        ),
        capital_provenance=tuple(provenance),
    )
