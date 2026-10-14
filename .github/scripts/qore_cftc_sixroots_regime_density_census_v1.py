"""Research value from already verified CFTC data: extreme-regime DENSITY only.

No EIA, OHLCV, FX prices, returns, PnL, strategy selection, outcome p-values,
position-level output, forward test, or prior H-COT-2 reopening. Re-download
only official public 2012-2021 CFTC archives pinned by earlier SHA256 audit.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from qore_futures_a_cftc_managed_money_one_shot_screen_v1 import (
    CFTC_URL,
    DIGESTS,
)
from qore_futures_a_cftc_sixroots_public_source_probe_v1 import (
    CONTRACT_CODES,
)

SCHEMA = "qore.cftc.sixroots.extreme-density-source-only.v1"
Z_LOOKBACK = 104
Z_THRESHOLD = 2.0
COOLDOWN_REPORTS = 8
REQUIRED = {
    "CFTC_Contract_Market_Code",
    "As_of_Date_In_Form_YYMMDD",
    "Market_and_Exchange_Names",
    "Open_Interest_All",
    "M_Money_Positions_Long_All",
    "M_Money_Positions_Short_All",
}
VENUES = {
    "CL": "NEW YORK MERCANTILE EXCHANGE",
    "NG": "NEW YORK MERCANTILE EXCHANGE",
    "GC": "COMMODITY EXCHANGE",
    "HG": "COMMODITY EXCHANGE",
    "ZC": "CHICAGO BOARD OF TRADE",
    "ZS": "CHICAGO BOARD OF TRADE",
}


class CftcDensityError(ValueError):
    """Do not use a source or identity that differs from certified CFTC archives."""


@dataclass(frozen=True)
class WeeklyPosition:
    asof: date
    net_oi: float


def decode_year(binary: bytes, year: int) -> dict[str, list[WeeklyPosition]]:
    """Pure census decoder; real data accepted only when archive digest matches."""
    if year not in DIGESTS or hashlib.sha256(binary).hexdigest() != DIGESTS[year]:
        raise CftcDensityError("ARCHIVE_SHA_MISMATCH")
    if len(binary) > 30_000_000:
        raise CftcDensityError("ARCHIVE_TOO_LARGE")
    try:
        with zipfile.ZipFile(io.BytesIO(binary)) as archive:
            members = [
                member for member in archive.infolist()
                if not member.is_dir()
                and member.filename.lower().endswith((".txt", ".csv"))
            ]
            if len(members) != 1 or members[0].file_size > 55_000_000:
                raise CftcDensityError("ARCHIVE_LAYOUT_OR_DECOMPRESSION_LIMIT")
            contents = archive.read(members[0])
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise CftcDensityError("INVALID_ARCHIVE") from exc
    reader = csv.DictReader(io.StringIO(contents.decode("latin-1")))
    if reader.fieldnames is None or not REQUIRED.issubset(reader.fieldnames):
        raise CftcDensityError("CFTC_SCHEMA_CHANGED")
    roots = {code: name for name, code in CONTRACT_CODES.items()}
    records: dict[str, list[WeeklyPosition]] = {
        root: [] for root in CONTRACT_CODES
    }
    seen: dict[str, set[date]] = {root: set() for root in CONTRACT_CODES}
    for row in reader:
        code = row["CFTC_Contract_Market_Code"].strip()
        if code not in roots:
            continue
        root = roots[code]
        venue = row["Market_and_Exchange_Names"].upper()
        if VENUES[root] not in venue:
            raise CftcDensityError("VENUE_IDENTITY_MISMATCH_" + root)
        raw_day = row["As_of_Date_In_Form_YYMMDD"].strip()
        if not raw_day.isdecimal() or len(raw_day) not in (6, 8):
            raise CftcDensityError("BAD_OR_MISSING_ASOF_DATE")
        try:
            fmt = "%y%m%d" if len(raw_day) == 6 else "%Y%m%d"
            stamp = datetime.strptime(raw_day, fmt).date()
            oi = int(row["Open_Interest_All"].replace(",", "").strip())
            longs = int(row["M_Money_Positions_Long_All"].replace(",", "").strip())
            shorts = int(row["M_Money_Positions_Short_All"].replace(",", "").strip())
        except (KeyError, ValueError) as exc:
            raise CftcDensityError("CORRUPT_CFTC_ROW") from exc
        if (
            stamp.year != year or stamp >= date(2022, 1, 1)
            or stamp in seen[root] or oi <= 0 or longs < 0 or shorts < 0
        ):
            raise CftcDensityError("INVALID_ASOF_OR_POSITION")
        seen[root].add(stamp)
        records[root].append(WeeklyPosition(stamp, (longs - shorts) / oi))
    for root, entries in records.items():
        if not 40 <= len(entries) <= 54:
            raise CftcDensityError("MISSING_OR_EXCESS_WEEKLY_ROOT_" + root)
        entries.sort(key=lambda v: v.asof)
    return records


def compute_z_preceding_104(rows: list[WeeklyPosition]) -> list[float | None]:
    """Current position is NOT part of historical mean/std estimate."""
    output: list[float | None] = [None] * len(rows)
    for i in range(Z_LOOKBACK, len(rows)):
        prior = [e.net_oi for e in rows[i - Z_LOOKBACK:i]]
        sigma = statistics.stdev(prior)
        if sigma > 0 and math.isfinite(sigma):
            output[i] = (rows[i].net_oi - statistics.mean(prior)) / sigma
    return output


def _count_streaks(signs: list[int]) -> dict[str, int | float]:
    spans: list[int] = []
    length = 0
    last = 0
    for sign in [*signs, 0]:
        if sign != 0 and sign == last:
            length += 1
        else:
            if length > 0:
                spans.append(length)
            length = int(sign != 0)
        last = sign
    if not spans:
        return {"streaks": 0, "median_weeks": 0.0, "max_weeks": 0}
    return {
        "streaks": len(spans),
        "median_weeks": float(statistics.median(spans)),
        "max_weeks": max(spans),
    }


def summarize_root(rows: list[WeeklyPosition]) -> dict[str, Any]:
    if len(set(x.asof for x in rows)) != len(rows):
        raise CftcDensityError("DUPLICATE_SOURCE_DATES")
    ordered = sorted(rows, key=lambda r: r.asof)
    if any(x.asof >= date(2022, 1, 1) for x in ordered):
        raise CftcDensityError("RESERVED_YEAR_PROHIBITED")
    zvals = compute_z_preceding_104(ordered)
    signs = [
        1 if x is not None and x >= Z_THRESHOLD else
        (-1 if x is not None and x <= -Z_THRESHOLD else 0)
        for x in zvals
    ]
    selected: list[tuple[int, int, date]] = []
    first_crossings = 0
    ignored_due_to_cooldown = 0
    for i in range(Z_LOOKBACK + 1, len(ordered)):
        sign = signs[i]
        if sign == 0 or sign == signs[i - 1]:
            continue
        first_crossings += 1
        if selected and i - selected[-1][0] < COOLDOWN_REPORTS:
            ignored_due_to_cooldown += 1
            continue
        selected.append((i, sign, ordered[i].asof))
    per_year: dict[str, dict[str, int]] = {}
    for year in range(2012, 2022):
        observed = [i for i, v in enumerate(ordered) if v.asof.year == year]
        per_year[str(year)] = {
            "weeks_available": len(observed),
            "weeks_with_eligible_z": sum(zvals[i] is not None for i in observed),
            "weeks_z_ge_pos2": sum(signs[i] == 1 for i in observed),
            "weeks_z_le_neg2": sum(signs[i] == -1 for i in observed),
            "crossings_admitted_after_8_report_cooldown": sum(
                stamp.year == year for _, _, stamp in selected
            ),
        }
    return {
        "original_weeks": len(ordered),
        "eligible_z_weeks": sum(x is not None for x in zvals),
        "extreme_positive_weeks": signs.count(1),
        "extreme_negative_weeks": signs.count(-1),
        "streaks_extreme": _count_streaks(signs),
        "first_extreme_crossings_unfiltered": first_crossings,
        "crossings_rejected_by_8_report_cooldown": ignored_due_to_cooldown,
        "crossings_admitted_after_8_report_cooldown": len(selected),
        "admitted_positive": sum(sign == 1 for _, sign, _ in selected),
        "admitted_negative": sum(sign == -1 for _, sign, _ in selected),
        "per_year": per_year,
        "observation_mode": "SOURCE_DESCRIPTIVE_NO_MARKET_OUTCOMES",
    }


def fetch_census() -> dict[str, Any]:
    series: dict[str, list[WeeklyPosition]] = {
        root: [] for root in CONTRACT_CODES
    }
    digests: dict[str, str] = {}
    for year in sorted(DIGESTS):
        req = urllib.request.Request(
            CFTC_URL.format(year=year),
            headers={"User-Agent": "QORE-CFTC-NO-EDGE-REGIME-DENSITY/1.0"},
        )
        with urllib.request.urlopen(req, timeout=80) as response:
            body = response.read(30_000_001)
        parsed = decode_year(body, year)
        digests[str(year)] = hashlib.sha256(body).hexdigest()
        for root in CONTRACT_CODES:
            series[root].extend(parsed[root])
    results = {root: summarize_root(rows) for root, rows in sorted(series.items())}
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "years": list(sorted(DIGESTS)),
        "source_zip_sha256_by_year": digests,
        "market_names": sorted(CONTRACT_CODES),
        "expected_market_count": 6,
        "expected_weekly_market_records": 3132,
        "counts": results,
        "z_threshold": Z_THRESHOLD,
        "z_lookback_prior_reports": Z_LOOKBACK,
        "cooldown_reports": COOLDOWN_REPORTS,
        "asset_is_public_retrievable_source_not_raw_archival": True,
        "past_cftc_edge_hypotheses_reopened": False,
        "market_price_outcomes_loaded": False,
        "2022_plus_holdout_inspected": False,
        "trading_edge_calculated": False,
        "pnl_pf_dd_calculated": False,
        "certification_allowed": False,
        "real_money_or_live": False,
        "cost_usd": 0,
    }
    if sum(v["original_weeks"] for v in results.values()) != 3132:
        raise CftcDensityError("TEN_YEAR_ROOT_COVERAGE_NOT_CANONICAL")
    blob = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)
    receipt["receipt_sha256"] = hashlib.sha256(blob.encode()).hexdigest()
    return receipt


def main() -> None:
    report = fetch_census()
    path = Path("artifacts/research/cftc_regime_density_sixroots.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    for root, record in report["counts"].items():
        print(
            "CFTC_REGIME_DENSITY", root,
            "extreme_pos_weeks", record["extreme_positive_weeks"],
            "extreme_neg_weeks", record["extreme_negative_weeks"],
            "admitted_crossings", record["crossings_admitted_after_8_report_cooldown"],
            "max_consecutive_weeks", record["streaks_extreme"]["max_weeks"],
        )
    print("CFTC_REGIME_ONLY_NO_OUTCOME_NO_PNL_NO_HOLDOUT")
    print("RECEIPT_SHA256", report["receipt_sha256"])


if __name__ == "__main__":
    main()
