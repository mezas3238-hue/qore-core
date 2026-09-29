from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest

from qore.infrastructure.trader_lab.nq_am_tlr_v3_tradestation_nq_evidence import (
    CHUNK_DAYS,
    ExactNqEvidenceError,
    barchart_url,
    chunk_grid,
    contract_manifest_sha256,
    evidence_payload,
    parse_barchart_response,
    parse_contract_manifest,
)


def _manifest() -> str:
    return json.dumps(
        {
            "provider": "tradestation-api-v3",
            "root": "NQ",
            "opened_at": "2024-08-13T00:00:00+00:00",
            "closed_at": "2024-10-01T00:00:00+00:00",
            "slices": [
                {
                    "symbol": "PROVIDER_VERIFIED_NQ_CONTRACT_A",
                    "opened_at": "2024-08-13T00:00:00+00:00",
                    "closed_at": "2024-09-20T00:00:00+00:00",
                },
                {
                    "symbol": "PROVIDER_VERIFIED_NQ_CONTRACT_B",
                    "opened_at": "2024-09-20T00:00:00+00:00",
                    "closed_at": "2024-10-01T00:00:00+00:00",
                },
            ],
        }
    )


def test_manifest_requires_exact_contiguous_provider_contract_slices() -> None:
    manifest = parse_contract_manifest(_manifest())
    assert manifest.root == "NQ"
    assert len(manifest.slices) == 2
    assert manifest.slices[0].closed_at == manifest.slices[1].opened_at
    assert len(contract_manifest_sha256(manifest)) == 64


def test_manifest_rejects_gap_between_contract_slices() -> None:
    payload = json.loads(_manifest())
    payload["slices"][1]["opened_at"] = "2024-09-21T00:00:00+00:00"
    with pytest.raises(ExactNqEvidenceError, match="gap-free"):
        parse_contract_manifest(json.dumps(payload))


def test_chunk_grid_stays_below_bounded_calendar_window() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=47)
    chunks = chunk_grid(start, end)
    assert len(chunks) == 3
    assert all(right - left <= timedelta(days=CHUNK_DAYS) for left, right in chunks)
    assert chunks[0][0] == start
    assert chunks[-1][1] == end


def test_barchart_url_is_m1_date_range_and_escapes_symbol() -> None:
    start = datetime(2024, 8, 13, tzinfo=UTC)
    end = datetime(2024, 8, 20, tzinfo=UTC)
    url = barchart_url("@NQ TEST", start, end)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.path.endswith("/marketdata/barcharts/%40NQ%20TEST")
    assert query["interval"] == ["1"]
    assert query["unit"] == ["Minute"]
    assert query["firstdate"] == ["2024-08-13T00:00:00Z"]
    assert query["lastdate"] == ["2024-08-20T00:00:00Z"]


def test_parse_barchart_response_preserves_exact_contract_identity() -> None:
    start = datetime(2024, 8, 13, tzinfo=UTC)
    end = start + timedelta(days=1)
    bars = parse_barchart_response(
        {
            "Bars": [
                {
                    "High": "19125.50",
                    "Low": "19100.25",
                    "Open": "19110.00",
                    "Close": "19120.75",
                    "TimeStamp": "2024-08-13T13:30:00Z",
                    "TotalVolume": "1200",
                    "OpenInterest": "50000",
                    "IsRealtime": False,
                }
            ]
        },
        symbol="PROVIDER_NQ_CONTRACT",
        opened_at=start,
        closed_at=end,
    )
    assert len(bars) == 1
    assert bars[0].provider_symbol == "PROVIDER_NQ_CONTRACT"
    assert bars[0].close == Decimal("19120.75")
    assert bars[0].total_volume == 1200
    assert bars[0].is_realtime is False


def test_evidence_payload_is_read_only_and_has_zero_trade_authority() -> None:
    manifest = parse_contract_manifest(_manifest())
    start = manifest.opened_at
    bars = parse_barchart_response(
        {
            "Bars": [
                {
                    "High": "101",
                    "Low": "99",
                    "Open": "100",
                    "Close": "100.5",
                    "TimeStamp": start.isoformat(),
                    "TotalVolume": "10",
                    "OpenInterest": "20",
                    "IsRealtime": False,
                }
            ]
        },
        symbol=manifest.slices[0].symbol,
        opened_at=start,
        closed_at=start + timedelta(days=1),
    )
    payload = evidence_payload(manifest, bars)
    assert payload["read_only"] is True
    assert payload["brokerage_endpoint_used"] is False
    assert payload["order_endpoint_used"] is False
    assert payload["live_authorized"] is False
    assert payload["real_capital_authorized"] is False
