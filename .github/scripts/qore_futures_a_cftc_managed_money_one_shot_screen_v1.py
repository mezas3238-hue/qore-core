"""One-shot PRE-REGISTERED CFTC positioning vs EIA F1 directional association.

No execution, returns, per-contract expiries, profit factor or usable edge claim.
Only DEV 2012-2018 and DIAG 2019-2021; EIA 2022+ outcomes never evaluated.
See scientific prereg at commit e6821685cbefd775f820865e4d2b0d03ab94dff2.
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_futures_a_eia_f1f2_predictive_screen_v1 import (
    read_frozen_eia_xls,
)

PREREG_SHA = "e6821685cbefd775f820865e4d2b0d03ab94dff2"
PREREG_PATH = (
    "docs/research/"
    "QORE_FUTURES_A_CFTC_MANAGED_MONEY_ONE_SHOT_EXPLORATORY_PREREG_2026-10-13.md"
)
DIGESTS = {
    2012: "79db37521556a5aa8acc84bd3ca86aa6bf80fb4c5d4a8013dfb215fc760f1e95",
    2013: "c9bc647013b9b2f1c18e96fdaed95dc94af57c3a949e9fe7dd94aee06f3837bc",
    2014: "a29872d680f595078062130274374ecb38dc2a24d86f1531a59f52b8abca7eea",
    2015: "36aacb4389831a89996ba5366c91eedeaa32a55abca8265325bc52d74b06ca34",
    2016: "50f52674fd924d24c794b921c29342be7d35cbe0a241ac823925ccf43ca1a6d2",
    2017: "6fc467b989df527a4fbea4ba07185e8951f35cb72563f156488904a37c100e43",
    2018: "df4bf7d72e8984d6ea04087f793c9f2bf3503ea8c2149f4b01eedeef4fbe40a8",
    2019: "942a438bcc6f66e65aaf594a1a1fdb8c1505fe4a0feece77a1fd97270317e753",
    2020: "0aa03c0fd6360f56b6897b6eaff30e8dba774c826bf93cac61598312e19bd1cd",
    2021: "12d5d49a8963367fd3439050e3e20e6a5338757dfa083432795c5556827ff8ae",
}
CONTRACT_CODES = {"WTI": "067651", "NG": "023651"}
EIA_KEYS = {"WTI": "WTI_F1", "NG": "NG_F1"}
CFTC_URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
REQUIRED_FIELDS = (
    "CFTC_Contract_Market_Code",
    "As_of_Date_In_Form_YYMMDD",
    "Open_Interest_All",
    "M_Money_Positions_Long_All",
    "M_Money_Positions_Short_All",
)
BLACKOUTS = ((date(2013, 9, 1), date(2013, 11, 30)),
             (date(2018, 12, 1), date(2019, 4, 30)))
ALPHA = 0.025
MIN_EFFECT = 0.10
MIN_GROUP = 8


class CftcScreenError(ValueError):
    """Cannot score any result if preregistered sources or chronology fail."""


@dataclass(frozen=True)
class CftcPosition:
    report_date: date
    net_oi: float


@dataclass(frozen=True)
class DiagnosticEvent:
    month: str
    positive_change: bool
    future_reference_up: bool


def _fisher_greater(a: int, b: int, c: int, d: int) -> float:
    total = a + b + c + d
    first = a + b
    up = a + c
    down = b + d
    denom = math.comb(total, first)
    return sum(
        math.comb(up, k) * math.comb(down, first - k) / denom
        for k in range(a, min(first, up) + 1)
        if 0 <= first - k <= down
    )


def _read_cftc_archive(data: bytes, year: int) -> dict[str, list[CftcPosition]]:
    if year not in DIGESTS or hashlib.sha256(data).hexdigest() != DIGESTS[year]:
        raise CftcScreenError("CFTC_SOURCE_DIGEST_MISMATCH")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            candidates = [
                x for x in z.infolist()
                if x.filename.lower().endswith((".txt", ".csv")) and not x.is_dir()
            ]
            if len(candidates) != 1 or candidates[0].file_size > 55_000_000:
                raise CftcScreenError("CFTC_ZIP_LAYOUT_OR_SIZE")
            source = z.read(candidates[0]).decode("latin-1")
    except (zipfile.BadZipFile, UnicodeError, OSError) as exc:
        raise CftcScreenError("CFTC_BAD_ZIP") from exc
    reader = csv.DictReader(io.StringIO(source))
    if reader.fieldnames is None or not set(REQUIRED_FIELDS).issubset(reader.fieldnames):
        raise CftcScreenError("CFTC_FIELDS_CHANGED")
    reverse = {code: name for name, code in CONTRACT_CODES.items()}
    rows: dict[str, list[CftcPosition]] = {name: [] for name in CONTRACT_CODES}
    seen: dict[str, set[date]] = {name: set() for name in CONTRACT_CODES}
    for item in reader:
        code = item["CFTC_Contract_Market_Code"].strip()
        if code not in reverse:
            continue
        root = reverse[code]
        stamp = item["As_of_Date_In_Form_YYMMDD"].strip()
        try:
            fmt = "%y%m%d" if len(stamp) == 6 else "%Y%m%d"
            day = datetime.strptime(stamp, fmt).date()
            oi = int(item["Open_Interest_All"].strip().replace(",", ""))
            long = int(item["M_Money_Positions_Long_All"].strip().replace(",", ""))
            short = int(item["M_Money_Positions_Short_All"].strip().replace(",", ""))
        except (KeyError, ValueError) as exc:
            raise CftcScreenError("CFTC_BAD_ROW") from exc
        if (day.year != year or day >= date(2022, 1, 1)
                or day in seen[root] or oi <= 0 or long < 0 or short < 0):
            raise CftcScreenError("CFTC_BAD_ASOF_OR_POSITIONS")
        seen[root].add(day)
        rows[root].append(CftcPosition(day, (long - short) / oi))
    for root, values in rows.items():
        if not 40 <= len(values) <= 54:
            raise CftcScreenError("CFTC_MISSING_ROOT_WEEKS_" + root)
        values.sort(key=lambda x: x.report_date)
    return rows


def _blocked(day: date) -> bool:
    return any(start <= day <= end for start, end in BLACKOUTS)


def build_events(
    weeks: list[CftcPosition], prices: dict[date, float],
) -> tuple[list[DiagnosticEvent], dict[str, int]]:
    """One first eligible CFTC report/month, delayed 21d, then five EIA dates.

    The result is a diagnostic, NOT verified first-publication-asof or PnL.
    """
    days = sorted(prices)
    accepted: list[DiagnosticEvent] = []
    counters = {"monthly_reports_considered": 0, "blackout_reports": 0,
                "missing_entry_or_exit": 0, "signal_or_price_ties": 0}
    months: set[tuple[int, int]] = set()
    for i in range(4, len(weeks)):
        row = weeks[i]
        month = (row.report_date.year, row.report_date.month)
        if month in months:
            continue
        months.add(month)
        counters["monthly_reports_considered"] += 1
        if _blocked(row.report_date):
            counters["blackout_reports"] += 1
            continue
        old = weeks[i - 4]
        if (row.report_date - old.report_date).days > 35:
            counters["missing_entry_or_exit"] += 1
            continue
        j = bisect.bisect_left(days, row.report_date + timedelta(days=21))
        if j + 5 >= len(days):
            counters["missing_entry_or_exit"] += 1
            continue
        entry, exit_day = days[j], days[j + 5]
        if not (
            (entry.year <= 2018 and exit_day.year <= 2018)
            or (2019 <= entry.year <= 2021 and 2019 <= exit_day.year <= 2021)
        ):
            counters["missing_entry_or_exit"] += 1
            continue
        if row.net_oi == old.net_oi or prices[entry] == prices[exit_day]:
            counters["signal_or_price_ties"] += 1
            continue
        accepted.append(DiagnosticEvent(
            f"{month[0]}-{month[1]:02d}",
            row.net_oi > old.net_oi,
            prices[exit_day] > prices[entry],
        ))
    return accepted, counters


def score(events: list[DiagnosticEvent], low: int, high: int) -> dict[str, Any]:
    sample = [e for e in events if low <= int(e.month[:4]) <= high]
    a = sum(e.future_reference_up for e in sample if e.positive_change)
    b = sum(not e.future_reference_up for e in sample if e.positive_change)
    c = sum(e.future_reference_up for e in sample if not e.positive_change)
    d = sum(not e.future_reference_up for e in sample if not e.positive_change)
    n1, n0 = a + b, c + d
    answer: dict[str, Any] = {"events": len(sample), "x_up_events": n1,
                              "x_down_events": n0, "price_up_x_up": a,
                              "price_up_x_down": c, "minimum_each_state": MIN_GROUP}
    if min(n1, n0) < MIN_GROUP:
        answer.update({"delta_probability": None, "fisher_one_sided_p": None,
                       "window_verdict": "INCONCLUSIVE_TOO_FEW_EVENTS"})
        return answer
    delta = a / n1 - c / n0
    p = _fisher_greater(a, b, c, d)
    passed = delta >= MIN_EFFECT and p <= ALPHA
    answer.update({"delta_probability": delta, "fisher_one_sided_p": p,
                   "window_verdict": "PRELIMINARY_SUPPORT" if passed else "NO_SUPPORT"})
    return answer


def fetch_and_score() -> dict[str, Any]:
    weekly: dict[str, list[CftcPosition]] = {name: [] for name in CONTRACT_CODES}
    for year in sorted(DIGESTS):
        req = urllib.request.Request(
            CFTC_URL.format(year=year),
            headers={"User-Agent": "QORE-ONE-SHOT-CFTC-PREREG/1.0"},
        )
        with urllib.request.urlopen(req, timeout=80) as response:
            raw = response.read(30_000_001)
        parsed = _read_cftc_archive(raw, year)
        for name, rows in parsed.items():
            weekly[name].extend(rows)
    result: dict[str, Any] = {
        "schema": "qore.futures-a.cftc-eia.one-shot-diagnostic.v1",
        "prereg_commit": PREREG_SHA,
        "source_cftc": "disaggregated-futures-only-2012-2021-sha256-pinned",
        "source_eia": "frozen-reference-f1-daily-xls",
        "family_tests": 2, "family_per_root_alpha": ALPHA,
        "minimum_probability_effect": MIN_EFFECT,
        "reserve_2022_plus_outcomes_evaluated": False,
        "unverified_first_published_at": True,
        "native_expiry_trading_prices_available": False,
        "economic_pnl_calculated": False,
        "trader_eligible": False, "live_enabled": False,
        "market_data_spend_usd": 0,
        "roots": {},
    }
    for root in ("NG", "WTI"):
        prices = read_frozen_eia_xls(EIA_KEYS[root])
        events, reasons = build_events(
            sorted(weekly[root], key=lambda x: x.report_date), prices
        )
        dev = score(events, 2012, 2018)
        diag = score(events, 2019, 2021)
        verdict = (
            "PRELIMINARY_DIAGNOSTIC_ASSOCIATION_ONLY"
            if dev["window_verdict"] == diag["window_verdict"] == "PRELIMINARY_SUPPORT"
            else "NO_SUPPORT_UNDER_PREREG"
        )
        result["roots"][root] = {
            "source_weekly_rows": len(weekly[root]),
            "counts": reasons,
            "dev": dev, "diag": diag, "scientific_decision": verdict,
        }
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    result["receipt_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main() -> None:
    output = fetch_and_score()
    path = Path("artifacts/research/cftc_mm_one_shot_diag.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n")
    for root, line in output["roots"].items():
        for stage in ("dev", "diag"):
            print("CFTC_DIAG", root, stage, json.dumps(line[stage], sort_keys=True))
        print("CFTC_VERDICT", root, line["scientific_decision"])
    print("CFTC_ONE_SHOT_DIAGNOSTIC_NOT_TRADEABLE_NO_HOLDOUT_NO_PNL")
    print("RECEIPT_SHA256", output["receipt_sha256"])


if __name__ == "__main__":
    main()
