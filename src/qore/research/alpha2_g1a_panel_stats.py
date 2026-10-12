"""Alpha2 paired gross panel: week-block uncertainty; NOT a net Trader verdict."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean

import numpy as np

from qore.research.alpha2_g1a_native_m5_gross import IDENTITY as SOURCE_ID
from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_signal_census import SOURCE_SHA

IDENTITY = "QORE_ALPHA2_G1A_PAIRED_GROSS_PANEL_FIRST_OUTCOME_V1"
B = 4000
SEED = 20261012
RT_ASSUMPTIONS_BPS = (0, 1, 3, 5, 10, 20)
ERAS = {
    "DEVELOPMENT": (date(2016, 9, 17), date(2022, 9, 17), 150, 52),
    "DIAGNOSTIC": (date(2022, 9, 17), date(2024, 9, 17), 50, 26),
}


def load_source(root: Path, *, expected_head: str) -> dict[str, list[dict]]:
    paths = sorted(root.rglob("alpha2-g1a-gross-*.json"))
    if len(paths) != 33:
        raise ValueError("exactly 33 original-source replay workers required")
    found: dict[str, list[dict]] = {}
    for path in paths:
        expected = {path.name: sha256_file(path)}
        side = path.with_name(path.name + ".sha256")
        if side.read_text(encoding="utf-8").strip() != (
            f"{expected[path.name]}  {path.name}"
        ):
            raise ValueError("worker G1A JSON SHA witness invalid")
        head = (path.parent / "exact-code-head-sha.txt").read_text(encoding="utf-8").strip()
        if head != expected_head:
            raise ValueError("worker G1A source HEAD changed across symbols")
        o = json.loads(path.read_text(encoding="utf-8"))
        sym = o.get("symbol")
        if (o.get("identity") != SOURCE_ID or sym not in MARKETS or sym in found
                or o.get("signals_exact_immutable_sha256") != SOURCE_SHA
                or o.get("net_certified") is not False
                or o.get("2024_09_17_plus_prices_not_read") is not True
                or o.get("production_untouched") is not True
                or o.get("total_original_signals") != len(o.get("events", []))):
            raise ValueError("symbol identity/provenance/raw source drift")
        found[sym] = o["events"]
    if set(found) != set(MARKETS) or sum(map(len, found.values())) != 224:
        raise ValueError("224 original signals must be accounted for in all 33")
    return found


def _iso_week(when: date) -> str:
    week = when.isocalendar()
    return f"{week.year}-W{week.week:02d}"


def _full_weeks(start: date, end: date) -> list[str]:
    monday = start - timedelta(days=start.weekday())
    weeks: list[str] = []
    while monday < end:
        weeks.append(_iso_week(monday))
        monday += timedelta(days=7)
    return weeks


def block_bootstrap(
    events: list[dict], *, era: str, length: int, draws: int = B,
) -> dict:
    if era not in ERAS or length not in (1, 2, 4):
        raise ValueError("frozen era / 1,2,4-week blocks required")
    start, end, _, _ = ERAS[era]
    labels = _full_weeks(start, end)
    n = len(labels)
    by_week: dict[str, tuple[float, int]] = {}
    grouped: dict[str, list[float]] = defaultdict(list)
    for event in events:
        if event["paired_observed"]:
            grouped[event["iso_week"]].append(event["paired_delta_gross_bps"])
    for week in labels:
        xs = grouped.get(week, [])
        by_week[week] = (sum(xs), len(xs))
    if set(grouped) - set(labels):
        raise ValueError("event's decision week not within frozen era")
    sum_data = np.array([by_week[w][0] for w in labels], dtype=np.float64)
    count_data = np.array([by_week[w][1] for w in labels], dtype=np.int32)
    eligible = int(np.sum(count_data))
    observed = float(np.sum(sum_data) / eligible) if eligible else None
    if not eligible:
        return {"block_weeks": length, "draws": draws,
                "mean_delta_bps": None, "ci95_bps": None,
                "p_centered_two_sided": 1.0, "zero_denominator_draws": draws,
                "week_clusters": n, "weeks_with_events": 0}
    rng = np.random.default_rng(SEED + length + (0 if era == "DEVELOPMENT" else 100))
    results = np.empty(draws, dtype=np.float64)
    zeros = 0
    for b in range(draws):
        starts = rng.integers(0, n, size=math.ceil(n / length))
        positions = np.concatenate(
            [np.arange(s, s + length, dtype=np.int32) % n for s in starts]
        )[:n]
        denom = int(count_data[positions].sum())
        if denom == 0:
            results[b] = np.nan
            zeros += 1
        else:
            results[b] = float(sum_data[positions].sum() / denom)
    valid = results[np.isfinite(results)]
    # Do not manufacture significance from degenerate block distribution.
    if len(valid) < B // 2 or np.std(valid) <= 1e-15:
        p = 1.0
        ci = None
    else:
        ci = [float(np.quantile(valid, 0.025)), float(np.quantile(valid, 0.975))]
        centered = valid - observed
        p = float((np.count_nonzero(np.abs(centered) >= abs(observed)) + 1)
                  / (len(valid) + 1))
    return {
        "block_weeks": length, "draws": draws, "bootstrap_seed": SEED + length
        + (0 if era == "DEVELOPMENT" else 100),
        "mean_delta_bps": observed, "ci95_bps": ci,
        "p_centered_two_sided": p, "zero_denominator_draws": zeros,
        "week_clusters": n, "weeks_with_events": int(np.count_nonzero(count_data)),
    }


def _mean_or_none(a: list[float]) -> float | None:
    return float(mean(a)) if a else None


def _gross_pf(rs: list[float]) -> float | None:
    gains = sum(x for x in rs if x > 0)
    losses = -sum(x for x in rs if x < 0)
    return float(gains / losses) if losses > 0 else None


def aggregate(root: Path, *, exact_head: str) -> dict:
    per_symbol = load_source(root, expected_head=exact_head)
    events = [x for sym in sorted(per_symbol) for x in per_symbol[sym]]
    eras: dict[str, dict] = {}
    diagnostics = {}
    for sym in sorted(MARKETS):
        a = per_symbol[sym]
        selected = [x for x in a if x["paired_observed"]]
        diagnostics[sym] = {
            "signals": len(a), "paired": len(selected),
            "strategy_gross_mean_bps_proxy": _mean_or_none(
                [x["strategy"]["gross_bps"] for x in selected]),
            "paired_delta_mean_bps_proxy": _mean_or_none(
                [x["paired_delta_gross_bps"] for x in selected]),
            "not_a_symbol_edge_certification": True,
        }
    for era, (start, end, min_trades, min_weeks) in ERAS.items():
        whole = [e for e in events if e["era"] == era]
        paired = [e for e in whole if e["paired_observed"]]
        weeks = len({e["iso_week"] for e in paired})
        a = [x["strategy"]["gross_bps"] for x in paired]
        ctrl = [x["baseline"]["gross_bps"] for x in paired]
        delta = [x["paired_delta_gross_bps"] for x in paired]
        rvals = [x["strategy"]["gross_R"] for x in paired]
        by_year: dict[str, dict] = {}
        for year in range(start.year, end.year + 1):
            year_events = [e for e in paired if datetime.fromisoformat(
                e["decision_utc"]).year == year]
            by_year[str(year)] = {
                "paired_events": len(year_events),
                "gross_strategy_mean_bps_proxy": _mean_or_none(
                    [e["strategy"]["gross_bps"] for e in year_events]),
                "gross_delta_mean_bps_proxy": _mean_or_none(
                    [e["paired_delta_gross_bps"] for e in year_events]),
                "gross_pf_proxy_not_UTC001": _gross_pf(
                    [e["strategy"]["gross_R"] for e in year_events]),
            }
        boots = {
            f"{L}wk": block_bootstrap(whole, era=era, length=L)
            for L in (1, 2, 4)
        }
        sample_gate = len(paired) >= min_trades and weeks >= min_weeks
        eras[era] = {
            "original_signals": len(whole), "evaluable_paired_events": len(paired),
            "censored_or_unpaired_events": len(whole) - len(paired),
            "weeks_with_evaluable_events": weeks,
            "sample_gate_predeclared": sample_gate,
            "sample_min_trades": min_trades, "sample_min_weeks": min_weeks,
            "gross_mean_bps_proxy": _mean_or_none(a),
            "control_gross_mean_bps_proxy": _mean_or_none(ctrl),
            "paired_delta_mean_bps_proxy": _mean_or_none(delta),
            "gross_mean_R_proxy": _mean_or_none(rvals),
            "gross_PF_proxy_not_UTC001": _gross_pf(rvals),
            "drawdown_is_not_certification": True,
            "hypothetical_gross_minus_RT_cost_bps_NOT_NET": {
                str(v): (_mean_or_none(a) - v if a else None)
                for v in RT_ASSUMPTIONS_BPS
            },
            "bootstrap_calendar_synced_all_markets": boots,
            "year_descriptive": by_year,
            "reason_count": dict(Counter(
                f"{e['strategy']['status']}|{e['baseline']['status']}"
                for e in whole if not e["paired_observed"]
            )),
        }
    supported = all(
        eras[era]["sample_gate_predeclared"]
        and eras[era]["gross_mean_bps_proxy"] is not None
        and eras[era]["gross_mean_bps_proxy"] > 0
        and eras[era]["paired_delta_mean_bps_proxy"] is not None
        and eras[era]["paired_delta_mean_bps_proxy"] > 0
        and all(
            eras[era]["bootstrap_calendar_synced_all_markets"][f"{l}wk"]["ci95_bps"]
            is not None and
            eras[era]["bootstrap_calendar_synced_all_markets"][f"{l}wk"]["ci95_bps"][0] > 0
            for l in (1, 2, 4)
        )
        for era in ERAS
    )
    verdict = ("GROSS_CANDIDATE_REQUIRES_BIDASK_AND_REAL_OOS" if supported
               else "UNDERPOWERED" if any(not eras[e]["sample_gate_predeclared"]
                                         for e in ERAS)
               else "NO_SUPPORT_FOR_PREDECLARED_GROSS_GATE")
    return {
        "identity": IDENTITY, "research_verdict": verdict,
        "source_head": exact_head, "source_signal_sha256": SOURCE_SHA,
        "markets": 33, "original_signals": len(events),
        "total_paired_gross_events": sum(e["evaluable_paired_events"]
                                         for e in eras.values()),
        "eras": eras, "by_symbol": diagnostics,
        "all_original_markets_reported_even_if_zero": True,
        "gross_reference_not_bidask_or_fills": True,
        "macro_news_PIT_unverified": True,
        "all_broker_costs_unknown": True,
        "net_pf_sharpe_sortino_dd_not_computed": True,
        "utc001_certified": False, "production_untouched": True,
        "2024_09_17_onward_prices_not_read": True,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("sources33", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--source-head", required=True)
    x = p.parse_args()
    r = aggregate(x.sources33, exact_head=x.source_head)
    x.dest.mkdir(parents=True, exist_ok=True)
    outfile = x.dest / "alpha2-g1a-paired-33-first-gross-panel.json"
    outfile.write_text(json.dumps(r, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": r["research_verdict"], "signals": r["original_signals"],
        "paired": r["total_paired_gross_events"],
        "eras": {e: {"paired": v["evaluable_paired_events"],
                     "gross": v["gross_mean_bps_proxy"],
                     "delta": v["paired_delta_mean_bps_proxy"],
                     "sample_gate": v["sample_gate_predeclared"]}
                 for e, v in r["eras"].items()},
        "no_NET_or_LIVE": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
