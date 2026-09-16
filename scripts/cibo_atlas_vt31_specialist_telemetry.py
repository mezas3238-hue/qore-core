"""Consumed-only specialist trader telemetry for CIBO Atlas / VT-31.

The input is the definitive tick-corrected deep-forensics artifact. All market
structure columns are PRE_ENTRY observations reconstructed under frozen consumed
semantics. Terminal outcomes are POST_OUTCOME_RESEARCH labels only. The output
is diagnostic and cannot select markets, parameters, candidates, or fresh data.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, cast

MARKETS = ("NAS100", "SP500", "US30")
SCHEMA = "qore.cibo_atlas.vt31.specialist_telemetry.v1"
NUMERIC_FEATURES = (
    "signal_minute",
    "risk_to_reference",
    "raid_body_fraction",
    "raid_wick_fraction",
    "raid_depth_to_reference",
    "final_extreme_depth_to_reference",
    "raid_to_final_extreme_latency_m1",
    "raid_to_confirmation_latency_m1",
    "confirmation_body_fraction",
    "confirmation_range_to_reference",
    "displacement_beyond_anchor_to_reference",
    "entry_location_to_reference",
    "protected_swing_opposing_series_length",
    "opposing_liquidity_r",
)


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def quantile(values: list[Decimal], p: Decimal) -> Decimal | None:
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


def terminal_family(row: dict[str, Any]) -> str:
    status = str(row.get("terminal_status", "")).lower()
    if "initial-stop" in status:
        return "initial_stop"
    if "protected-stop" in status:
        return "protected_stop"
    if "target" in status:
        return "target"
    return "other"


def numeric_distribution(rows: list[dict[str, Any]], feature: str) -> dict[str, Any]:
    values: list[Decimal] = []
    for row in rows:
        raw = row.get(feature)
        if raw is None or isinstance(raw, bool):
            continue
        try:
            values.append(dec(raw))
        except Exception:
            continue
    if not values:
        return {"n": 0, "p10": None, "p50": None, "p90": None, "mean": None}
    total = sum(values, Decimal(0))
    return {
        "n": len(values),
        "p10": fmt(quantile(values, Decimal("0.10"))),
        "p50": fmt(quantile(values, Decimal("0.50"))),
        "p90": fmt(quantile(values, Decimal("0.90"))),
        "mean": fmt(total / Decimal(len(values))),
    }


def distributions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {feature: numeric_distribution(rows, feature) for feature in NUMERIC_FEATURES}


def outcome_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(terminal_family(row) for row in rows)
    return {key: int(value) for key, value in sorted(counts.items())}


def max_losing_streak(rows: list[dict[str, Any]]) -> int:
    ordered = sorted(rows, key=lambda row: (str(row["signal_at"]), str(row["root_id"])))
    maximum = 0
    current = 0
    for row in ordered:
        if dec(row["terminal_r"]) < 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def grouped_outcomes(
    rows: list[dict[str, Any]], key: Callable[[dict[str, Any]], str]
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    output: dict[str, Any] = {}
    for name, group in sorted(groups.items()):
        n = len(group)
        wins = sum(dec(row["terminal_r"]) > 0 for row in group)
        losses = sum(dec(row["terminal_r"]) < 0 for row in group)
        mean = sum((dec(row["terminal_r"]) for row in group), Decimal(0)) / Decimal(n)
        output[name] = {
            "n": n,
            "wins": wins,
            "losses": losses,
            "mean_terminal_r": fmt(mean),
            "terminal_family_counts": outcome_counts(group),
        }
    return output


def specialist(rows: list[dict[str, Any]], market: str) -> dict[str, Any]:
    own = [row for row in rows if row["market"] == market]
    if not own:
        raise ValueError(f"missing specialist rows for {market}")
    by_outcome: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in own:
        by_outcome[terminal_family(row)].append(row)
    return {
        "market": market,
        "terminal_count": len(own),
        "date_from": min(str(row["ny_date"]) for row in own),
        "date_to": max(str(row["ny_date"]) for row in own),
        "side_counts": dict(sorted(Counter(str(row["side"]) for row in own).items())),
        "entry_family_counts": dict(
            sorted(Counter(str(row["entry_family"]) for row in own).items())
        ),
        "resolution_source_counts": dict(
            sorted(Counter(str(row["resolution_source"]) for row in own).items())
        ),
        "terminal_family_counts": outcome_counts(own),
        "max_losing_streak_within_market": max_losing_streak(own),
        "pre_entry_distributions": distributions(own),
        "outcome_label_distributions": {
            outcome: distributions(group) for outcome, group in sorted(by_outcome.items())
        },
        "side_outcomes": grouped_outcomes(own, lambda row: str(row["side"])),
        "entry_family_outcomes": grouped_outcomes(
            own, lambda row: str(row["entry_family"])
        ),
        "side_x_entry_family_outcomes": grouped_outcomes(
            own, lambda row: f"{row['side']}::{row['entry_family']}"
        ),
        "protected_swing_state_outcomes": grouped_outcomes(
            own, lambda row: str(row["protected_swing_like_at_signal"])
        ),
    }


def load(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema") != "qore.vt31.tick_corrected.deep_forensics.v1":
        raise ValueError("specialist telemetry requires definitive deep-forensics v1")
    if payload.get("research_only") is not True:
        raise ValueError("deep-forensics must remain research-only")
    if payload.get("selection_prohibited") is not True:
        raise ValueError("deep-forensics selection must be prohibited")
    if payload.get("opens_new_holdout") is not False:
        raise ValueError("deep-forensics cannot open fresh evidence")
    if payload.get("feature_timing") != "pre-entry-only":
        raise ValueError("feature timing must remain pre-entry-only")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 618:
        raise ValueError("definitive deep-forensics must contain 618 terminal rows")
    return payload


def build(source: Path, output_dir: Path) -> dict[str, Any]:
    source_payload = load(source)
    rows = cast(list[dict[str, Any]], source_payload["rows"])
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "feature_timing": "pre-entry-only",
        "outcome_timing": "post-outcome-research-label-only",
        "source_terminal_count": len(rows),
        "specialists": {market: specialist(rows, market) for market in MARKETS},
        "governance": {
            "positive_subgroup_is_candidate": False,
            "automatic_market_drop": False,
            "automatic_parameter_change": False,
            "requires_methodology_binding": True,
            "requires_leakage_free_walk_forward": True,
        },
    }
    if sum(int(payload["specialists"][m]["terminal_count"]) for m in MARKETS) != 618:
        raise ValueError("specialist telemetry terminal conservation failed")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-specialist-telemetry.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def self_test() -> None:
    sample = [
        {"terminal_status": "initial-stop-after-fill", "terminal_r": "-1", "signal_at": "1", "root_id": "a"},
        {"terminal_status": "fixed-2r-target", "terminal_r": "2", "signal_at": "2", "root_id": "b"},
    ]
    assert terminal_family(sample[0]) == "initial_stop"
    assert terminal_family(sample[1]) == "target"
    assert max_losing_streak(sample) == 1
    assert quantile([Decimal(1), Decimal(3)], Decimal("0.5")) == Decimal(2)
    print("CIBO Atlas specialist telemetry self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.source is None or args.output_dir is None:
        parser.error("source and output-dir are required")
    payload = build(args.source, args.output_dir)
    print(json.dumps(payload["specialists"], sort_keys=True))


if __name__ == "__main__":
    main()
