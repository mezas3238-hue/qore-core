"""Official CFTC six-commodity source audit; zero price/outcome inspection.

Reads CFTC Disaggregated FUTURES ONLY annual archives for 2012, 2018,
and 2021 (source identity snapshots). No strategy, no COT edge/PnL, no holdout.
Outputs metadata counts and input digests, never trader positions.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA = "qore.futures-a.cftc-sixroots.source-audit.v1"
URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
YEARS = (2012, 2018, 2021)  # Audit sample only; NOT 2012-2021 full coverage.
CONTRACT_CODES = {
    "CL": "067651",  # NYMEX WTI physical
    "NG": "023651",  # NYMEX natural gas
    "GC": "088691",  # COMEX gold
    "HG": "085692",  # COMEX copper
    "ZC": "002602",  # CBOT corn
    "ZS": "005602",  # CBOT soybeans
}
REQUIRED_COLUMNS = (
    "CFTC_Contract_Market_Code",
    "As_of_Date_Form_YYYY-MM-DD",
    "Market_and_Exchange_Names",
    "Open_Interest_All",
    "M_Money_Positions_Long_All",
    "M_Money_Positions_Short_All",
)
_CODE_RE = re.compile(r"[A-Z0-9]{6}\Z")


class CftcSourceError(ValueError):
    """The public source does not satisfy the pinned source identity."""


def parse_cftc_source(binary: bytes, year: int) -> dict[str, Any]:
    """Audit source structure only. Never return economic trader position values."""
    if type(year) is not int or year not in YEARS:
        raise CftcSourceError("UNAUTHORIZED_YEAR_OR_RESERVED_OOS")
    if type(binary) is not bytes or len(binary) < 512 or len(binary) > 30_000_000:
        raise CftcSourceError("ZIP_EMPTY_OR_UNTRUSTED_SIZE")
    digest = hashlib.sha256(binary).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(binary)) as handle:
            infos = [
                info for info in handle.infolist()
                if info.filename.lower().endswith((".txt", ".csv"))
                and not info.is_dir()
            ]
            if len(infos) != 1 or infos[0].file_size > 55_000_000:
                raise CftcSourceError("ARCHIVE_LAYOUT_OR_ZIP_BOMB")
            contents = handle.read(infos[0])
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise CftcSourceError("CORRUPT_CFTC_ARCHIVE") from exc
    if len(contents) > 55_000_000:
        raise CftcSourceError("DECOMPRESSED_TOO_LARGE")
    # CFTC's official comma-delimited legacy source uses western single-byte
    # names. Values/market identity fields are required to be ASCII.
    table = csv.DictReader(io.StringIO(contents.decode("latin-1")))
    if table.fieldnames is None:
        raise CftcSourceError("NO_CSV_HEADERS")
    fields = {name.strip().lstrip("\ufeff") for name in table.fieldnames}
    if not set(REQUIRED_COLUMNS).issubset(fields):
        print("CFTC_SOURCE_SCHEMA_HEADERS", sorted(fields)[:32])
        print("CFTC_SOURCE_SCHEMA_MISSING", sorted(set(REQUIRED_COLUMNS) - fields))
        raise CftcSourceError("REQUIRED_DISAGGREGATED_FIELDS_ABSENT")
    by_code = {v: k for k, v in CONTRACT_CODES.items()}
    observations: dict[str, set[date]] = {root: set() for root in CONTRACT_CODES}
    names: dict[str, set[str]] = {root: set() for root in CONTRACT_CODES}
    for row in table:
        raw = row.get("CFTC_Contract_Market_Code", "").strip().upper()
        if raw not in by_code:
            continue
        if not _CODE_RE.fullmatch(raw):
            raise CftcSourceError("WRONG_MARKET_CODE")
        root = by_code[raw]
        market_name = row.get("Market_and_Exchange_Names", "").strip().upper()
        if not market_name or " - " not in market_name:
            raise CftcSourceError("UNVERIFIED_EXCHANGE_NAME")
        if root in ("CL", "NG") and "NEW YORK MERCANTILE EXCHANGE" not in market_name:
            raise CftcSourceError("WRONG_NYMEX_EXCHANGE")
        if root in ("GC", "HG") and "COMMODITY EXCHANGE" not in market_name:
            raise CftcSourceError("WRONG_COMEX_EXCHANGE")
        if root in ("ZC", "ZS") and "CHICAGO BOARD OF TRADE" not in market_name:
            raise CftcSourceError("WRONG_CBOT_EXCHANGE")
        try:
            day = date.fromisoformat(row["As_of_Date_Form_YYYY-MM-DD"].strip())
        except (KeyError, ValueError) as exc:
            raise CftcSourceError("BAD_CFTC_REPORT_DATE") from exc
        if day.year != year or day.weekday() != 1 or day >= date(2022, 1, 1):
            raise CftcSourceError("REPORT_DATE_OUTSIDE_AUDIT_SCOPE")
        if day in observations[root]:
            raise CftcSourceError("DUPLICATE_CFTC_MARKET_WEEK")
        for field in (
            "Open_Interest_All", "M_Money_Positions_Long_All",
            "M_Money_Positions_Short_All",
        ):
            try:
                n = int(row[field].replace(",", "").strip())
            except (KeyError, ValueError) as exc:
                raise CftcSourceError("BAD_POSITION_SCHEMA") from exc
            if n < 0:
                raise CftcSourceError("NEGATIVE_POSITION_FIELD")
        observations[root].add(day)
        names[root].add(market_name)
    results: dict[str, Any] = {}
    for root in sorted(CONTRACT_CODES):
        dates = sorted(observations[root])
        if len(dates) < 40 or len(dates) > 54:
            raise CftcSourceError("ROOT_MISSING_WEEKS_" + root)
        results[root] = {
            "cftc_market_code": CONTRACT_CODES[root],
            "weekly_reports": len(dates),
            "first_report_asof_tuesday": dates[0].isoformat(),
            "last_report_asof_tuesday": dates[-1].isoformat(),
            "market_names_observed": sorted(names[root]),
            "expiry_specific": False,
            "has_bidask": False,
            "has_daily_ohlcv": False,
            "known_original_release_timestamp_each_report": False,
        }
    return {
        "year": year,
        "official_archive_url": URL.format(year=year),
        "zip_sha256": digest,
        "records_by_root": results,
    }


def fetch_year(year: int) -> dict[str, Any]:
    req = urllib.request.Request(
        URL.format(year=year),
        headers={"User-Agent": "QORE-PUBLIC-CFTC-SOURCE-RESEARCH/1.0"},
    )
    with urllib.request.urlopen(req, timeout=80) as response:
        data = response.read(30_000_001)
    return parse_cftc_source(data, year)


def main() -> None:
    annual = [fetch_year(year) for year in YEARS]
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "source_issuer": "US-CFTC",
        "source_class": "disaggregated-futures-only-weekly-aggregate",
        "source_archive_years_actually_checked": list(YEARS),
        "all_2012_2021_years_checked": False,
        "roots_expected": sorted(CONTRACT_CODES),
        "root_count_verified_in_sample": 6,
        "sample_years": annual,
        "source_has_native_expiry_ohlcv": False,
        "source_has_historical_release_asof_per_row": False,
        "source_is_executable_futures_market_data": False,
        "data_use_or_redistribution_rights_independently_certified": False,
        "hypothesis_tested": False,
        "net_trading_edge_demonstrated": False,
        "heldout_2022_plus_read": False,
        "market_data_spend_usd": 0,
    }
    canonical = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    receipt["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    result = Path("artifacts/research/cftc_sixroots_source_audit.json")
    result.parent.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    for row in annual:
        print("CFTC_SOURCE_YEAR", row["year"], row["zip_sha256"])
        for root, details in row["records_by_root"].items():
            print("CFTC_SOURCE_ROOT", root, details["weekly_reports"])
    print("CFTC_SOURCE_AUDIT_ONLY_NON_EXECUTABLE_NO_HOLDOUT_NO_PNL")
    print("CFTC_SOURCE_RECEIPT_SHA256", receipt["receipt_sha256"])


if __name__ == "__main__":
    main()
