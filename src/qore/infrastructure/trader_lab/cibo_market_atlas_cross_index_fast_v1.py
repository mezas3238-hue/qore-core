"""Performance-only cross-index aggregation for CIBO Journey Layer V1.

Preserves the frozen cross-index semantics from the Journey extractor while
replacing per-event full peer scans with binary search over sorted departure
timestamps. No detector, association window, evidence tier, or output schema is
changed.
"""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    CROSS_INDEX_SCHEMA,
    IDENTITY,
    MANIFEST_SCHEMA,
    SOURCE_GIT_SHA,
    SOURCE_RUN_ID,
    _dt,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _departure_rows(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[datetime], list[dict[str, Any]]]:
    pairs: list[tuple[datetime, dict[str, Any]]] = []
    for row in rows:
        raw = row.get("departure_at")
        if raw is not None:
            pairs.append((_dt(str(raw)), row))
    pairs.sort(key=lambda item: item[0])
    return [item[0] for item in pairs], [item[1] for item in pairs]


def _nearest(
    departures: Sequence[datetime],
    rows: Sequence[dict[str, Any]],
    target: datetime,
) -> tuple[datetime, dict[str, Any]] | None:
    if not departures:
        return None
    position = bisect_left(departures, target)
    candidates: list[int] = []
    if position < len(departures):
        candidates.append(position)
    if position > 0:
        candidates.append(position - 1)
    index = min(
        candidates,
        key=lambda item: (
            abs((departures[item] - target).total_seconds()),
            departures[item],
        ),
    )
    return departures[index], rows[index]


def cross_index_rows(
    nas100: Sequence[dict[str, Any]],
    sp500: Sequence[dict[str, Any]],
    us30: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    populations = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    indexed = {
        symbol: _departure_rows(rows) for symbol, rows in populations.items()
    }
    result: list[dict[str, Any]] = []
    for symbol, (departures, rows) in indexed.items():
        for departure, row in zip(departures, rows, strict=True):
            peers: dict[str, Any] = {}
            for peer_symbol, (peer_departures, peer_rows) in indexed.items():
                if peer_symbol == symbol:
                    continue
                nearest = _nearest(peer_departures, peer_rows, departure)
                if nearest is None:
                    continue
                nearest_at, nearest_row = nearest
                delta = int((nearest_at - departure).total_seconds() // 60)
                within = abs(delta) <= 120
                peers[peer_symbol] = {
                    "episode_id": nearest_row["episode_id"] if within else None,
                    "departure_at": nearest_at.isoformat() if within else None,
                    "lead_lag_minutes": delta if within else None,
                    "agreement": (
                        row.get("side") == nearest_row.get("side")
                        if within
                        else None
                    ),
                    "comparison_window_minutes": 120,
                }
            result.append(
                {
                    "schema": CROSS_INDEX_SCHEMA,
                    "identity": IDENTITY,
                    "episode_id": row["episode_id"],
                    "symbol": symbol,
                    "departure_at": departure.isoformat(),
                    "side": row.get("side"),
                    "peer_states": peers,
                    "association_only": True,
                    "causal_feature": False,
                    "outcome_only": True,
                }
            )
    result.sort(key=lambda item: (item["departure_at"], item["symbol"]))
    return result


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_cross_index(
    nas100: Path, sp500: Path, us30: Path, output: Path
) -> dict[str, Any]:
    rows = cross_index_rows(
        _read_jsonl(nas100), _read_jsonl(sp500), _read_jsonl(us30)
    )
    output.mkdir(parents=True, exist_ok=True)
    path = output / "CROSS_INDEX_JOURNEY_LEDGER.jsonl"
    count = _write_jsonl(path, rows)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "identity": IDENTITY,
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
        "ledger": "CROSS_INDEX_JOURNEY_LEDGER",
        "rows": count,
        "sha256": _sha256(path),
        "lead_lag_evidence_tier": "E1_ASSOCIATION_ONLY",
        "aggregation_transport": "BINARY_SEARCH_NEAREST_V1",
        "comparison_window_minutes": 120,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "cross-index-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest
