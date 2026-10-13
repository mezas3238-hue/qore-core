"""Preregistered EIA WTI/NG F1/F2 diagnostic predictive screen, no PnL.

See docs/research/QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_PREREG_2026-10-13.md
for hypotheses, partitions, strict source hashes and stop conditions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import xlrd
from scipy.stats import fisher_exact

SOURCES: dict[str, tuple[str, str]] = {
    "WTI_F1": (
        "https://www.eia.gov/dnav/pet/hist_xls/RCLC1d.xls",
        "a55a70d2438ebdc600a77f9d3f9c46be1e2f480ac5ffec3bb753c61cf21db0c9",
    ),
    "WTI_F2": (
        "https://www.eia.gov/dnav/pet/hist_xls/RCLC2d.xls",
        "31d8a01ae5bd3cb8753925743802c9e77f11bd54ce1b5e0fd4d91d91940ecea7",
    ),
    "NG_F1": (
        "https://www.eia.gov/dnav/ng/hist_xls/RNGC1d.xls",
        "1e71a774943c00cdba337c8be1c9888ea1d56b175c446527cc0d94f7dc2b03f1",
    ),
    "NG_F2": (
        "https://www.eia.gov/dnav/ng/hist_xls/RNGC2d.xls",
        "abf42f8f7c6acc9581d283688d7571336a0ee4850c7ae43e433e37720f655aee",
    ),
}
DEV_START = date(2012, 1, 1)
DEV_END = date(2018, 12, 31)
DIAG_START = date(2019, 1, 1)
DIAG_END = date(2021, 12, 31)
HOLDOUT_START = date(2022, 1, 1)
MIN_GROUP_MONTHS = 8
MIN_DELTA = 0.10
P_THRESHOLD = 0.025


class BlockedSourceRevision(Exception):
    """Do not silently update a historically revised or substituted EIA source."""


@dataclass(frozen=True)
class Observation:
    date: date
    f1: float
    f2: float


@dataclass(frozen=True)
class DiagnosticEvent:
    month: str
    signal_backwardation: bool
    reference_f1_up_later: bool


def read_frozen_eia_xls(key: str, *, binary: bytes | None = None) -> dict[date, float]:
    url, expected_sha = SOURCES[key]
    if binary is None:
        request = urllib.request.Request(
            url, headers={"User-Agent": "QORE-EIA-DIAGNOSTIC-FROZEN/1.0"}
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            binary = response.read(8_000_001)
    if len(binary) > 8_000_000:
        raise BlockedSourceRevision("SOURCE_OVER_8MB_" + key)
    actual_sha = hashlib.sha256(binary).hexdigest()
    if actual_sha != expected_sha:
        raise BlockedSourceRevision(
            f"SOURCE_SHA256_MISMATCH_{key}: expected={expected_sha} actual={actual_sha}"
        )
    workbook = xlrd.open_workbook(file_contents=binary, on_demand=True)
    sheet = workbook.sheet_by_name("Data 1")
    points: dict[date, float] = {}
    for i in range(sheet.nrows):
        date_cell = sheet.cell(i, 0)
        price_cell = sheet.cell(i, 1)
        if date_cell.ctype != xlrd.XL_CELL_DATE:
            continue
        day = xlrd.xldate.xldate_as_datetime(
            date_cell.value, workbook.datemode
        ).date()
        # NO holdout market values enter the computation, even as a statistic.
        if not DEV_START <= day < HOLDOUT_START:
            continue
        if price_cell.ctype != xlrd.XL_CELL_NUMBER:
            raise BlockedSourceRevision("NON_NUMERIC_OBSERVATION_" + key)
        price = float(price_cell.value)
        if not math.isfinite(price):
            raise BlockedSourceRevision("NONFINITE_OBSERVATION_" + key)
        if day in points:
            raise BlockedSourceRevision("DUPLICATE_DATE_" + key)
        points[day] = price
    if len(points) < 1700:
        raise BlockedSourceRevision("TOO_FEW_DEV_DIAG_PRICES_" + key)
    return points


def build_monthly_events(
    f1: dict[date, float], f2: dict[date, float]
) -> tuple[list[DiagnosticEvent], dict[str, int]]:
    common = sorted(set(f1) & set(f2))
    events: list[DiagnosticEvent] = []
    reasons: dict[str, int] = {
        "eligible_months": 0,
        "not_enough_same_month_observations": 0,
        "spread_ties": 0,
        "outcome_ties": 0,
        "valid_one_per_month": 0,
    }
    by_month: dict[tuple[int, int], list[date]] = {}
    for day in common:
        by_month.setdefault((day.year, day.month), []).append(day)
    for month, dates in sorted(by_month.items()):
        reasons["eligible_months"] += 1
        if len(dates) < 8:
            reasons["not_enough_same_month_observations"] += 1
            continue
        t, after_two, after_seven = dates[0], dates[2], dates[7]
        assert (t.year, t.month) == (after_seven.year, after_seven.month)
        spread = f1[t] - f2[t]
        price_move = f1[after_seven] - f1[after_two]
        if spread == 0:
            reasons["spread_ties"] += 1
            continue
        if price_move == 0:
            reasons["outcome_ties"] += 1
            continue
        events.append(
            DiagnosticEvent(
                month=f"{month[0]}-{month[1]:02d}",
                signal_backwardation=spread > 0,
                reference_f1_up_later=price_move > 0,
            )
        )
        reasons["valid_one_per_month"] += 1
    return events, reasons


def summarize_window(
    events: list[DiagnosticEvent], *, start: int, end: int
) -> dict[str, Any]:
    xs = [x for x in events if start <= int(x.month[:4]) <= end]
    backwardation = [x for x in xs if x.signal_backwardation]
    contango = [x for x in xs if not x.signal_backwardation]
    up_back = sum(x.reference_f1_up_later for x in backwardation)
    up_cont = sum(x.reference_f1_up_later for x in contango)
    down_back = len(backwardation) - up_back
    down_cont = len(contango) - up_cont
    enough = (
        len(backwardation) >= MIN_GROUP_MONTHS and len(contango) >= MIN_GROUP_MONTHS
    )
    delta: float | None = None
    p: float | None = None
    decision = "INCONCLUSIVE_TOO_FEW_MONTHS"
    if enough:
        delta = up_back / len(backwardation) - up_cont / len(contango)
        _, p_value = fisher_exact(
            [[up_back, down_back], [up_cont, down_cont]],
            alternative="greater",
        )
        p = float(p_value)
        if delta <= 0:
            decision = "NO_POSITIVE_DIRECTION"
        elif delta >= MIN_DELTA and p <= P_THRESHOLD:
            decision = "PRELIMINARY_PREREG_WINDOW_PASS"
        else:
            decision = "NO_SUPPORT_UNDER_PREREG"
    return {
        "window": f"{start}-{end}",
        "n_months": len(xs),
        "n_backwardation_months": len(backwardation),
        "n_contango_months": len(contango),
        "up_backwardation": up_back,
        "down_backwardation": down_back,
        "up_contango": up_cont,
        "down_contango": down_cont,
        "delta_probability_up": round(delta, 10) if delta is not None else None,
        "one_sided_fisher_p": round(p, 10) if p is not None else None,
        "min_months_per_state": MIN_GROUP_MONTHS,
        "minimum_positive_delta": MIN_DELTA,
        "family_alpha_per_root": P_THRESHOLD,
        "decision": decision,
    }


def evaluate_root(
    root: str, f1: dict[date, float], f2: dict[date, float]
) -> dict[str, Any]:
    events, audit = build_monthly_events(f1, f2)
    dev = summarize_window(events, start=2012, end=2018)
    diag = summarize_window(events, start=2019, end=2021)
    judgments = [dev["decision"], diag["decision"]]
    if all(j == "PRELIMINARY_PREREG_WINDOW_PASS" for j in judgments):
        decision = "CANDIDATE_DESERVES_HOLDOUT_PROPOSAL"
    elif "INCONCLUSIVE_TOO_FEW_MONTHS" in judgments:
        decision = "INCONCLUSIVE_TOO_FEW_MONTHS"
    elif "NO_POSITIVE_DIRECTION" in judgments:
        decision = "NO_POSITIVE_DIRECTION"
    else:
        decision = "NO_SUPPORT_UNDER_PREREG"
    return {
        "root": root,
        "months_audit": audit,
        "dev": dev,
        "diag": diag,
        "decision": decision,
        "is_tradable_edge_certified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    prices = {name: read_frozen_eia_xls(name) for name in SOURCES}
    root_reports = [
        evaluate_root(root, prices[f"{root}_F1"], prices[f"{root}_F2"])
        for root in ("WTI", "NG")
    ]
    report: dict[str, Any] = {
        "identity": "QORE_FUTURES_A_EIA_FRONT_RANK_PROSPECTIVE_V1",
        "preregistered_hypothesis_count": 2,
        "source_SHA256": {name: digest for name, (_, digest) in SOURCES.items()},
        "scope": "monthly_first_common_day_signal_2_day_embargo_to_5_day_reference_change",
        "dev": "2012-2018",
        "diag": "2019-2021",
        "holdout_2022_2024": "SEALED_NO_VALUES_LOADED",
        "forward_reference_price_change_not_executable_roll_net": True,
        "market_data_budget_USD": 0,
        "trading_orders": 0,
        "trader_certified": 0,
        "full_source_ready_for_6_roots": False,
        "results": root_reports,
        "fx_holdout_touched": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    for root_result in root_reports:
        print("PREREG_F1F2_DIAGNOSTIC", json.dumps(root_result, sort_keys=True))
    print("NO_TRADABLE_EDGE_CLAIM_HOLDOUT_SEALED_USD0")


if __name__ == "__main__":
    main()
