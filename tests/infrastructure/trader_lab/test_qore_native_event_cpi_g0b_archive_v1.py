"""G0B release-header corroboration tests, without CPI numbers or any price rows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_event_cpi_g0b_archive_v1 as m


def test_2016_to_2026_archive_index_maps_actual_day_and_reference_month() -> None:
    html = """
    <ul>
      <li><a href="/news.release/archives/cpi_10242025.htm">
      September 2025 Consumer Price Index</a></li>
      <li><a href="https://www.bls.gov/news.release/archives/cpi_09112026.htm">
      August 2026 Consumer Price Index</a></li>
      <li>October 2025 Consumer Price Index - not published</li>
      <li><a href="https://other.example.com/news.release/archives/cpi_07162020.htm">
      June 2020 Consumer Price Index</a></li>
    </ul>
    """
    result = m.parse_index(html)
    assert set(result) == {"2025-10-24", "2026-09-11"}
    assert result["2025-10-24"].ref_month == "September"
    assert result["2026-09-11"].ref_year == 2026
    assert all(r.url.startswith("https://www.bls.gov/") for r in result.values())


def test_actual_embargo_header_and_month_must_both_match() -> None:
    html = """<html><head><title>CPI archive</title></head><body>
    <h1>Consumer Price Index News Release</h1>
    Transmission of material in this release is embargoed until
    8:30 a.m. (ET) Friday, September 11, 2026 USDL-26-1000
    <strong>CONSUMER PRICE INDEX - AUGUST 2026</strong>
    CPI actual 3.4% (NEVER OUTPUT)
    </body></html>"""
    assert m.parse_header(html) == ("2026-09-11", "August", 2026)



def test_legacy_2022_release_embargo_missing_weekday_is_valid() -> None:
    header = """<html><body>
    Transmission of material in this release is embargoed until
    8:30 a.m. (ET) May 11, 2022 USDL-22-0835
    CONSUMER PRICE INDEX - APRIL 2022
    </body></html>"""
    assert m.parse_header(header) == ("2022-05-11", "April", 2022)


def test_legacy_non_utf8_ascii_header_is_parseable() -> None:
    raw = (b"Transmission of material in this release is embargoed until "
           b"8:30 a.m. (ET) Tuesday, October 18, 2016 "
           b"CONSUMER PRICE INDEX - SEPTEMBER 2016"
           + bytes([0x96]))
    assert m.parse_header(raw.decode("utf-8", errors="replace")) == (
        "2016-10-18", "September", 2016
    )


def test_posted_schedule_with_missing_archive_is_unconfirmed() -> None:
    row = {"ny_date": "2026-09-11", "ref_month": "August",
           "ref_year": 2026}
    witness = m.inspect_entry(row, None)
    assert witness["status"] == "ARCHIVE_INDEX_NO_MATCH"
    assert witness["archive_header_confirmed"] is False


def test_bls_archive_reference_mismatch_blocks_before_fetch() -> None:
    row = {"ny_date": "2025-10-24", "ref_month": "October", "ref_year": 2025}
    indexed = m.ArchivedEntry(
        "2025-10-24", "September", 2025,
        "https://www.bls.gov/news.release/archives/cpi_10242025.htm",
    )
    mismatch = m.inspect_entry(row, indexed)
    assert mismatch["status"] == "ARCHIVE_CONTRADICTION"
    assert mismatch["difference"] == "REFERENCE_MONTH_OR_YEAR_MISMATCH"


def test_header_effective_release_checked_not_just_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = {"ny_date": "2025-10-24", "ref_month": "September",
           "ref_year": 2025}
    archive = m.ArchivedEntry("2025-10-24", "September", 2025,
                            "https://www.bls.gov/news.release/archives/cpi_10242025.htm")
    stub = b"""<html><body>Transmission of material in this release is embargoed until
    8:30 a.m. (ET) Friday, October 24, 2025
    <h2>CONSUMER PRICE INDEX - SEPTEMBER 2025</h2></body></html>"""
    monkeypatch.setattr(m, "fetch_official", lambda url: stub)
    report = m.inspect_entry(row, archive)
    assert report["status"] == "ARCHIVED_RELEASE_HEADER_MATCH"
    assert report["archive_header_confirmed"] is True
    assert report["archived_header_prefix_sha256"] == hashlib.sha256(stub).hexdigest()
    assert "actual" not in report and "forecast" not in report


def test_archive_header_wrong_date_cannot_be_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = {"ny_date": "2025-10-24", "ref_month": "September", "ref_year": 2025}
    archive = m.ArchivedEntry("2025-10-24", "September", 2025,
                            "https://www.bls.gov/news.release/archives/cpi_10242025.htm")
    monkeypatch.setattr(m, "fetch_official", lambda url: b"""
    Transmission of material in this release is embargoed until
    8:30 a.m. (ET) Wednesday, October 15, 2025
    CONSUMER PRICE INDEX - SEPTEMBER 2025""")
    assert m.inspect_entry(row, archive)["status"] == "ARCHIVE_CONTRADICTION"


def test_sha_source_g0_artifact_and_119_events_required(tmp_path: Path) -> None:
    source = tmp_path / "cpi-bls-g0-dated-events.json"
    data = [{
        "ny_date": f"2024-01-{i + 1:02d}",
        "local_ny_clock": "08:30", "ref_month": "December",
        "ref_year": 2023,
        "source_calendar_url": "https://www.bls.gov/schedule/2024/",
        "provenance": "BLS_CALENDAR_ROW_RETROSPECTIVE_NOT_ASOF"
    } for i in range(24)]
    source.write_text(json.dumps(data))
    (tmp_path / "OUTPUT_SHA256SUMS.txt").write_text(
        hashlib.sha256(source.read_bytes()).hexdigest() +
        "  cpi-bls-g0-dated-events.json\n"
    )
    with pytest.raises(ValueError, match="event population"):
        m.read_locked_calendar(tmp_path)
    source.write_text(json.dumps([*data, *data] * 4))
    with pytest.raises(ValueError, match="SHA256"):
        m.read_locked_calendar(tmp_path)


def test_privacy_and_single_source_contract() -> None:
    source = Path(m.__file__).read_text()
    assert m.PREREG_SHA == "c8092917ea27afbeee2d6b4cb4df1d2cbe245d1a"
    assert m.CALENDAR_RUN == 38189483643
    assert m.CALENDAR_ARTIFACT == 11720651765
    for forbidden in (
        'row.get("open_relative")', 'row["open_relative"]', "ctrader_open_api",
        "math.log(", "profit_factor", "sharpe", "sqlite",
    ):
        assert forbidden not in source
