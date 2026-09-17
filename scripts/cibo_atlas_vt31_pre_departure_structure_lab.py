"""Consumed-only CIBO Atlas pre-departure structure statistics for VT-31.

For every gap05-admissible market day whose first 09:00 range breach later reaches
the opposite 09:00 boundary, this lab finds the last unbroken M1 reaction pivot
before that objective and records which frozen source-setup zones the pivot
revisited (Breaker, Order Block, FVG) plus whether the pivot itself performed a
reference/local-liquidity sweep-and-reclaim. Trader outcomes are overlay labels
only. No candidate selection or fresh evidence is permitted.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_r8_sparse_reference_forensics as sparse
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22ReferenceRange,
    _detect_raid,
    _entry_evidence,
    _structure,
)

MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r5", "r6", "r8_fresh")
SCHEMA = "qore.cibo_atlas.vt31.pre_departure_structure_lab.v1"


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def fraction(n: int, d: int) -> str | None:
    return None if d == 0 else fmt(Decimal(n) / Decimal(d))


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


def bars_between(
    bars: tuple[OhlcSnapshot, ...], start: tuple[int, int, int], end: tuple[int, int, int]
) -> tuple[OhlcSnapshot, ...]:
    return tuple(bar for bar in bars if start <= _wall(bar.opened_at) < end)


def intersects(bar: OhlcSnapshot, evidence: Vt31R22EntryEvidence) -> bool:
    return dec(bar.high) >= evidence.zone_lower and dec(bar.low) <= evidence.zone_upper


def local_swing_indices(path: tuple[OhlcSnapshot, ...], side: str) -> list[int]:
    result: list[int] = []
    for i in range(2, len(path) - 2):
        if side == "short":
            center = dec(path[i].high)
            left = [dec(path[i - 2].high), dec(path[i - 1].high)]
            right = [dec(path[i + 1].high), dec(path[i + 2].high)]
            if center >= max(left) and center > max(right):
                result.append(i)
        else:
            center = dec(path[i].low)
            left = [dec(path[i - 2].low), dec(path[i - 1].low)]
            right = [dec(path[i + 1].low), dec(path[i + 2].low)]
            if center <= min(left) and center < min(right):
                result.append(i)
    return result


def departure_pivot(path: tuple[OhlcSnapshot, ...], side: str) -> tuple[int, str]:
    if len(path) < 2:
        return 0, "single-bar-fallback"
    swings = local_swing_indices(path, side)
    eligible: list[int] = []
    for i in swings:
        if side == "short":
            level = dec(path[i].high)
            if all(dec(bar.high) <= level for bar in path[i + 1 :]):
                eligible.append(i)
        else:
            level = dec(path[i].low)
            if all(dec(bar.low) >= level for bar in path[i + 1 :]):
                eligible.append(i)
    if eligible:
        return eligible[-1], "last-unbroken-2x2-swing"
    if side == "short":
        extreme = max(dec(bar.high) for bar in path[:-1])
        return max(i for i, bar in enumerate(path[:-1]) if dec(bar.high) == extreme), "path-extreme-fallback"
    extreme = min(dec(bar.low) for bar in path[:-1])
    return max(i for i, bar in enumerate(path[:-1]) if dec(bar.low) == extreme), "path-extreme-fallback"


def prior_confirmed_swing(path: tuple[OhlcSnapshot, ...], pivot_index: int, side: str) -> int | None:
    prefix = path[: pivot_index + 1]
    candidates = [i for i in local_swing_indices(prefix, side) if i <= pivot_index - 2]
    return candidates[-1] if candidates else None


def sweep_flags(
    path: tuple[OhlcSnapshot, ...], pivot_index: int, side: str, ref_high: Decimal, ref_low: Decimal
) -> tuple[bool, bool]:
    pivot = path[pivot_index]
    if side == "short":
        reference = dec(pivot.high) > ref_high and dec(pivot.close) < ref_high
    else:
        reference = dec(pivot.low) < ref_low and dec(pivot.close) > ref_low
    prior_index = prior_confirmed_swing(path, pivot_index, side)
    local = False
    if prior_index is not None:
        prior = path[prior_index]
        if side == "short":
            local = dec(pivot.high) > dec(prior.high) and dec(pivot.close) < dec(prior.high)
        else:
            local = dec(pivot.low) < dec(prior.low) and dec(pivot.close) > dec(prior.low)
    return reference, local


def signature(families: tuple[str, ...], reference_sweep: bool, local_sweep: bool) -> str:
    labels = list(families)
    if reference_sweep:
        labels.append("reference-liquidity-sweep")
    if local_sweep:
        labels.append("local-liquidity-sweep")
    return "+".join(sorted(set(labels))) if labels else "none-recognized"


@dataclass(frozen=True, slots=True)
class DepartureRow:
    partition: str
    market: str
    ny_date: str
    side: str
    objective_at: str
    pivot_at: str
    pivot_method: str
    pivot_minute_from_1000: int
    reference_width: Decimal
    pivot_to_objective_ref: Decimal
    source_families_available: tuple[str, ...]
    source_families_touched: tuple[str, ...]
    reference_liquidity_sweep: bool
    local_liquidity_sweep: bool
    structure_signature: str
    path_contiguous_to_objective: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "market": self.market,
            "ny_date": self.ny_date,
            "side": self.side,
            "objective_at": self.objective_at,
            "pivot_at": self.pivot_at,
            "pivot_method": self.pivot_method,
            "pivot_minute_from_1000": self.pivot_minute_from_1000,
            "reference_width": fmt(self.reference_width),
            "pivot_to_objective_ref": fmt(self.pivot_to_objective_ref),
            "source_families_available": list(self.source_families_available),
            "source_families_touched": list(self.source_families_touched),
            "reference_liquidity_sweep": self.reference_liquidity_sweep,
            "local_liquidity_sweep": self.local_liquidity_sweep,
            "structure_signature": self.structure_signature,
            "path_contiguous_to_objective": self.path_contiguous_to_objective,
        }


def analyze_day(partition: str, market: str, day_bars: tuple[OhlcSnapshot, ...]) -> DepartureRow | None:
    reference = cast(tuple[OhlcSnapshot, ...], sparse._reference_bars(cast(tuple[object, ...], day_bars)))
    session = bars_between(day_bars, (10, 0, 0), (11, 0, 0))
    lifecycle = bars_between(day_bars, (10, 0, 0), (16, 0, 0))
    if len(session) != 60 or not reference or not sparse._policy_accepts(cast(tuple[object, ...], reference), "gap05"):
        return None
    ref_high = max(dec(bar.high) for bar in reference)
    ref_low = min(dec(bar.low) for bar in reference)
    ref_width = ref_high - ref_low
    if ref_width <= 0:
        return None
    ref_obj = Vt31R22ReferenceRange(
        high=ref_high,
        low=ref_low,
        opened_at=reference[0].opened_at,
        closed_at=reference[-1].closed_at,
    )
    raid = _detect_raid(session, ref_obj)
    if raid is None or raid.high_taken and raid.low_taken:
        return None
    side = raid.side.value
    structure = _structure(session, raid)
    candidates: tuple[Vt31R22EntryEvidence, ...] = ()
    if structure is not None:
        confirmation_index, extreme_index, _, _ = structure
        candidates = _entry_evidence(session, raid, confirmation_index, extreme_index)
    raid_at = session[raid.index].opened_at
    eligible = tuple(bar for bar in lifecycle if bar.opened_at >= raid_at)
    objective_index: int | None = None
    for i, bar in enumerate(eligible):
        if side == "short" and dec(bar.low) <= ref_low:
            objective_index = i
            break
        if side == "long" and dec(bar.high) >= ref_high:
            objective_index = i
            break
    if objective_index is None:
        return None
    path = eligible[: objective_index + 1]
    pivot_index, pivot_method = departure_pivot(path, side)
    pivot = path[pivot_index]
    objective = path[-1]
    touched = tuple(
        sorted(
            {
                candidate.family.value
                for candidate in candidates
                if candidate.formed_at <= pivot.closed_at and intersects(pivot, candidate)
            }
        )
    )
    available = tuple(sorted({candidate.family.value for candidate in candidates}))
    reference_sweep, local_sweep = sweep_flags(path, pivot_index, side, ref_high, ref_low)
    if side == "short":
        pivot_to_objective = max(Decimal(0), dec(pivot.high) - ref_low) / ref_width
    else:
        pivot_to_objective = max(Decimal(0), ref_high - dec(pivot.low)) / ref_width
    contiguous = all(cur.opened_at == prev.closed_at for prev, cur in zip(path, path[1:], strict=False))
    local = pivot.opened_at.astimezone(sparse.NY)
    return DepartureRow(
        partition=partition,
        market=market,
        ny_date=str(_day(pivot.opened_at)),
        side=side,
        objective_at=objective.opened_at.isoformat(),
        pivot_at=pivot.opened_at.isoformat(),
        pivot_method=pivot_method,
        pivot_minute_from_1000=local.hour * 60 + local.minute - 600,
        reference_width=ref_width,
        pivot_to_objective_ref=pivot_to_objective,
        source_families_available=available,
        source_families_touched=touched,
        reference_liquidity_sweep=reference_sweep,
        local_liquidity_sweep=local_sweep,
        structure_signature=signature(touched, reference_sweep, local_sweep),
        path_contiguous_to_objective=contiguous,
    )


def load_days(partition: str, market: str, path: Path) -> list[DepartureRow]:
    series, _, _, _, _, _ = load_market_evidence(path)
    by_day: dict[date, list[OhlcSnapshot]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)
    rows: list[DepartureRow] = []
    for _, bars in sorted(by_day.items()):
        row = analyze_day(partition, market, tuple(bars))
        if row is not None:
            rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    signatures = Counter(str(row["structure_signature"]) for row in rows)
    family_counts: Counter[str] = Counter()
    for row in rows:
        for family in cast(list[str], row["source_families_touched"]):
            family_counts[family] += 1
    pivots = [Decimal(str(row["pivot_minute_from_1000"])) for row in rows]
    distances = [dec(row["pivot_to_objective_ref"]) for row in rows]
    return {
        "n": len(rows),
        "contiguous_path_rate": fraction(sum(bool(row["path_contiguous_to_objective"]) for row in rows), len(rows)),
        "signature_counts": dict(sorted(signatures.items())),
        "signature_rates": {key: fraction(value, len(rows)) for key, value in sorted(signatures.items())},
        "family_touch_counts": dict(sorted(family_counts.items())),
        "family_touch_rates": {key: fraction(value, len(rows)) for key, value in sorted(family_counts.items())},
        "reference_liquidity_sweep_rate": fraction(sum(bool(row["reference_liquidity_sweep"]) for row in rows), len(rows)),
        "local_liquidity_sweep_rate": fraction(sum(bool(row["local_liquidity_sweep"]) for row in rows), len(rows)),
        "pivot_minute_from_1000_p50": fmt(quantile(pivots, Decimal("0.5"))),
        "pivot_to_objective_ref_p50": fmt(quantile(distances, Decimal("0.5"))),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    attribution = cast(dict[str, Any], json.loads(cast(Path, args.attribution).read_text(encoding="utf-8")))
    if attribution.get("schema") != "qore.cibo_atlas.vt31.root_cause_attribution.v1":
        raise ValueError("requires immutable root-cause attribution v1")
    all_rows: list[DepartureRow] = []
    for partition in PARTITIONS:
        for market in MARKETS:
            all_rows.extend(load_days(partition, market, cast(Path, getattr(args, f"{partition}_{market.lower()}"))))
    keyed: dict[tuple[str, str], DepartureRow] = {}
    for row in all_rows:
        key = (row.market, row.ny_date)
        if key in keyed:
            raise ValueError(f"overlapping consumed departure day {key}")
        keyed[key] = row
    market_rows = [row.to_dict() for row in sorted(keyed.values(), key=lambda item: (item.ny_date, item.market))]
    demonstrated_roots: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for raw in cast(list[dict[str, Any]], attribution["rows"]):
        if raw.get("demonstrated_path_fact") != "demonstrated_exit_before_eventual_source_objective":
            continue
        key = (str(raw["market"]), str(raw["ny_date"]))
        departure = keyed.get(key)
        if departure is None:
            unmapped.append(str(raw["root_id"]))
            continue
        row = departure.to_dict()
        row.update(
            {
                "root_id": raw["root_id"],
                "terminal_family": raw["terminal_family"],
                "entry_family": raw["entry_family"],
                "trader_side": raw["side"],
                "risk_to_reference": raw["risk_to_reference"],
                "confirmation_body_fraction": raw["confirmation_body_fraction"],
                "raid_to_confirmation_latency_m1": raw["raid_to_confirmation_latency_m1"],
                "protected_swing_like_at_signal": raw["protected_swing_like_at_signal"],
                "cross_index_state": raw["cross_index_state"],
            }
        )
        demonstrated_roots.append(row)
    if unmapped:
        raise ValueError(f"demonstrated roots missing pre-departure market row: {len(unmapped)}")
    if len(demonstrated_roots) != 163:
        raise ValueError(f"expected 163 demonstrated roots, got {len(demonstrated_roots)}")
    by_market = {
        market: summarize([row for row in market_rows if row["market"] == market]) for market in MARKETS
    }
    demonstrated_by_market = {
        market: summarize([row for row in demonstrated_roots if row["market"] == market]) for market in MARKETS
    }
    by_terminal_family = {
        family: summarize([row for row in demonstrated_roots if row["terminal_family"] == family])
        for family in ("initial_stop", "protected_stop")
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "definition_contract": {
            "breaker_order_block_fvg": "reuse-frozen-vt31-r2.2-source-formalization",
            "departure_pivot": "last-unbroken-2x2-m1-swing-before-first-opposite-09-boundary-hit-with-path-extreme-fallback",
            "reference_liquidity_sweep": "pivot-penetrates-09-reference-boundary-and-closes-back-inside",
            "local_liquidity_sweep": "pivot-penetrates-most-recent-confirmed-2x2-local-swing-and-closes-back-through-it",
            "multi_label": True,
            "post_outcome_diagnostic_only": True,
        },
        "objective_completion_market_day_count": len(market_rows),
        "market_baseline_by_market": by_market,
        "demonstrated_stop_root_count": len(demonstrated_roots),
        "demonstrated_stop_by_market": demonstrated_by_market,
        "demonstrated_stop_by_terminal_family": by_terminal_family,
        "interpretation_constraints": [
            "a touched structure is a statistical waypoint, not proof of causality",
            "source-family touch only uses zones formed by the frozen VT31 source formalization",
            "liquidity-sweep labels are CIBO diagnostic definitions, not claimed TTrades source rules",
            "no family or signature may be promoted directly into a trader rule",
            "market-specific repair requires post-exit structure continuity and leakage-free WFO",
        ],
        "market_day_rows": market_rows,
        "demonstrated_root_rows": demonstrated_roots,
    }
    out = cast(Path, args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cibo-atlas-vt31-pre-departure-structure-lab.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    compact = {
        "market_days": len(market_rows),
        "demonstrated_roots": len(demonstrated_roots),
        "market_baseline_by_market": by_market,
        "demonstrated_stop_by_market": demonstrated_by_market,
        "demonstrated_stop_by_terminal_family": by_terminal_family,
    }
    (out / "cibo-atlas-vt31-pre-departure-structure-summary.json").write_text(
        json.dumps(compact, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def self_test() -> None:
    assert signature(("fair-value-gap",), False, True) == "fair-value-gap+local-liquidity-sweep"
    assert signature((), False, False) == "none-recognized"
    assert fraction(1, 4) == "0.25"
    print("CIBO Atlas VT31 pre-departure structure lab self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--attribution", type=Path)
    parser.add_argument("--output-dir", type=Path)
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_', '-')}-{market.lower()}", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    required = [args.attribution, args.output_dir]
    required.extend(
        getattr(args, f"{partition}_{market.lower()}") for partition in PARTITIONS for market in MARKETS
    )
    if any(value is None for value in required):
        parser.error("attribution, output-dir and all nine consumed market files are required")
    payload = build(args)
    print(
        json.dumps(
            {
                "market_days": payload["objective_completion_market_day_count"],
                "demonstrated_roots": payload["demonstrated_stop_root_count"],
                "by_market": payload["demonstrated_stop_by_market"],
                "by_terminal_family": payload["demonstrated_stop_by_terminal_family"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
