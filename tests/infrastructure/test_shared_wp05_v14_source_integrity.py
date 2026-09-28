from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
    peer_spec,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_source_integrity import (
    V14SourceIntegrityError,
    audit_v14_peer_page,
)


def _canonical(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def _write_page(
    root: Path,
    *,
    peer: V14PeerFamily,
    side: str = "BID",
    empty: bool = False,
) -> Path:
    spec = peer_spec(peer)
    start = datetime(2017, 1, 2, 15, 0, tzinfo=UTC)
    end = start + timedelta(minutes=1)
    retrieved = end + timedelta(days=3000)
    rows = []
    if not empty:
        rows = [
            {
                "provider_event_at": (start + timedelta(seconds=1)).isoformat(
                    timespec="microseconds"
                ),
                "provider_wire_timestamp_value": 1,
                "provider_wire_price_value": 100,
                "relative_price": 100,
                "price": "1.00",
            }
        ]
    provenance = {
        "schema": "qore.shared.wp05.v12.historical_quote_side_shard.v2",
        "quote_side": side,
        "window_index": 0,
        "page_index": 0,
        "request_from_at": start.isoformat(timespec="microseconds"),
        "request_to_at": end.isoformat(timespec="microseconds"),
        "retrieved_at": retrieved.isoformat(timespec="microseconds"),
        "source": None if empty else ["source"],
        "provider_account_id": None if empty else 123,
        "provider_symbol_id": None if empty else spec.provider_symbol_id,
        "provider_symbol": None if empty else spec.provider_symbol,
        "content_sha256": _canonical(rows),
    }
    provenance_sha = _canonical(provenance)
    header = {
        **provenance,
        "provenance_sha256": provenance_sha,
        "tick_count": len(rows),
    }
    side_dir = root / side
    side_dir.mkdir(parents=True)
    path = side_dir / f"w000000-p000000-{provenance_sha}.jsonl.gz"
    encoded = [json.dumps({"header": header}, sort_keys=True)]
    encoded.extend(json.dumps({"tick": row}, sort_keys=True) for row in rows)
    path.write_bytes(gzip.compress(("\n".join(encoded) + "\n").encode(), mtime=0))
    return path


@pytest.mark.parametrize("peer", list(V14PeerFamily))
def test_v14_raw_page_verifies_exact_peer_identity(
    tmp_path: Path,
    peer: V14PeerFamily,
) -> None:
    page = audit_v14_peer_page(
        _write_page(tmp_path, peer=peer),
        peer=peer,
    )
    assert page.provider_identity_verified is True
    assert page.tick_count == 1


def test_v14_raw_page_accepts_explicit_empty_provider_page(tmp_path: Path) -> None:
    page = audit_v14_peer_page(
        _write_page(tmp_path, peer=V14PeerFamily.SP500, empty=True),
        peer=V14PeerFamily.SP500,
    )
    assert page.provider_identity_verified is False
    assert page.tick_count == 0
    assert page.first_event_at is None


def test_v14_raw_page_rejects_cross_peer_identity(tmp_path: Path) -> None:
    path = _write_page(tmp_path, peer=V14PeerFamily.SP500)
    with pytest.raises(V14SourceIntegrityError, match="provider symbol drift"):
        audit_v14_peer_page(path, peer=V14PeerFamily.US30)
