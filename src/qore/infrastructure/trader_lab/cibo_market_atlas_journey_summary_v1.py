"""CIBO Market Atlas Journey Layer V1 statistical summary.

Research-only summarizer for already-consumed Journey artifacts. It produces
regenerable descriptive statistics without promoting trader rules or changing
any execution authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from statistics import median
from typing import Any

IDENTITY = "CIBO_MARKET_JOURNEY_SUMMARY_V1"
SOURCE_IDENTITY = "CIBO_MARKET_JOURNEY_LAYER_V1"
SOURCE_RUN_ID = 35175979474
SOURCE_GIT_SHA = "9cc0f17a2f30846d61b242132547f39391909656"
SCHEMA = "qore.cibo_market_atlas.journey_summary.v1"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _quantile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _distribution(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _rate(values: Sequence[bool]) -> float | None:
    return None if not values else sum(values) / len(values)


def _latency_summary(values: Sequence[int | float]) -> dict[str, float | int | None]:
    numeric = [float(value) for value in values]
    return {
        "n": len(numeric),
        "p25": _quantile(numeric, 0.25),
        "median": None if not numeric else median(numeric),
        "p75": _quantile(numeric, 0.75),
        "p90": _quantile(numeric, 0.90),
    }


def _symbol_summary(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    journeys = _read_jsonl(root / "MARKET_JOURNEY_LEDGER.jsonl")
    timing = _read_jsonl(root / "DEPARTURE_TIMING_LEDGER.jsonl")
    targets = _read_jsonl(root / "TARGET_DESTINATION_LEDGER.jsonl")
    daily = _read_jsonl(root / "DAILY_PATH_LEDGER.jsonl")

    resolved = [row for row in journeys if row.get("departure_at") is not None]
    unresolved = len(journeys) - len(resolved)
    source_to_departure = [
        int(row["minutes_source_event_to_departure"])
        for row in timing
        if row.get("minutes_source_event_to_departure") is not None
    ]
    reclaim_latency = [
        int(row["reclaim_latency_minutes"])
        for row in timing
        if row.get("reclaim_latency_minutes") is not None
    ]
    target_hits = [bool(row.get("first_objective_touched_24h")) for row in targets]
    target_minutes = [
        int(row["time_to_first_objective_minutes"])
        for row in targets
        if row.get("time_to_first_objective_minutes") is not None
    ]
    daily_efficiency = [
        float(row["path_efficiency"])
        for row in daily
        if row.get("path_efficiency") is not None
    ]
    daily_overlap = [
        float(row["overlap_fraction"])
        for row in daily
        if row.get("overlap_fraction") is not None
    ]

    return {
        "symbol": manifest["symbol"],
        "provider_symbol": manifest["provider_symbol"],
        "retained_m5_bars": int(manifest["retained_m5_bars"]),
        "episodes": len(journeys),
        "resolved_departures": len(resolved),
        "unresolved_departures": unresolved,
        "resolved_departure_rate": None if not journeys else len(resolved) / len(journeys),
        "source_boundary_types": _distribution(
            str(row["source_boundary_type"]) for row in journeys
        ),
        "last_pre_departure_structures": _distribution(
            str(row["last_structure_before_departure"]) for row in journeys
        ),
        "source_timeframes": _distribution(str(row["source_timeframe"]) for row in journeys),
        "sides": _distribution(str(row["side"]) for row in journeys),
        "sessions": _distribution(str(row["session_bucket"]) for row in journeys),
        "weekdays": _distribution(str(row["weekday"]) for row in timing),
        "source_event_to_departure_minutes": _latency_summary(source_to_departure),
        "reclaim_latency_minutes": _latency_summary(reclaim_latency),
        "opposite_boundary_hit_24h_rate": _rate(target_hits),
        "time_to_opposite_boundary_minutes": _latency_summary(target_minutes),
        "daily_path_efficiency": _latency_summary(daily_efficiency),
        "daily_overlap_fraction": _latency_summary(daily_overlap),
        "daily_rows": len(daily),
        "structure_coverage": manifest["structure_coverage"],
        "trader_sync_status": manifest["trader_sync_status"],
    }


def _cross_index_summary(path: Path) -> dict[str, Any]:
    rows = _read_jsonl(path)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        source = str(row["symbol"])
        for peer, state in dict(row["peer_states"]).items():
            grouped[(source, str(peer))].append(dict(state))

    pairs: list[dict[str, Any]] = []
    for (source, peer), states in sorted(grouped.items()):
        comparable = [state for state in states if state.get("agreement") is not None]
        lags = [
            int(state["lead_lag_minutes"])
            for state in comparable
            if state.get("lead_lag_minutes") is not None
        ]
        agreements = [bool(state["agreement"]) for state in comparable]
        absolute_lags = [abs(value) for value in lags]
        pairs.append(
            {
                "source": source,
                "peer": peer,
                "rows": len(states),
                "comparable_rows": len(comparable),
                "comparison_coverage": (
                    None if not states else len(comparable) / len(states)
                ),
                "agreement_rate": _rate(agreements),
                "signed_lead_lag_minutes": _latency_summary(lags),
                "absolute_lead_lag_minutes": _latency_summary(absolute_lags),
                "within_5m_rate": _rate([value <= 5 for value in absolute_lags]),
                "within_15m_rate": _rate([value <= 15 for value in absolute_lags]),
                "within_30m_rate": _rate([value <= 30 for value in absolute_lags]),
                "within_60m_rate": _rate([value <= 60 for value in absolute_lags]),
                "evidence_tier": "E1_ASSOCIATION_ONLY",
            }
        )
    return {"rows": len(rows), "ordered_pairs": pairs}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_report(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# CIBO Market Atlas — Journey 10Y Summary V1",
        "",
        f"- Identity: `{payload['identity']}`",
        f"- Source Journey run: `{payload['source_run_id']}`",
        f"- Total M5 bars: **{payload['totals']['retained_m5_bars']:,}**",
        f"- Total Journey episodes: **{payload['totals']['episodes']:,}**",
        f"- Total structure touches: **{payload['totals']['structure_touches']:,}**",
        f"- Cross-index rows: **{payload['cross_index']['rows']:,}**",
        "",
        "## Per market",
        "",
        "| Market | Episodes | Resolved departure | Opposite boundary <=24h |",
        "|---|---:|---:|---:|",
    ]
    for symbol in payload["symbols"]:
        departure = symbol["resolved_departure_rate"]
        target = symbol["opposite_boundary_hit_24h_rate"]
        lines.append(
            "| {symbol} | {episodes:,} | {departure:.2%} | {target:.2%} |".format(
                symbol=symbol["symbol"],
                episodes=symbol["episodes"],
                departure=0.0 if departure is None else departure,
                target=0.0 if target is None else target,
            )
        )
    lines.extend(
        [
            "",
            "## Governance / interpretation",
            "",
            (
                "These are consumed descriptive research statistics. Cross-index "
                "lead/lag is E1 association only. No field in this report authorizes "
                "a trader rule or execution."
            ),
            "",
            "`DEMO_ELIGIBLE=false`  ",
            "`LIVE_AUTHORIZED=false`  ",
            "`REAL_CAPITAL_AUTHORIZED=false`  ",
            "`PRODUCTION_AUTHORIZED=false`",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def build_summary(journeys_root: Path, aggregate_root: Path, output: Path) -> dict[str, Any]:
    manifests: list[tuple[Path, dict[str, Any]]] = []
    for path in journeys_root.rglob("journey-manifest.json"):
        payload = json.loads(path.read_text())
        if payload.get("identity") != SOURCE_IDENTITY:
            raise ValueError("unexpected Journey identity")
        manifests.append((path.parent, payload))
    if len(manifests) != 12:
        raise ValueError(f"expected 12 Journey symbol manifests, found {len(manifests)}")

    symbols = [
        _symbol_summary(root, manifest)
        for root, manifest in sorted(manifests, key=lambda item: item[1]["symbol"])
    ]
    cross_path = aggregate_root / "CROSS_INDEX_JOURNEY_LEDGER.jsonl"
    if not cross_path.exists():
        raise ValueError("cross-index Journey ledger missing")
    cross = _cross_index_summary(cross_path)

    retained = sum(int(item["retained_m5_bars"]) for item in symbols)
    episodes = sum(int(item["episodes"]) for item in symbols)
    touches = sum(
        int(manifest["ledger_counts"]["STRUCTURE_TOUCH_LEDGER"])
        for _, manifest in manifests
    )
    daily_rows = sum(int(item["daily_rows"]) for item in symbols)
    payload = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_identity": SOURCE_IDENTITY,
        "source_run_id": SOURCE_RUN_ID,
        "source_git_sha": SOURCE_GIT_SHA,
        "totals": {
            "retained_m5_bars": retained,
            "episodes": episodes,
            "structure_touches": touches,
            "daily_rows": daily_rows,
        },
        "symbols": symbols,
        "cross_index": cross,
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "cross_index_evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "cibo-journey-10y-summary.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_report(payload, output / "cibo-journey-10y-summary.md")
    (output / "cibo-journey-10y-summary.sha256").write_text(_sha256(json_path) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="CIBO Journey 10Y descriptive summary")
    parser.add_argument("journeys_root", type=Path)
    parser.add_argument("aggregate_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_summary(args.journeys_root, args.aggregate_root, args.output)
    print(json.dumps(result["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
