"""QORE Futures A M0: free public archive custody/coverage preflight.

This tool performs source inventory ONLY: no execution, trading signal, PnL,
profit factor, Sharpe, or licensed raw price dissemination. Runner downloaded
archives are discarded. Only contract filename and date coverage metadata
are emitted, with source SHA-256 for independent source identity.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

URLS = {
    "TURTLE_CL": "https://www.turtletrader.com/cddata/cl.zip",
    "TURTLE_GC": "https://www.turtletrader.com/cddata/gc.zip",
    "TURTLE_HG": "https://www.turtletrader.com/cddata/hg.zip",
    "TURTLE_ZC": "https://www.turtletrader.com/cddata/c.zip",
    "TURTLE_ZS": "https://www.turtletrader.com/cddata/s.zip",
    "ACADEMIC_17": (
        "https://raw.githubusercontent.com/SSEconomics/"
        "commodity-spot-and-futures-data/main/Futures%20Data.zip"
    ),
}
FIXED_ROOTS = ("CL", "NG", "GC", "HG", "ZC", "ZS")
LIMIT_DOWNLOAD = 45_000_000
LIMIT_UNCOMPRESSED_TOTAL = 450_000_000


def _request_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "QORE-Free-Source-Inventory/1.0 (metadata-only)"},
    )
    with urllib.request.urlopen(req, timeout=40) as response:
        content_len = response.headers.get("Content-Length")
        if content_len and int(content_len) > LIMIT_DOWNLOAD:
            raise ValueError("DECLARED_DOWNLOAD_EXCEEDS_45MB")
        buff = bytearray()
        while True:
            part = response.read(1024 * 128)
            if not part:
                break
            buff.extend(part)
            if len(buff) > LIMIT_DOWNLOAD:
                raise ValueError("DOWNLOAD_EXCEEDS_45MB")
        return bytes(buff)


def _parse_candidate_date(cell: str) -> date | None:
    val = cell.strip().strip('"').strip("'")
    if not val or len(val) > 32:
        return None
    try:
        if re.fullmatch(r"(?:19|20)\d{6}", val):
            parsed = date(int(val[:4]), int(val[4:6]), int(val[6:8]))
        elif re.fullmatch(r"(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}", val):
            chunks = re.split("[-/]", val)
            parsed = date(*(int(i) for i in chunks))
        elif re.fullmatch(r"\d{6}", val):
            year = int(val[:2])
            parsed = date(2000 + year if year < 70 else 1900 + year,
                          int(val[2:4]), int(val[4:6]))
        else:
            return None
        if 1970 <= parsed.year <= 2026:
            return parsed
    except ValueError:
        return None
    return None


def _classify_member(member: zipfile.ZipInfo) -> str:
    name = Path(member.filename).name.lower()
    if name.endswith((".txt", ".csv", ".asc", ".dat")):
        return "TEXT"
    if name.endswith((".xlsx", ".xls")):
        return "WORKBOOK"
    return "OTHER"


def scan_zip(source_id: str, body: bytes) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "source_id": source_id,
        "http_status": "OK_ZIP",
        "archive_sha256": hashlib.sha256(body).hexdigest(),
        "archive_size_bytes": len(body),
        "free_to_download_page": True,
        "license_for_strategy_reuse_independently_verified": False,
        "raw_archive_retained_or_uploaded": False,
        "economic_or_return_metrics_calculated": False,
    }
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
        if sum(m.file_size for m in members) > LIMIT_UNCOMPRESSED_TOTAL:
            raise ValueError("ZIP_UNCOMPRESSED_EXCEEDS_450MB")
        kinds = Counter(_classify_member(m) for m in members)
        summary["archive_member_count"] = len(members)
        summary["member_types"] = dict(kinds)
        summary["file_names_first_12"] = [
            Path(m.filename).name[:80] for m in members[:12]
        ]
        years: Counter[int] = Counter()
        rows_with_parseable_dates = 0
        date_files = 0
        earliest: date | None = None
        latest: date | None = None
        sample_text_files = 0
        for info in members:
            if _classify_member(info) != "TEXT":
                continue
            sample_text_files += 1
            this_file_has_date = False
            # No raw values leave the runner. Scan up to 25K rows per member,
            # and only parse the first field as a trade date.
            with zf.open(info) as fh:
                for idx, data in enumerate(fh):
                    if idx >= 25_000:
                        break
                    line = data.decode("utf-8", errors="replace")
                    first = line.split(",", 1)[0].split(";", 1)[0]
                    parsed = _parse_candidate_date(first)
                    if parsed is None:
                        continue
                    this_file_has_date = True
                    rows_with_parseable_dates += 1
                    years[parsed.year] += 1
                    if earliest is None or parsed < earliest:
                        earliest = parsed
                    if latest is None or parsed > latest:
                        latest = parsed
            if this_file_has_date:
                date_files += 1
        summary["scanned_text_files"] = sample_text_files
        summary["text_files_with_parseable_dates"] = date_files
        summary["date_rows_checked"] = rows_with_parseable_dates
        summary["earliest_date_seen"] = earliest.isoformat() if earliest else None
        summary["latest_date_seen"] = latest.isoformat() if latest else None
        summary["rows_in_2012_2024"] = sum(
            n for y, n in years.items() if 2012 <= y <= 2024
        )
        summary["rows_in_2023_2024"] = years[2023] + years[2024]
        summary["workbook_base_names"] = [
            Path(m.filename).name[:100]
            for m in members if _classify_member(m) == "WORKBOOK"
        ][:40]
        summary["has_six_roots_native_contract_daily_verified"] = False
        summary["monthly_curve_vs_daily_bar_evidence"] = (
            "NO_DAY_BAR_COVERAGE_IN_ARCHIVE_PROVEN"
            if kinds["TEXT"] == 0
            else "TEXT_DATE_COVERAGE_ONLY_NOT_OHLCV_OR_NATIVE_CERTIFIED"
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reports: list[dict[str, Any]] = []
    for source_id, url in URLS.items():
        print(f"FETCH_METADATA_SOURCE {source_id}", flush=True)
        try:
            body = _request_bytes(url)
            report = scan_zip(source_id, body)
            del body
        except (OSError, ValueError, zipfile.BadZipFile,
                urllib.error.URLError) as exc:
            report = {
                "source_id": source_id,
                "http_status": "BLOCKED_OR_BAD_ARCHIVE",
                "error_class": type(exc).__name__,
                "error_message": str(exc)[:180],
                "raw_archive_retained_or_uploaded": False,
                "economic_or_return_metrics_calculated": False,
            }
        print("SOURCE_METADATA", json.dumps(report, sort_keys=True), flush=True)
        reports.append(report)
    summary: dict[str, Any] = {
        "identity": "QORE_FUTURES_A_M0_PUBLIC_FREE_ARCHIVE_METADATA_V1",
        "fixed_roots": list(FIXED_ROOTS),
        "sources": reports,
        "monetary_spend_usd": 0,
        "has_authorized_2012_2024_6x2_native_contract_ohlcv": False,
        "certified_license_to_store_or_reuse_raw_market_data": False,
        "certified_contract_execution_or_costs": False,
        "source_ready_for_prereg": False,
        "backtests_or_sharpe_executed": False,
        "holdout_touched": False,
        "traders_certified": 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("OVERALL_STATUS NO_SOURCE_READY_NO_PNL_NO_HOLDOUT", flush=True)


if __name__ == "__main__":
    main()
