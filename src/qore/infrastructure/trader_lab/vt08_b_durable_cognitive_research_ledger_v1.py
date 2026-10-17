"""VT08 B crash-safe, research-only SQLite WAL lifecycle evidence barrier.

Independent of source discovery and any execution broker. A ledger record only
authenticates *internal continuity*: an arbitrary caller-provided SHA is NOT
proof of the corresponding cTrader bar or broker order. Full cognitive state
rehydration and actual execution ingestion remain separate future contracts.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

HEX: Final = re.compile(r"[0-9a-f]{64}\Z")
EVENT_KINDS: Final = frozenset(
    ("WAIT", "ABSTAIN", "EXECUTE", "FILL", "POSITION", "TERMINAL")
)
DECISIONS: Final = frozenset(("WAIT", "ABSTAIN", "EXECUTE"))
ZERO: Final = "0" * 64


def _utc_time(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("VT08 WAL requires aware UTC-comparable timestamp")
    if value.utcoffset() is None:
        raise ValueError("VT08 WAL timestamp requires valid UTC offset")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise ValueError(f"VT08 WAL invalid SHA256 for {name}")


def _digest(data: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            data, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class Vt08WalReceipt:
    seq: int
    source_event_id: str
    market: str
    kind: str
    as_of_utc: str
    identity_sha256: str
    evidence_sha256: str
    event_key: str
    fill_id: str | None
    previous_sha256: str
    entry_sha256: str
    inserted: bool
    research_only: bool = True
    broker_authorized: bool = False


def _record(row: tuple[object, ...], *, inserted: bool) -> Vt08WalReceipt:
    return Vt08WalReceipt(
        seq=int(str(row[0])),
        source_event_id=str(row[1]),
        market=str(row[2]),
        kind=str(row[3]),
        as_of_utc=str(row[4]),
        identity_sha256=str(row[5]),
        evidence_sha256=str(row[6]),
        event_key=str(row[7]),
        fill_id=None if row[8] is None else str(row[8]),
        previous_sha256=str(row[9]),
        entry_sha256=str(row[10]),
        inserted=inserted,
    )


def _chain_payload(record: Vt08WalReceipt) -> dict[str, object]:
    return {
        "seq": record.seq,
        "source_event_id": record.source_event_id,
        "market": record.market,
        "kind": record.kind,
        "as_of_utc": record.as_of_utc,
        "identity_sha256": record.identity_sha256,
        "evidence_sha256": record.evidence_sha256,
        "event_key": record.event_key,
        "fill_id": record.fill_id,
        "previous_sha256": record.previous_sha256,
    }


class Vt08DurableResearchLedger:
    """Transactional WAL with duplicate returns, terminal and killed tombstones.

    Multiple processes serialize via SQLite BEGIN IMMEDIATE, so identical
    duplicated messages are idempotent and conflicting messages raise.
    This class does NOT place an order, reconstruct cognitive hypotheses, or
    certify a source/strategy. Consumers must independently verify provenance.
    """

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or str(path) == ":memory:":
            raise ValueError("VT08 WAL requires a durable filesystem Path")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), timeout=15, isolation_level=None)
        self._conn.execute("PRAGMA busy_timeout=15000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS vt08_wal_v1 (
                seq INTEGER PRIMARY KEY,
                source_event_id TEXT NOT NULL,
                market TEXT NOT NULL,
                kind TEXT NOT NULL
                    CHECK(kind IN ('WAIT','ABSTAIN','EXECUTE','FILL','POSITION','TERMINAL')),
                as_of_utc TEXT NOT NULL,
                identity_sha256 TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                event_key TEXT NOT NULL,
                fill_id TEXT,
                previous_sha256 TEXT NOT NULL,
                entry_sha256 TEXT NOT NULL,
                UNIQUE(source_event_id,event_key)
            )"""
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS vt08_wal_fill_unique_v1 "
            "ON vt08_wal_v1(fill_id) WHERE kind='FILL'"
        )
        self.verify_integrity()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Vt08DurableResearchLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _all(self) -> list[Vt08WalReceipt]:
        return [
            _record(row, inserted=False)
            for row in self._conn.execute(
                "SELECT seq,source_event_id,market,kind,as_of_utc,"
                "identity_sha256,evidence_sha256,event_key,fill_id,"
                "previous_sha256,entry_sha256 FROM vt08_wal_v1 ORDER BY seq"
            ).fetchall()
        ]

    def verify_integrity(self) -> tuple[int, str]:
        previous = ZERO
        counter = 0
        clock = ""
        for item in self._all():
            counter += 1
            if item.seq != counter or item.previous_sha256 != previous:
                raise ValueError("VT08 WAL chain order/digest broken")
            if item.as_of_utc < clock:
                raise ValueError("VT08 WAL global as_of clock moved backward")
            if _digest(_chain_payload(item)) != item.entry_sha256:
                raise ValueError("VT08 WAL record content tampered")
            previous = item.entry_sha256
            clock = item.as_of_utc
        return counter, previous

    def events(self) -> tuple[Vt08WalReceipt, ...]:
        return tuple(self._all())

    def append(
        self, *, source_event_id: str, market: str, kind: str,
        as_of: datetime, identity_sha256: str, evidence_sha256: str,
        fill_id: str | None = None,
    ) -> Vt08WalReceipt:
        """Commit an already-observed research event, without making it true."""
        if not isinstance(source_event_id, str) or not source_event_id.strip():
            raise ValueError("VT08 WAL missing source identity")
        if not isinstance(market, str) or not market.strip():
            raise ValueError("VT08 WAL market missing")
        if kind not in EVENT_KINDS:
            raise ValueError("VT08 WAL unknown event kind")
        _sha(identity_sha256, "identity")
        _sha(evidence_sha256, "evidence")
        instant = _utc_time(as_of)
        if kind == "FILL":
            if not isinstance(fill_id, str) or not fill_id.strip():
                raise ValueError("VT08 WAL FILL requires stable fill_id")
        elif kind == "TERMINAL":
            if not isinstance(fill_id, str) or not fill_id.strip():
                raise ValueError("VT08 WAL TERMINAL requires prior fill_id")
        elif fill_id is not None:
            raise ValueError("VT08 WAL fill_id prohibited for non-fill evidence")
        key = (
            f"{kind}:{fill_id}" if kind in ("FILL", "TERMINAL")
            else f"{kind}:{instant}"
        )
        db = self._conn
        db.execute("BEGIN IMMEDIATE")
        try:
            prior = db.execute(
                "SELECT seq,source_event_id,market,kind,as_of_utc,"
                "identity_sha256,evidence_sha256,event_key,fill_id,"
                "previous_sha256,entry_sha256 FROM vt08_wal_v1 "
                "WHERE source_event_id=? AND event_key=?",
                (source_event_id, key),
            ).fetchone()
            if prior is not None:
                record = _record(prior, inserted=False)
                if (
                    record.market != market or record.kind != kind
                    or record.as_of_utc != instant
                    or record.identity_sha256 != identity_sha256
                    or record.evidence_sha256 != evidence_sha256
                    or record.fill_id != fill_id
                ):
                    raise ValueError("VT08 WAL duplicate key has conflicting evidence")
                db.execute("COMMIT")
                return record

            latest = db.execute(
                "SELECT seq,as_of_utc,entry_sha256 FROM vt08_wal_v1 "
                "ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            global_clock = "" if latest is None else str(latest[1])
            if instant < global_clock:
                raise ValueError("VT08 WAL global source time regression")
            previous_hash = ZERO if latest is None else str(latest[2])
            next_seq = 1 if latest is None else int(latest[0]) + 1
            history = db.execute(
                "SELECT market,kind,as_of_utc,identity_sha256,fill_id "
                "FROM vt08_wal_v1 WHERE source_event_id=? ORDER BY seq",
                (source_event_id,),
            ).fetchall()
            kinds = [str(row[1]) for row in history]
            if history:
                if any(
                    row[0] != market or row[3] != identity_sha256
                    for row in history
                ):
                    raise ValueError("VT08 WAL source identity drift")
                if "ABSTAIN" in kinds or "TERMINAL" in kinds:
                    raise ValueError("VT08 WAL terminal/killed event cannot resurrect")
                last_source_time = str(history[-1][2])
                if kind in DECISIONS and instant <= last_source_time:
                    raise ValueError("VT08 WAL decision timestamp must advance")
                if kind == "POSITION" and instant <= last_source_time:
                    raise ValueError("VT08 WAL position timestamp must advance")
                if kind in ("FILL", "TERMINAL") and instant < last_source_time:
                    raise ValueError("VT08 WAL fill/terminal timestamp regressed")
            elif kind not in DECISIONS:
                raise ValueError("VT08 WAL source must have admission decision")
            if kind in DECISIONS:
                if "EXECUTE" in kinds:
                    raise ValueError("VT08 WAL no decision after executed source")
            elif kind == "FILL":
                if kinds.count("EXECUTE") != 1 or "FILL" in kinds:
                    raise ValueError("VT08 WAL fill without unique EXECUTE")
                prior_fill = db.execute(
                    "SELECT source_event_id FROM vt08_wal_v1 "
                    "WHERE kind='FILL' AND fill_id=?", (fill_id,),
                ).fetchone()
                if prior_fill is not None:
                    raise ValueError("VT08 WAL fill_id reused across source events")
            else:
                if kinds.count("FILL") != 1:
                    raise ValueError("VT08 WAL terminal/position requires fill")
                original_id = next(str(row[4]) for row in history if row[1] == "FILL")
                if kind == "TERMINAL" and original_id != fill_id:
                    raise ValueError("VT08 WAL terminal fill lineage drift")
            item = Vt08WalReceipt(
                seq=next_seq, source_event_id=source_event_id, market=market,
                kind=kind, as_of_utc=instant, identity_sha256=identity_sha256,
                evidence_sha256=evidence_sha256, event_key=key, fill_id=fill_id,
                previous_sha256=previous_hash, entry_sha256="", inserted=True,
            )
            digest = _digest(_chain_payload(item))
            db.execute(
                "INSERT INTO vt08_wal_v1 VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    next_seq, source_event_id, market, kind, instant,
                    identity_sha256, evidence_sha256, key, fill_id,
                    previous_hash, digest,
                ),
            )
            db.execute("COMMIT")
            return Vt08WalReceipt(
                seq=item.seq, source_event_id=item.source_event_id,
                market=item.market, kind=item.kind, as_of_utc=item.as_of_utc,
                identity_sha256=item.identity_sha256,
                evidence_sha256=item.evidence_sha256, event_key=item.event_key,
                fill_id=item.fill_id, previous_sha256=previous_hash,
                entry_sha256=digest, inserted=True,
            )
        except Exception:
            db.execute("ROLLBACK")
            raise
