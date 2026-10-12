"""Single-test 33-symbol TSMOM exploratory weekly calendar-block inference.

Equal-week, equal-symbol gross reference bps: NOT NAV, NOT NET/UTC001/OOS.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_tsmom_daily_weekly import BEGIN, DEV_END, EMBARGO
from qore.research.alpha2_tsmom_daily_weekly import IDENTITY as SOURCE_ID

IDENTITY = "QORE_ALPHA2_TSMOM_D1_EXPOSED_33_FROZEN_GROSS_WEEKLY_BOOTSTRAP_V1"
FROZEN_BLOCK_WEEKS = 4
BOOTSTRAP_DRAWS = 2000
RNG_SEED = 20261012
MIN_ACTIVE_WEEKS = {"DEVELOPMENT": 52, "DIAGNOSTIC": 26}
STRESS_BPS = (0, 1, 3, 5, 10, 20)
ORIGINAL12 = frozenset({
    "AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "NAS100",
    "SP500", "US30", "USDCAD", "USDJPY", "XAGUSD", "XAUUSD",
})


def _iso_week(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def era_weeks(era: str) -> list[str]:
    left, right = (
        (BEGIN, DEV_END) if era == "DEVELOPMENT" else
        (DEV_END, EMBARGO) if era == "DIAGNOSTIC" else
        (None, None)
    )
    if left is None:
        raise ValueError("TSMOM_UNKNOWN_ERA")
    monday = left - timedelta(days=left.weekday())
    out = []
    while monday < right:
        out.append(_iso_week(monday))
        monday += timedelta(days=7)
    return out


def load_all33(root: Path, exact_head: str) -> dict[str, dict]:
    result = {}
    paths = sorted(root.rglob("alpha2-tsmom-daily-weekly-*.json"))
    if len(paths) != 33:
        raise ValueError("TSMOM_ALL33_WORKERS_REQUIRED")
    for p in paths:
        witness = p.with_name(p.name + ".sha256")
        if witness.read_text(encoding="utf-8").strip() != (
            sha256_file(p) + "  " + p.name
        ):
            raise ValueError("TSMOM_WORKER_SHA_CHANGED")
        if (p.parent / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip() != exact_head:
            raise ValueError("TSMOM_ORIGINAL_WORKER_HEAD_MISMATCH")
        a = json.loads(p.read_text(encoding="utf-8"))
        sym = a.get("symbol")
        if (
            a.get("identity") != SOURCE_ID or sym not in MARKETS or sym in result
            or a.get("native_full_RAW_QUALITY_11year_SHA_verified_before_prices") is not True
            or a.get("after_embargo_OHLC_unread") is not True
            or a.get("historical_panel_previously_exposed_not_virgin_OOS") is not True
            or a.get("original_33_source_sha256") != (
                "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
            )
            or a.get("NET_computed") is not False or a.get("UTC001_certified") is not False
            or a.get("orders") != 0 or a.get("production_modified") is not False
            or a.get("original_events") != len(a.get("events", []))
        ):
            raise ValueError("TSMOM_WORKER_SOURCE_PROVENANCE_OR_IDENTITY_INVALID")
        expected = "ORIGINAL12_CIBO_ATLAS" if sym in ORIGINAL12 else "NEW21_ICMARKETS_DEMO"
        if a.get("original_proof", {}).get("source_cohort") != expected:
            raise ValueError("TSMOM_COHORT_SOURCE_IDENTITY_MISMATCH")
        result[sym] = a
    if set(result) != set(MARKETS) or len(ORIGINAL12) != 12:
        raise ValueError("TSMOM_ALL33_ORIGINAL_UNIVERSE_DRIFT")
    return result


def _bootstrap(weeks: list[tuple[float, float]], seed: int) -> dict:
    n = len(weeks)
    if n < FROZEN_BLOCK_WEEKS:
        raise ValueError("TSMOM_TOO_FEW_CALENDAR_WEEKS")
    rand = random.Random(seed)
    strategy, delta = [], []
    for _ in range(BOOTSTRAP_DRAWS):
        positions: list[int] = []
        for _block in range(math.ceil(n / FROZEN_BLOCK_WEEKS)):
            start = rand.randrange(n)
            positions.extend((start + j) % n for j in range(FROZEN_BLOCK_WEEKS))
        positions = positions[:n]
        strategy.append(sum(weeks[i][0] for i in positions) / n)
        delta.append(sum(weeks[i][1] for i in positions) / n)

    def ci(values: list[float]) -> list[float]:
        sorted_values = sorted(values)
        return [sorted_values[int(0.025 * BOOTSTRAP_DRAWS)],
                sorted_values[int(0.975 * BOOTSTRAP_DRAWS) - 1]]

    return {"bootstrap_draws": BOOTSTRAP_DRAWS,
            "block_calendar_weeks": FROZEN_BLOCK_WEEKS,
            "CI95_mean_portfolio_gross_reference_bps_per_week": ci(strategy),
            "CI95_mean_portfolio_paired_delta_gross_reference_bps_per_week": ci(delta)}


def panel(workers: dict[str, dict]) -> dict:
    if set(workers) != set(MARKETS):
        raise ValueError("TSMOM_ALL33_MISSING_WORKER")
    by_era = defaultdict(list)
    by_market = {}
    for sym in MARKETS:
        worker = workers[sym]
        events = worker["events"]
        seq = set()
        for e in events:
            wk, era = e["iso_week"], e["era"]
            if e["symbol"] != sym or era not in MIN_ACTIVE_WEEKS or (era, wk) in seq:
                raise ValueError("TSMOM_EVENT_OR_WEEK_DRIFT")
            seq.add((era, wk))
            if (
                not isinstance(e.get("strategy_gross_reference_bps"), (float, int))
                or not math.isfinite(e["strategy_gross_reference_bps"])
                or not math.isfinite(e["paired_delta_gross_reference_bps"])
                or type(e.get("opposed_control")) is not bool
                or e.get("NET_economic_execution_not_measured") is not True
                or e.get("source_provider_BID_ASK_asof") is not False
            ):
                raise ValueError("TSMOM_EVENT_GROSS_ONLY_CONTRACT_BROKEN")
            by_era[era].append(e)
        by_market[sym] = {
            "cohort": "ATLAS12" if sym in ORIGINAL12 else "NEW21",
            "events": len(events),
            "development_events": sum(e["era"] == "DEVELOPMENT" for e in events),
            "diagnostic_events": sum(e["era"] == "DIAGNOSTIC" for e in events),
            "gross_mean_bps_per_trade": mean(
                e["strategy_gross_reference_bps"] for e in events
            ) if events else None,
        }
    eras = {}
    for j, (era, minimum) in enumerate(MIN_ACTIVE_WEEKS.items()):
        events = by_era[era]
        weeks = era_weeks(era)
        wset = set(weeks)
        sums = defaultdict(lambda: [0.0, 0.0, 0])
        years = defaultdict(lambda: [0.0, 0, 0.0])
        cohorts = defaultdict(list)
        for e in events:
            w = e["iso_week"]
            if w not in wset:
                raise ValueError("TSMOM_EVENT_OUTSIDE_FROZEN_ERA")
            sums[w][0] += e["strategy_gross_reference_bps"] / 33
            sums[w][1] += e["paired_delta_gross_reference_bps"] / 33
            sums[w][2] += 1
            year = int(e["entry_first_native_M5_open_on_utc_day"][:4])
            years[year][0] += e["strategy_gross_reference_bps"]
            years[year][1] += 1
            years[year][2] += e["paired_delta_gross_reference_bps"]
            cohorts["ATLAS12" if e["symbol"] in ORIGINAL12 else "NEW21"].append(e)
        pair = [(sums[w][0], sums[w][1]) for w in weeks]
        bootstrap = _bootstrap(pair, RNG_SEED + j)
        active = sum(sums[w][2] > 0 for w in weeks)
        opposed = sum(e["opposed_control"] for e in events)
        gross = mean(row[0] for row in pair)
        delta = mean(row[1] for row in pair)
        eras[era] = {
            "calendar_weeks_including_flat": len(weeks),
            "active_weeks": active,
            "weekly_events": len(events),
            "opposing_252d_vs_5d_control_count": opposed,
            "opposing_control_fraction": opposed / len(events) if events else 0.0,
            "min_occupied_calendar_weeks": minimum,
            "meets_min_week_gate": active >= minimum,
            "mean_equal_33_weight_weekly_strategy_gross_reference_bps": gross,
            "mean_equal_33_weight_weekly_paired_delta_reference_bps": delta,
            "mean_event_strategy_gross_reference_bps": (
                mean(e["strategy_gross_reference_bps"] for e in events) if events else None
            ),
            "year_descriptive": {
                str(y): {"n_events": n, "mean_gross_reference_bps": total / n,
                         "mean_paired_delta_gross_reference_bps": paired / n}
                for y, (total, n, paired) in sorted(years.items())
            },
            "by_original_source_cohort": {
                cohort: {
                    "n_events": len(cohorts[cohort]),
                    "mean_gross_reference_bps": (
                        mean(e["strategy_gross_reference_bps"] for e in cohorts[cohort])
                        if cohorts[cohort] else None
                    ),
                } for cohort in ("ATLAS12", "NEW21")
            },
            "fixed_hypothetical_cost_stress_not_NET_bps_per_trade": {
                str(c): (
                    mean(e["strategy_gross_reference_bps"] - c for e in events)
                    if events else None
                ) for c in STRESS_BPS
            },
            "synchronized_market_calendar_4week_bootstrap": bootstrap,
        }
    enough = all(e["meets_min_week_gate"] for e in eras.values())
    discriminative = all(e["opposing_control_fraction"] >= 0.2 for e in eras.values())
    positive = all(
        e["mean_equal_33_weight_weekly_strategy_gross_reference_bps"] > 0
        and e["synchronized_market_calendar_4week_bootstrap"][
            "CI95_mean_portfolio_gross_reference_bps_per_week"][0] > 0
        for e in eras.values()
    )
    status = (
        "INCONCLUSIVE_UNDERPOWERED" if not enough else
        "TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL_NONDISCRIMINATIVE_CONTROL"
        if not discriminative else
        "TSMOM_EXPLORATORY_GROSS_SIGNAL_REQUIRES_TRUE_OOS"
        if positive else
        "TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL"
    )
    return {
        "identity": IDENTITY, "status": status, "universe_markets": 33,
        "original12": 12, "new21": 21,
        "historical_2016_2024_panel_was_previously_exposed": True,
        "no_independent_OOS_claim": True,
        "strategy_params_tuned_after_outcome": False,
        "original_daily_M5_source_SHA_verified_all33": True,
        "all33_zero_event_symbols_retained": True,
        "per_market": by_market,
        "eras": eras,
        "gross_is_reference_only_from_native_M5_open_close": True,
        "capital_portfolio_broker_contract_comparable": False,
        "real_broker_costs_or_BIDASK_proven": False,
        "broker_NET_PF_Sharpe_DD_computed": False,
        "UTC001_certified": False, "orders": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("workers", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--head", required=True)
    args = p.parse_args()
    data = panel(load_all33(args.workers, args.head))
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "alpha2-tsmom-33-weekly-gross-exploratory-panel.json"
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": data["status"],
        "markets": data["universe_markets"],
        "dev_events": data["eras"]["DEVELOPMENT"]["weekly_events"],
        "diag_events": data["eras"]["DIAGNOSTIC"]["weekly_events"],
        "DEV_weekly_gross_bps": data["eras"]["DEVELOPMENT"][
            "mean_equal_33_weight_weekly_strategy_gross_reference_bps"
        ],
        "DIAG_weekly_gross_bps": data["eras"]["DIAGNOSTIC"][
            "mean_equal_33_weight_weekly_strategy_gross_reference_bps"
        ],
        "NET": "NOT_COMPUTED", "UTC001": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
