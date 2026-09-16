"""Consumed-only VT-31 multi-index behavior observatory.

This module studies the definitive tick-corrected VT-31 population across
NAS100, SP500 and US30. It is intentionally descriptive: outcomes may be used as
labels for diagnostics, but never as features for regime construction or as an
automatic candidate selector.

Inputs are immutable consumed artifacts only. No fresh holdout is opened.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable

FRICTION = Decimal("0.10")
MARKETS = ("NAS100", "SP500", "US30")
SIDES = ("long", "short")
REGIME_K = 6
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_BLOCK = 5
BOOTSTRAP_SEED = 20260916


def D(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | float | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return format(value, ".12f")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def q(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = p * Decimal(len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - Decimal(lo)
    return xs[lo] * (Decimal(1) - frac) + xs[hi] * frac


def stressed(row: dict[str, Any]) -> Decimal:
    return D(row["terminal_r"]) - FRICTION


def _max_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _max_losing_streak(values: list[Decimal]) -> int:
    best = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda r: (r["signal_at"], r["market"], r["root_id"]))
    vals = [stressed(row) for row in ordered]
    n = len(vals)
    if n == 0:
        return {"n": 0}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    total = sum(vals, Decimal(0))
    gross_win = sum(wins, Decimal(0))
    gross_loss = abs(sum(losses, Decimal(0)))
    pf = gross_win / gross_loss if gross_loss else None
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": fmt(Decimal(len(wins)) / Decimal(n)),
        "total_stressed_r": fmt(total),
        "mean_stressed_r": fmt(total / Decimal(n)),
        "median_stressed_r": fmt(q(vals, Decimal("0.5"))),
        "p10_stressed_r": fmt(q(vals, Decimal("0.10"))),
        "p90_stressed_r": fmt(q(vals, Decimal("0.90"))),
        "profit_factor_stressed": fmt(pf),
        "max_drawdown_stressed_r": fmt(_max_drawdown(vals)),
        "max_losing_streak": _max_losing_streak(vals),
        "terminal_status_counts": dict(sorted(Counter(str(r["terminal_status"]) for r in rows).items())),
    }


def bucket(value: Decimal, edges: tuple[Decimal, ...]) -> str:
    prior: Decimal | None = None
    for edge in edges:
        if value <= edge:
            return f"<= {edge}" if prior is None else f"({prior}, {edge}]"
        prior = edge
    return f"> {edges[-1]}"


def half_year(ts: str) -> str:
    d = parse_ts(ts)
    return f"{d.year}-H{1 if d.month <= 6 else 2}"


def quarter(ts: str) -> str:
    d = parse_ts(ts)
    return f"{d.year}-Q{((d.month - 1) // 3) + 1}"


def weekday(ts: str) -> str:
    return parse_ts(ts).strftime("%A")


def group_metrics(rows: list[dict[str, Any]], key: Callable[[dict[str, Any]], str]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return {name: metrics(group) for name, group in sorted(groups.items())}


def period_stability(rows: list[dict[str, Any]], period_fn: Callable[[str], str]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[period_fn(str(row["signal_at"]))].append(row)
    periods = {name: metrics(group) for name, group in sorted(grouped.items())}
    eligible = [m for m in periods.values() if int(m.get("n", 0)) >= 10]
    positive = sum(D(m["mean_stressed_r"]) > 0 for m in eligible)
    return {
        "periods": periods,
        "eligible_period_count_n_ge_10": len(eligible),
        "positive_period_count": positive,
        "positive_period_fraction": fmt(Decimal(positive) / Decimal(len(eligible))) if eligible else None,
    }


def _moving_block_bootstrap(values: list[Decimal], draws: int, block: int, seed: int) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    rng = random.Random(seed)
    n = len(values)
    block = max(1, min(block, n))
    starts = list(range(0, n - block + 1))
    means: list[Decimal] = []
    for _ in range(draws):
        sample: list[Decimal] = []
        while len(sample) < n:
            start = rng.choice(starts)
            sample.extend(values[start : start + block])
        sample = sample[:n]
        means.append(sum(sample, Decimal(0)) / Decimal(n))
    return {
        "n": n,
        "draws": draws,
        "block": block,
        "mean_p05": fmt(q(means, Decimal("0.05"))),
        "mean_p50": fmt(q(means, Decimal("0.50"))),
        "mean_p95": fmt(q(means, Decimal("0.95"))),
        "positive_mean_fraction": fmt(Decimal(sum(v > 0 for v in means)) / Decimal(draws)),
    }


def bootstrap_section(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    groups: dict[str, list[dict[str, Any]]] = {f"market:{m}": [r for r in rows if r["market"] == m] for m in MARKETS}
    for market in MARKETS:
        for side in SIDES:
            groups[f"market_side:{market}:{side}"] = [r for r in rows if r["market"] == market and r["side"] == side]
    for i, (name, group) in enumerate(sorted(groups.items())):
        vals = [stressed(r) for r in sorted(group, key=lambda r: (r["signal_at"], r["root_id"]))]
        result[name] = _moving_block_bootstrap(vals, BOOTSTRAP_DRAWS, BOOTSTRAP_BLOCK, BOOTSTRAP_SEED + i)
    return result


def pearson(xs: list[Decimal], ys: list[Decimal]) -> Decimal | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = sum(xs, Decimal(0)) / Decimal(len(xs))
    my = sum(ys, Decimal(0)) / Decimal(len(ys))
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum((a * b for a, b in zip(dx, dy)), Decimal(0))
    denx = sum((a * a for a in dx), Decimal(0))
    deny = sum((b * b for b in dy), Decimal(0))
    if denx <= 0 or deny <= 0:
        return None
    return num / (denx.sqrt() * deny.sqrt())


def cross_index_section(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_day[str(row["ny_date"])].append(row)
    cohorts: list[dict[str, Any]] = []
    for day, day_rows in sorted(by_day.items()):
        markets = sorted({str(r["market"]) for r in day_rows})
        sides = sorted({str(r["side"]) for r in day_rows})
        vals = [stressed(r) for r in day_rows]
        cohorts.append({
            "ny_date": day,
            "active_market_count": len(markets),
            "markets": markets,
            "side_state": sides[0] if len(sides) == 1 else "mixed",
            "all_positive": all(v > 0 for v in vals),
            "all_negative": all(v < 0 for v in vals),
            "mean_stressed_r": fmt(sum(vals, Decimal(0)) / Decimal(len(vals))),
            "sum_stressed_r": fmt(sum(vals, Decimal(0))),
        })
    breadth: dict[str, list[dict[str, Any]]] = defaultdict(list)
    consensus: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for day, day_rows in by_day.items():
        breadth[str(len({r["market"] for r in day_rows}))].extend(day_rows)
        side_state = str(day_rows[0]["side"]) if len({r["side"] for r in day_rows}) == 1 else "mixed"
        consensus[side_state].extend(day_rows)
    pairwise: dict[str, Any] = {}
    market_by_day: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        market_by_day[str(row["ny_date"])][str(row["market"])] = row
    for left, right in combinations(MARKETS, 2):
        xs: list[Decimal] = []
        ys: list[Decimal] = []
        side_agree = 0
        paired = 0
        for day in sorted(market_by_day):
            item = market_by_day[day]
            if left not in item or right not in item:
                continue
            paired += 1
            xs.append(stressed(item[left]))
            ys.append(stressed(item[right]))
            if item[left]["side"] == item[right]["side"]:
                side_agree += 1
        pairwise[f"{left}__{right}"] = {
            "paired_days": paired,
            "stressed_r_correlation": fmt(pearson(xs, ys)),
            "side_agreement_fraction": fmt(Decimal(side_agree) / Decimal(paired)) if paired else None,
        }
    return {
        "day_cohort_count": len(cohorts),
        "breadth_metrics": {k: metrics(v) for k, v in sorted(breadth.items())},
        "side_consensus_metrics": {k: metrics(v) for k, v in sorted(consensus.items())},
        "pairwise_same_day": pairwise,
        "cohorts": cohorts,
    }


def coverage_section(ledger: dict[str, Any]) -> dict[str, Any]:
    roots = ledger.get("roots")
    if not isinstance(roots, list) or len(roots) != 780:
        raise ValueError("definitive ledger must contain exactly 780 roots")
    dimensions: dict[str, dict[str, Counter[str]]] = {
        "market": defaultdict(Counter),
        "side": defaultdict(Counter),
        "partition": defaultdict(Counter),
    }
    for row in roots:
        classification = str(row["classification"])
        for dim in dimensions:
            dimensions[dim][str(row[dim])][classification] += 1
    rendered: dict[str, Any] = {}
    for dim, groups in dimensions.items():
        rendered[dim] = {}
        for key, counts in sorted(groups.items()):
            total = sum(counts.values())
            terminal = counts.get("terminal", 0)
            rendered[dim][key] = {
                "root_count": total,
                "terminal": terminal,
                "no_trade": counts.get("no_trade", 0),
                "censored": counts.get("censored", 0),
                "terminalization_fraction": fmt(Decimal(terminal) / Decimal(total)) if total else None,
            }
    counts = Counter(str(row["classification"]) for row in roots)
    return {"root_count": len(roots), "class_counts": dict(sorted(counts.items())), "by_dimension": rendered}


def failure_family(status: str) -> str:
    s = status.lower()
    if "target" in s:
        return "target"
    if "initial-stop" in s:
        return "initial_stop"
    if "protected-stop" in s:
        return "protected_stop"
    return "other"


def failure_section(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for market in MARKETS:
        market_rows = [r for r in rows if r["market"] == market]
        groups[market] = {
            "all": dict(sorted(Counter(failure_family(str(r["terminal_status"])) for r in market_rows).items())),
            "long": dict(sorted(Counter(failure_family(str(r["terminal_status"])) for r in market_rows if r["side"] == "long").items())),
            "short": dict(sorted(Counter(failure_family(str(r["terminal_status"])) for r in market_rows if r["side"] == "short").items())),
        }
    return {
        "overall": dict(sorted(Counter(failure_family(str(r["terminal_status"])) for r in rows).items())),
        "by_market": groups,
    }


REGIME_FEATURES = (
    "signal_minute",
    "risk_to_reference",
    "raid_body_fraction",
    "confirmation_body_fraction",
    "raid_depth_to_reference",
    "final_extreme_depth_to_reference",
    "raid_to_final_extreme_latency_m1",
    "raid_to_confirmation_latency_m1",
    "displacement_beyond_anchor_to_reference",
    "entry_location_to_reference",
    "protected_swing_opposing_series_length",
    "opposing_liquidity_r",
)


def _raw_feature(row: dict[str, Any], name: str) -> Decimal:
    return D(row[name])


def _robust_matrix(rows: list[dict[str, Any]]) -> tuple[list[list[float]], dict[str, Any]]:
    columns: dict[str, list[Decimal]] = {name: [_raw_feature(r, name) for r in rows] for name in REGIME_FEATURES}
    scale: dict[str, Any] = {}
    medians: dict[str, Decimal] = {}
    widths: dict[str, Decimal] = {}
    for name, values in columns.items():
        med = q(values, Decimal("0.5")) or Decimal(0)
        q25 = q(values, Decimal("0.25")) or med
        q75 = q(values, Decimal("0.75")) or med
        width = q75 - q25
        if width == 0:
            width = max(values) - min(values)
        if width == 0:
            width = Decimal(1)
        medians[name] = med
        widths[name] = width
        scale[name] = {"median": fmt(med), "iqr_or_range": fmt(width)}
    matrix: list[list[float]] = []
    for row in rows:
        vector = []
        for name in REGIME_FEATURES:
            z = (_raw_feature(row, name) - medians[name]) / widths[name]
            z = max(Decimal(-5), min(Decimal(5), z))
            vector.append(float(z))
        matrix.append(vector)
    return matrix, scale


def _dist2(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _kmeans(matrix: list[list[float]], k: int) -> tuple[list[int], list[list[float]]]:
    if not matrix:
        return [], []
    k = max(1, min(k, len(matrix)))
    norms = [sum(v * v for v in row) for row in matrix]
    first = min(range(len(matrix)), key=lambda i: (norms[i], i))
    centroids = [list(matrix[first])]
    chosen = {first}
    while len(centroids) < k:
        candidate = max(
            (i for i in range(len(matrix)) if i not in chosen),
            key=lambda i: (min(_dist2(matrix[i], c) for c in centroids), -i),
        )
        chosen.add(candidate)
        centroids.append(list(matrix[candidate]))
    assignments = [-1] * len(matrix)
    for _ in range(60):
        updated = [min(range(k), key=lambda j: (_dist2(row, centroids[j]), j)) for row in matrix]
        if updated == assignments:
            break
        assignments = updated
        next_centroids: list[list[float]] = []
        for cluster in range(k):
            members = [matrix[i] for i, value in enumerate(assignments) if value == cluster]
            if not members:
                next_centroids.append(list(centroids[cluster]))
                continue
            next_centroids.append([sum(member[j] for member in members) / len(members) for j in range(len(matrix[0]))])
        centroids = next_centroids
    return assignments, centroids


def regime_section(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix, scaling = _robust_matrix(rows)
    assignments, centroids = _kmeans(matrix, REGIME_K)
    clusters: dict[str, Any] = {}
    for cluster in range(len(centroids)):
        members = [rows[i] for i, assigned in enumerate(assignments) if assigned == cluster]
        profile: dict[str, Any] = {}
        for feature in REGIME_FEATURES:
            values = [_raw_feature(r, feature) for r in members]
            profile[feature] = {
                "median": fmt(q(values, Decimal("0.50"))),
                "p25": fmt(q(values, Decimal("0.25"))),
                "p75": fmt(q(values, Decimal("0.75"))),
            }
        clusters[f"regime_{cluster}"] = {
            "n": len(members),
            "market_counts": dict(sorted(Counter(str(r["market"]) for r in members).items())),
            "side_counts": dict(sorted(Counter(str(r["side"]) for r in members).items())),
            "entry_family_counts": dict(sorted(Counter(str(r["entry_family"]) for r in members).items())),
            "outcome_metrics_label_only": metrics(members),
            "half_year_stability_label_only": period_stability(members, half_year),
            "feature_profile_pre_entry_only": profile,
        }
    row_regimes = [
        {
            "root_id": rows[i]["root_id"],
            "market": rows[i]["market"],
            "ny_date": rows[i]["ny_date"],
            "side": rows[i]["side"],
            "regime": f"regime_{assignments[i]}",
            "distance_to_centroid": fmt(math.sqrt(_dist2(matrix[i], centroids[assignments[i]]))),
            "terminal_r": rows[i]["terminal_r"],
        }
        for i in range(len(rows))
    ]
    return {
        "method": "deterministic robust-scaled kmeans; outcomes excluded from clustering",
        "k": len(centroids),
        "features": list(REGIME_FEATURES),
        "scaling": scaling,
        "clusters": clusters,
        "rows": row_regimes,
    }


def interaction_section(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "market_x_side": group_metrics(rows, lambda r: f"{r['market']}|{r['side']}"),
        "market_x_entry_family": group_metrics(rows, lambda r: f"{r['market']}|{r['entry_family']}"),
        "market_x_signal_5m": group_metrics(rows, lambda r: f"{r['market']}|{bucket(D(r['signal_minute']), (Decimal(5), Decimal(10), Decimal(15), Decimal(20)))}"),
        "market_x_risk_reference": group_metrics(rows, lambda r: f"{r['market']}|{bucket(D(r['risk_to_reference']), (Decimal('0.10'), Decimal('0.125'), Decimal('0.15'), Decimal('0.175')))}"),
        "market_x_protected_swing": group_metrics(rows, lambda r: f"{r['market']}|{r['protected_swing_like_at_signal']}"),
        "market_x_prior_day_alignment": group_metrics(rows, lambda r: f"{r['market']}|{r['side_aligned_with_prior_day']}"),
        "market_x_terminal_family": group_metrics(rows, lambda r: f"{r['market']}|{failure_family(str(r['terminal_status']))}"),
    }


def feature_distributions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = (
        "risk_to_reference", "raid_body_fraction", "confirmation_body_fraction",
        "raid_depth_to_reference", "final_extreme_depth_to_reference",
        "displacement_beyond_anchor_to_reference", "entry_location_to_reference",
        "opposing_liquidity_r", "signal_minute",
    )
    result: dict[str, Any] = {}
    for market in MARKETS:
        market_rows = [r for r in rows if r["market"] == market]
        result[market] = {}
        for name in names:
            values = [D(r[name]) for r in market_rows]
            result[market][name] = {
                "p10": fmt(q(values, Decimal("0.10"))),
                "p25": fmt(q(values, Decimal("0.25"))),
                "median": fmt(q(values, Decimal("0.50"))),
                "p75": fmt(q(values, Decimal("0.75"))),
                "p90": fmt(q(values, Decimal("0.90"))),
            }
    return result


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "root_id", "partition", "market", "ny_date", "signal_at", "side", "entry_family",
        "terminal_r", "terminal_status", "resolution_source", "signal_minute",
        "risk_to_reference", "raid_body_fraction", "confirmation_body_fraction",
        "raid_depth_to_reference", "final_extreme_depth_to_reference",
        "raid_to_final_extreme_latency_m1", "raid_to_confirmation_latency_m1",
        "displacement_beyond_anchor_to_reference", "entry_location_to_reference",
        "protected_swing_like_at_signal", "protected_swing_opposing_series_length",
        "side_aligned_with_prior_day", "opposing_liquidity_r",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["signal_at"], r["market"], r["root_id"])):
            writer.writerow(row)


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# VT-31 Multi-Index Behavior Observatory",
        "",
        "Consumed-only descriptive research. No candidate is selected and no fresh holdout is opened.",
        "",
        f"Definitive terminal trades: **{payload['terminal_count']}** / roots: **{payload['coverage']['root_count']}**.",
        "",
        "## Market behavior",
        "",
        "| Market | n | Mean stressed R | PF | Max DD R | Losing streak |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for market in MARKETS:
        m = payload["market_metrics"][market]
        lines.append(f"| {market} | {m['n']} | {m['mean_stressed_r']} | {m['profit_factor_stressed']} | {m['max_drawdown_stressed_r']} | {m['max_losing_streak']} |")
    lines.extend([
        "",
        "## Governance",
        "",
        "- Regimes are built only from pre-entry features; terminal outcome is attached afterwards as a diagnostic label.",
        "- All buckets/interactions are descriptive and cannot be promoted automatically into R9 rules.",
        "- Fresh evidence remains sealed.",
        "- LIVE/PRODUCTION authorization is not granted by this report.",
        "",
        "## Outputs",
        "",
        "The JSON artifact contains market/side interactions, temporal stability, block-bootstrap uncertainty, cross-index cohorts, censoring coverage, terminal failure composition, feature distributions and six deterministic unsupervised pre-entry regimes.",
    ])
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deep-forensics", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    deep = json.loads(args.deep_forensics.read_text())
    ledger = json.loads(args.ledger.read_text())
    for name, payload in (("deep", deep), ("ledger", ledger)):
        if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
            raise ValueError(f"{name} governance guard failed")
    if deep.get("selection_prohibited") is not True or deep.get("feature_timing") != "pre-entry-only":
        raise ValueError("deep forensics selection guard failed")
    rows = deep.get("rows")
    if not isinstance(rows, list) or len(rows) != deep.get("terminal_count"):
        raise ValueError("deep forensics terminal rows malformed")
    if len(rows) != ledger.get("terminal_trade_count"):
        raise ValueError("ledger/deep terminal count mismatch")
    if len({r["root_id"] for r in rows}) != len(rows):
        raise ValueError("terminal root identities are not unique")
    if tuple(sorted({str(r["market"]) for r in rows})) != tuple(sorted(MARKETS)):
        raise ValueError("unexpected market universe")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    market_metrics = group_metrics(rows, lambda r: str(r["market"]))
    payload = {
        "schema": "qore.vt31.multi_index_behavior_observatory.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "selection_prohibited": True,
        "live_authorized": False,
        "production_authorized": False,
        "friction_r": str(FRICTION),
        "terminal_count": len(rows),
        "market_universe": list(MARKETS),
        "coverage": coverage_section(ledger),
        "aggregate": metrics(rows),
        "market_metrics": market_metrics,
        "side_metrics": group_metrics(rows, lambda r: str(r["side"])),
        "partition_metrics": group_metrics(rows, lambda r: str(r["partition"])),
        "entry_family_metrics": group_metrics(rows, lambda r: str(r["entry_family"])),
        "weekday_metrics": group_metrics(rows, lambda r: weekday(str(r["signal_at"]))),
        "signal_5m_metrics": group_metrics(rows, lambda r: bucket(D(r["signal_minute"]), (Decimal(5), Decimal(10), Decimal(15), Decimal(20)))),
        "interactions": interaction_section(rows),
        "failure_modes": failure_section(rows),
        "feature_distributions_by_market": feature_distributions(rows),
        "temporal": {
            "overall_half_year": period_stability(rows, half_year),
            "overall_quarter": period_stability(rows, quarter),
            "market_half_year": {m: period_stability([r for r in rows if r["market"] == m], half_year) for m in MARKETS},
            "market_quarter": {m: period_stability([r for r in rows if r["market"] == m], quarter) for m in MARKETS},
        },
        "block_bootstrap_uncertainty": bootstrap_section(rows),
        "cross_index": cross_index_section(rows),
        "unsupervised_pre_entry_regimes": regime_section(rows),
        "interpretation_constraints": [
            "terminal outcome is a diagnostic label and is excluded from unsupervised regime construction",
            "all buckets and interactions are descriptive; they do not select R9 rules",
            "no fresh evidence is opened or inspected",
            "market differences must be validated by future predeclared leakage-free walk-forward before promotion",
        ],
    }

    json_path = args.output_dir / "vt31-behavior-observatory.json"
    csv_path = args.output_dir / "vt31-behavior-trade-matrix.csv"
    md_path = args.output_dir / "vt31-behavior-dossier.md"
    json_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    write_csv(rows, csv_path)
    write_markdown(payload, md_path)
    print(json.dumps({
        "terminal_count": len(rows),
        "markets": market_metrics,
        "coverage": payload["coverage"]["class_counts"],
        "regime_count": payload["unsupervised_pre_entry_regimes"]["k"],
        "cross_index_days": payload["cross_index"]["day_cohort_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
