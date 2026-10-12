"""QORE CPI source-only pre-G1: verify frozen 24 PIT dates and power scenarios.

Consumes ONLY G0/G0B date-identity metadata and binary minute-presence
witnesses. Never opens NAS100 OHLC, CPI values, forecasts, fees or any P&L.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

IDENTITY = "QORE_EVENT_CPI_PRE_G1_SOURCE_ONLY_POWER_FEASIBILITY_V1"
G0_RUN = 38189483643
G0_BLS_ARTIFACT = 11720651765
G0_CIBO_PRESENCE_ARTIFACT = 11720822239
G0B_RUN = 38191275999
G0B_ARCHIVE_ARTIFACT = 11721212991
EXPECTED_BLS_HASH = "7a480476b0269d1b673330c780ed39c5bc7af10552cba6c7a098f55b209fdb3e"
EXPECTED_CIBO_HASH = "648b10a01ae7610cfad66619db7ec9833679afe4774c48f141c4af8e82de25d5"
EXPECTED_G0B_HASH = "3d78e694b353afad2bafd1c061117f8c1633fcedd79e00eebd57b387589f51d3"
FROZEN_24 = (
    "2016-10-18", "2016-11-17", "2016-12-15",
    "2017-03-15", "2017-10-13",
    "2018-03-13", "2018-10-11",
    "2019-03-12", "2019-10-10",
    "2020-03-11", "2020-10-13",
    "2021-03-10", "2021-10-13",
    "2022-03-10", "2022-10-13",
    "2023-03-14", "2023-10-12",
    "2024-03-12", "2024-10-10",
    "2025-03-12", "2025-10-24",
    "2026-01-13", "2026-05-12", "2026-09-11",
)
ALPHA = 0.05
POWER_GOAL = 0.80
Z_TWO_SIDED = 1.959963984540054
Z_POWER_80 = 0.8416212335729143
SIGMA_SCENARIOS_BPS = (10, 20, 40, 60)
EFFECT_SCENARIOS_BPS = (5, 10, 15)
N_SCENARIOS = (113, 56, 560)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified(root: Path, filename: str, expected: str) -> Any:
    path = root / filename
    if not path.is_file() or sha256(path) != expected:
        raise ValueError("original immutable G0/G0B witness SHA mismatch: " + filename)
    return json.loads(path.read_text(encoding="utf-8"))


def normal_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def mde_bps(*, n: int, sigma_bps: float) -> float:
    if n <= 0 or sigma_bps <= 0:
        raise ValueError("N and sigma must be positive")
    return (Z_TWO_SIDED + Z_POWER_80) * sigma_bps / math.sqrt(n)


def hypothetical_power(*, n: int, effect_bps: float, sigma_bps: float) -> float:
    if n <= 0 or sigma_bps <= 0:
        raise ValueError("N and sigma must be positive")
    signal = effect_bps * math.sqrt(n) / sigma_bps
    return (1 - normal_cdf(Z_TWO_SIDED - signal)) + normal_cdf(
        -Z_TWO_SIDED - signal
    )


def audit(
    calendar_root: Path,
    presence_root: Path,
    archive_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calendar = load_verified(
        calendar_root, "cpi-bls-g0-dated-events.json", EXPECTED_BLS_HASH
    )
    presence = load_verified(
        presence_root, "cpi-nas100-m1-g0-event-presence.json", EXPECTED_CIBO_HASH
    )
    archive = load_verified(
        archive_root, "g0b-release-header-by-date.json", EXPECTED_G0B_HASH
    )
    if not all(isinstance(rows, list) and len(rows) == 119 for rows in (
        calendar, presence, archive
    )):
        raise ValueError("immutable CPI 119-row population changed")
    cal_dates = [row["ny_date"] for row in calendar]
    pre_dates = [row["date_ny"] for row in presence]
    arc_dates = [row["date_ny"] for row in archive]
    if not (cal_dates == pre_dates == arc_dates == sorted(cal_dates)):
        raise ValueError("CPI G0/G0B date order does not match")
    if len(set(cal_dates)) != 119:
        raise ValueError("duplicate CPI source dates")
    if any(x["status"] != "ARCHIVED_RELEASE_HEADER_MATCH"
           or x["archive_header_confirmed"] is not True
           or x["archive_index_match"] is not True
           for x in archive):
        raise ValueError("one or more CPI releases not individually verified")
    if len(FROZEN_24) != 24 or len(set(FROZEN_24)) != 24:
        raise ValueError("frozen 24-event sample size drift")
    lookup = set(cal_dates)
    unknown = sorted(set(FROZEN_24) - lookup)
    if unknown:
        raise ValueError("PIT source audit dates not in original BLS 119: " + str(unknown))
    if any(row["provider_ohlc_read"] is not False
           or row["provider_bidask_fills_observed"] is not False
           for row in presence):
        raise ValueError("G0 presence metadata boundaries violated")
    covered = sum(x["window_all_candles_present"] for x in presence)
    if covered != 113:
        raise ValueError("G0 source-reported 113/119 complete window count drift")
    with_meta = {
        row["ny_date"]: (row, presence[i], archive[i])
        for i, row in enumerate(calendar)
    }
    per_date: list[dict[str, Any]] = []
    for d in FROZEN_24:
        cal, price_presence, original = with_meta[d]
        per_date.append({
            "ny_date": d,
            "release_reference_month": cal["ref_month"],
            "release_reference_year": cal["ref_year"],
            "original_bls_release_header": original["status"],
            "nas100_71_m1_present": bool(price_presence["window_all_candles_present"]),
            "consensus_vendor_A_pre_t0_available": False,
            "consensus_vendor_B_pre_t0_available": False,
            "consensus_comparison_executed": False,
            "event_time_bid_ask_execution_cost_verified": False,
            "economic_returns_opened": False,
        })
    selected_covered = sum(r["nas100_71_m1_present"] for r in per_date)
    scenarios: list[dict[str, Any]] = []
    for n in N_SCENARIOS:
        for sigma in SIGMA_SCENARIOS_BPS:
            scenarios.append({
                "n_assumed": n, "sigma_assumed_bps": sigma,
                "mde_bps_at_alpha5_power80_two_sided": mde_bps(
                    n=n, sigma_bps=sigma
                ),
                "hypothetical_power_for_effects": {
                    str(effect): hypothetical_power(
                        n=n, effect_bps=effect, sigma_bps=sigma
                    ) for effect in EFFECT_SCENARIOS_BPS
                },
                "hypothetical_independent_events_only": True,
                "not_an_empirical_volatility_estimate": True,
            })
    report = {
        "identity": IDENTITY,
        "g0_calendar_artifact": G0_BLS_ARTIFACT,
        "g0_presence_artifact": G0_CIBO_PRESENCE_ARTIFACT,
        "g0b_release_archive_artifact": G0B_ARCHIVE_ARTIFACT,
        "g0_run": G0_RUN, "g0b_run": G0B_RUN,
        "all_source_hashes_verified": True,
        "full_documented_releases": 119,
        "complete_timestamp_event_windows": covered,
        "frozen_provider_comparison_events": len(FROZEN_24),
        "frozen_comparison_dates_all_exist_in_original_BLS": True,
        "frozen_comparison_nas100_71_m1_complete": selected_covered,
        "frozen_comparison_nas100_missing_dates": [
            x["ny_date"] for x in per_date if not x["nas100_71_m1_present"]
        ],
        "bls_source_counts_per_publication_year": dict(
            sorted(Counter(str(date.fromisoformat(x).year) for x in cal_dates).items())
        ),
        "n_valid_for_future_G1_at_most": covered,
        "independent_events_assumed_for_planning_only": True,
        "alpha_two_sided": ALPHA, "power_target": POWER_GOAL,
        "power_scenarios_only": scenarios,
        "effect_estimate_measured": False,
        "sigma_estimate_measured": False,
        "PIT_vintage_verified": False,
        "two_independent_forecast_sources_compared": False,
        "CPI_window_0835_0905_cost_verified": False,
        "calendar_known_asof_verified": False,
        "performance_or_returns_opened": False,
        "macro_pooling_authorized": False,
        "candidate_macro_family": "CPI_ONLY",
        "actual_trading_signal_authorized": False,
        "G1_economic_authorized": False,
        "status": "BLOCKED_NOT_EVALUABLE_INFRASTRUCTURE",
        "no_vps_no_mt5_no_live_no_traders": True,
    }
    return report, per_date


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("calendar_metadata", type=Path)
    p.add_argument("nas100_presence_metadata", type=Path)
    p.add_argument("original_release_headers_metadata", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    report, sample = audit(
        args.calendar_metadata,
        args.nas100_presence_metadata,
        args.original_release_headers_metadata,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    for name, obj in (
        ("cpi-pre-g1-feasibility-power-scenarios.json", report),
        ("cpi-pre-g1-24-date-source-verification.json", sample),
    ):
        path = args.output / name
        path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
        (args.output / (name + ".sha256")).write_text(
            sha256(path) + "  " + name + "\n"
        )
    print(json.dumps({
        "status": report["status"],
        "frozen_24_verified": report["frozen_comparison_dates_all_exist_in_original_BLS"],
        "complete_CPI_M1_windows": report["complete_timestamp_event_windows"],
        "frozen_24_M1_windows": report["frozen_comparison_nas100_71_m1_complete"],
        "PIT_or_prices_opened": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
