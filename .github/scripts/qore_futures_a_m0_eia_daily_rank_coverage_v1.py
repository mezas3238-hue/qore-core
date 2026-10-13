"""Audita SOLO cobertura temporal de 2 series de futuros energéticos EIA.

NO exporta niveles, NO PnL, NO reglas de entrada, NO señales.
Un futuro "contract 1/2" de EIA es rango rotativo, NO contrato CME nativo.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

import xlrd

SOURCES = {
    "WTI_F1": "https://www.eia.gov/dnav/pet/hist_xls/RCLC1d.xls",
    "WTI_F2": "https://www.eia.gov/dnav/pet/hist_xls/RCLC2d.xls",
    "NG_F1": "https://www.eia.gov/dnav/ng/hist_xls/RNGC1d.xls",
    "NG_F2": "https://www.eia.gov/dnav/ng/hist_xls/RNGC2d.xls",
}
MIN_DATE = date(2012, 1, 1)
MAX_DATE = date(2024, 9, 16)


def coverage(series_name: str, url: str) -> tuple[dict[str, Any], set[date]]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "QORE-COVERAGE-ONLY/1.0"}
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        raw = response.read(16_000_001)
    if len(raw) > 16_000_000:
        raise ValueError("source file exceeds 16 MB limit")
    book = xlrd.open_workbook(file_contents=raw, on_demand=True)
    sheet = book.sheet_by_name("Data 1")
    all_dates: set[date] = set()
    window_dates: set[date] = set()
    duplicate_count = 0
    skipped_non_numeric = 0
    year_counts: dict[str, int] = {}
    for i in range(sheet.nrows):
        day_cell = sheet.cell(i, 0)
        value_cell = sheet.cell(i, 1)
        if day_cell.ctype != xlrd.XL_CELL_DATE:
            continue
        dt = xlrd.xldate.xldate_as_datetime(day_cell.value, book.datemode).date()
        if value_cell.ctype != xlrd.XL_CELL_NUMBER:
            skipped_non_numeric += 1
            continue
        if dt in all_dates:
            duplicate_count += 1
        all_dates.add(dt)
        if MIN_DATE <= dt <= MAX_DATE:
            window_dates.add(dt)
            y = str(dt.year)
            year_counts[y] = year_counts.get(y, 0) + 1
    if not all_dates:
        raise ValueError("no dated numeric observations")
    return (
        {
            "series": series_name,
            "source_url": url,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "observations_dated_numeric_all": len(all_dates),
            "first_numeric_date": min(all_dates).isoformat(),
            "last_numeric_date": max(all_dates).isoformat(),
            "observations_2012_01_01_to_2024_09_16": len(window_dates),
            "year_counts_2012_2024": year_counts,
            "duplicate_date_count": duplicate_count,
            "dated_rows_with_missing_non_numeric_price": skipped_non_numeric,
            "contains_native_expiration_month_contract_id": False,
            "contains_ohlcv_candles": False,
            "historical_first_published_at_verified": False,
        },
        window_dates,
    )


def main() -> None:
    reports: list[dict[str, Any]] = []
    observed: dict[str, set[date]] = {}
    for name, url in SOURCES.items():
        report, days = coverage(name, url)
        reports.append(report)
        observed[name] = days
        print("EIA_FREE_DATED_SOURCE", json.dumps(report, sort_keys=True))
    pairs = {}
    for root in ("WTI", "NG"):
        a = observed[f"{root}_F1"]
        b = observed[f"{root}_F2"]
        common = a & b
        pairs[root] = {
            "paired_rank1_rank2_common_date_count": len(common),
            "first_paired_date": min(common).isoformat() if common else None,
            "last_paired_date": max(common).isoformat() if common else None,
            "rank1_only_days": len(a - b),
            "rank2_only_days": len(b - a),
            "contract_month_identity_known": False,
            "settle_or_trade_close_asof_timestamps_verified": False,
        }
    result = {
        "identity": "QORE_FUTURES_A_M0_EIA_RANK_1_AND_2_DATE_COVERAGE_V1",
        "budget_market_data_usd": 0,
        "source_government": "EIA",
        "series": reports,
        "paired_date_coverage": pairs,
        "source_family_count": 2,
        "required_source_family_count": 6,
        "full_D1_OHLCV_contract_native_history_verified": False,
        "source_ready_for_prereg": False,
        "PnL_trading_returns_calculated": False,
        "holdout_market_prices_researched": False,
        "traders_certified": 0,
    }
    out = Path("eia_energy_2012_2024_date_coverage_metadata_only.json")
    out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("EIA_FREE_TWO_ENERGY_ROOTS_DATE_COVERAGE_NO_PNL")


if __name__ == "__main__":
    main()
