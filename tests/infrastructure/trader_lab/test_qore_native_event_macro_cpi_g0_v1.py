"""QORE EVENT MACRO CPI source-only and timestamp privacy gates."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_event_macro_cpi_g0_v1 as g


def bls_html(*rows: str) -> str:
    return "<html><table>" + "".join(
        "<tr><td>" + row.replace(" | ", "</td><td>") + "</td></tr>"
        for row in rows
    ) + "</table></html>"


def test_source_clock_uses_eastern_dst_and_only_cpi() -> None:
    blob = bls_html(
        "Friday, September 11, 2026 | 08:30 AM | Consumer Price Index for August 2026",
        "Wednesday, January 13, 2026 | 08:30 AM | Consumer Price Index for December 2025",
        "Friday, September 11, 2026 | 08:30 AM | Real Earnings for August 2026",
    )
    result = g.parse_bls_year(blob, 2026)
    assert len(result) == 2
    assert result[0].ny_date == "2026-01-13"
    assert result[0].timestamp_utc == "2026-01-13T13:30:00+00:00"
    assert result[1].ny_date == "2026-09-11"
    assert result[1].timestamp_utc == "2026-09-11T12:30:00+00:00"
    assert all(x.provenance.endswith("NOT_ASOF") for x in result)


def test_bls_october_2025_cancellation_not_fabricated() -> None:
    blob = bls_html(
        "Friday, October 24, 2025 | 08:30 AM | Consumer Price Index for September 2025",
        "Thursday, December 18, 2025 | 08:30 AM | Consumer Price Index for November 2025",
    )
    events = g.parse_bls_year(blob, 2025)
    assert len(events) == 2
    assert "October" not in [x.ref_month for x in events]
    assert events[0].ny_date == "2025-10-24"


def test_bls_changed_clock_fail_closed() -> None:
    blob = bls_html(
        "Friday, October 24, 2025 | 10:00 AM | Consumer Price Index for September 2025",
    )
    with pytest.raises(ValueError, match="08:30"):
        g.parse_bls_year(blob, 2025)


def test_unparseable_official_schedule_fail_closed() -> None:
    blob = bls_html("Friday, October 24, 2025 | 08:30 AM | Consumer Price Index for")
    with pytest.raises(ValueError, match="lacks date"):
        g.parse_bls_year(blob, 2025)


def test_duplicate_reference_month_changed_date_fails() -> None:
    blob = bls_html(
        "Friday, October 24, 2025 | 08:30 AM | Consumer Price Index for September 2025",
        "Tuesday, October 21, 2025 | 08:30 AM | Consumer Price Index for September 2025",
    )
    with pytest.raises(ValueError, match="contradictory"):
        g.parse_bls_year(blob, 2025)


def test_windows_71_minutes_and_full_dst() -> None:
    assert list(g.COVER_WINDOWS) == ["PRE10", "PRINT0", "AFTER30", "AFTER60"]
    assert len(g.SELECTED) == 71
    assert len(g.COVER_WINDOWS["PRE10"]) == 10
    assert len(g.COVER_WINDOWS["PRINT0"]) == 1
    assert len(g.COVER_WINDOWS["AFTER30"]) == 30
    assert len(g.COVER_WINDOWS["AFTER60"]) == 30
    assert min(g.SELECTED) == 500 and max(g.SELECTED) == 570


def cibo_manifest(root: Path) -> None:
    manifest = {
        "identity": g.CIBO_IDENTITY,
        "canonical_symbol": "NAS100",
        "provider_symbol": "USTEC",
        "provider_native_m1": True, "synthetic_m1": False,
        "interpolated_m1": False, "read_only": True,
        "live_authorized": False, "production_authorized": False,
        "contradictory_m1": 0,
        "target_start": g.START.isoformat(),
        "target_end_exclusive": g.END.isoformat(),
        "provider_symbol_id": 101, "digits": 2,
        "retained_m1": 1,
        "partitions": [{"partition": str(y), "retained_m1": 0}
                       for y in g.YEARS],
    }
    f = root / "m1-clone-manifest.json"
    f.write_text(json.dumps(manifest))
    (root / "MANIFEST_SHA256SUMS.txt").write_text(
        hashlib.sha256(f.read_bytes()).hexdigest() + "  m1-clone-manifest.json\n"
    )


def test_cibo_native_manifest_contract_no_synthetic(tmp_path: Path) -> None:
    cibo_manifest(tmp_path)
    m = g.cibo_source(tmp_path)
    assert m["canonical_symbol"] == "NAS100"
    assert m["provider_symbol"] == "USTEC"
    path = tmp_path / "m1-clone-manifest.json"
    modified = json.loads(path.read_text())
    modified["synthetic_m1"] = True
    path.write_text(json.dumps(modified))
    with pytest.raises(ValueError, match="SHA mismatch"):
        g.cibo_source(tmp_path)
    (tmp_path / "MANIFEST_SHA256SUMS.txt").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  m1-clone-manifest.json\n"
    )
    with pytest.raises(ValueError, match="source identity"):
        g.cibo_source(tmp_path)


def test_current_script_never_reads_market_prices() -> None:
    script = Path(g.__file__).read_text(encoding="utf-8")
    # Strings may appear in privacy comments, never index row values by price.
    for forbidden in (
        'row["open_relative"]',
        'row["high_relative"]',
        'row["low_relative"]',
        'row["close_relative"]',
        'row.get("open_relative")',
        'row.get("close_relative")',
        "math.log(", "numpy", "pandas",
        "profit_factor", "sharpe_ratio",
    ):
        assert forbidden not in script


def test_utc_source_range_correct() -> None:
    assert g.START == datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
    assert g.END == datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
    assert g.CIBO_ARTIFACT == 10618862813
    assert g.PREREG_SHA == "621c55ffc21d31305fe0f623cb9822b7b7b2b476"
