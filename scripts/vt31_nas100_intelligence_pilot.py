"""Causal, research-only intelligence pilot for VT31_NAS100."""
# ruff: noqa: B009,I001
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast
from zoneinfo import ZoneInfo

import vt31_nas100_r1_candidate as baseline
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as source_model
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
)

SCHEMA = "qore.vt31.nas100.intelligence_pilot.v1"
MARKET = "NAS100"
NY = ZoneInfo("America/New_York")
FRICTION = Decimal("0.05")
ENTRY_FLOOR = 10 * 60 + 30
ENTRY_CLOSE = 11 * 60
CIBO_SCHEMA = "qore.cibo_atlas.vt31.eight_ledger_bundle.v1"
CIBO_ARTIFACT_ID = 10478487667
CIBO_DIGEST = "sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _minute(value: datetime) -> int:
    local = value.astimezone(NY)
    return local.hour * 60 + local.minute


def _bar_minute(bar: object) -> int:
    return _minute(cast(datetime, getattr(bar, "opened_at")))


def _ratio(n: int, d: int) -> str:
    return "0" if d == 0 else format(Decimal(n) / Decimal(d), "f")


def build_knowledge(ledger_dir: Path) -> dict[str, Any]:
    """Build aggregate CIBO knowledge; never map an outcome back to a live date."""
    summary = json.loads(
        (ledger_dir / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json").read_text()
    )
    if summary.get("schema") != CIBO_SCHEMA or summary.get("research_only") is not True:
        raise ValueError("CIBO bundle governance/schema mismatch")
    departures = [
        r for r in _jsonl(ledger_dir / "DEPARTURE_TIMING_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    trader = [
        r for r in _jsonl(ledger_dir / "TRADER_MARKET_SYNC_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    targets = [
        r for r in _jsonl(ledger_dir / "TARGET_DESTINATION_LEDGER.jsonl")
        if r.get("market") == MARKET
    ]
    if (len(departures), len(trader), len(targets)) != (547, 208, 1591):
        raise ValueError("unexpected NAS100 CIBO row counts")

    structures = Counter(str(r.get("last_structure_before_departure")) for r in departures)
    source_hour = [
        r for r in departures
        if 600 <= _minute(datetime.fromisoformat(str(r["departure_at"]))) < 660
    ]
    late = [
        r for r in source_hour
        if _minute(datetime.fromisoformat(str(r["departure_at"]))) >= 630
    ]
    initial = [r for r in trader if r.get("terminal_family") == "initial_stop"]
    protected = [r for r in trader if r.get("terminal_family") == "protected_stop"]
    initial_later = sum(
        bool(r.get("trader_stopped_before_eventual_source_objective")) for r in initial
    )
    protected_later = sum(
        bool(r.get("trader_stopped_before_eventual_source_objective")) for r in protected
    )
    target_hits = [r for r in targets if bool(r.get("opposite_boundary_hit_by_16"))]
    ext_025 = sum(
        bool(r.get("post_boundary_ladder", {}).get("0.25")) for r in target_hits
    )
    reclaim_count = structures.get("local-liquidity-sweep-reclaim", 0) + structures.get(
        "reference-liquidity-sweep-reclaim", 0
    )

    return {
        "schema": "qore.vt31.nas100.cibo_knowledge.v1",
        "binding": {
            "artifact_id": CIBO_ARTIFACT_ID,
            "digest": CIBO_DIGEST,
            "source_sha": (ledger_dir / "git-sha.txt").read_text().strip(),
        },
        "timing": {
            "completed_reversals": len(departures),
            "source_hour_departures": len(source_hour),
            "late_source_hour_departures": len(late),
            "late_share": _ratio(len(late), len(source_hour)),
            "pilot_entry_floor_ny": "10:30",
        },
        "structure": {
            "last_structure_counts": dict(sorted(structures.items())),
            "local_or_reference_reclaim_rate": _ratio(reclaim_count, len(departures)),
        },
        "stops": {
            "initial_stop_later_objective_rate": _ratio(initial_later, len(initial)),
            "protected_stop_later_objective_rate": _ratio(
                protected_later, len(protected)
            ),
        },
        "targets": {
            "opposite_boundary_hit_by_16_rate": _ratio(len(target_hits), len(targets)),
            "plus_0_25_after_boundary_rate": _ratio(ext_025, len(target_hits)),
        },
        "runtime_policy": {
            "timing": "wait-until-10:30-NY",
            "entry": "causal-reclaim-then-source-valid-pd-array",
            "stop": "raid-to-decision-structural-extreme",
            "target": "opposite-frozen-09-reference-boundary",
            "management": "no-premature-protected-trail-or-BE",
            "date_level_outcome_lookup": False,
        },
    }


def _reference_reclaim(
    prefix: tuple[object, ...], source: Vt31R22SourceSetup
) -> datetime | None:
    for bar in prefix:
        closed = cast(datetime, getattr(bar, "closed_at"))
        if closed < source.structure.raid_at or _bar_minute(bar) < ENTRY_FLOOR:
            continue
        close = _d(getattr(bar, "close"))
        if source.side.value == "short" and close < source.reference.high:
            return closed
        if source.side.value == "long" and close > source.reference.low:
            return closed
    return None


def _local_reclaim(
    prefix: tuple[object, ...], source: Vt31R22SourceSetup
) -> datetime | None:
    bars = [
        b for b in prefix
        if cast(datetime, getattr(b, "closed_at")) >= source.structure.raid_at
    ]
    for i in range(3, len(bars)):
        bar = bars[i]
        if _bar_minute(bar) < ENTRY_FLOOR:
            continue
        prev = bars[i - 3:i]
        prior_high = max(_d(getattr(x, "high")) for x in prev)
        prior_low = min(_d(getattr(x, "low")) for x in prev)
        high, low, close = (_d(getattr(bar, x)) for x in ("high", "low", "close"))
        if source.side.value == "short" and high > prior_high and close < prior_high:
            return cast(datetime, getattr(bar, "closed_at"))
        if source.side.value == "long" and low < prior_low and close > prior_low:
            return cast(datetime, getattr(bar, "closed_at"))
    return None


def _reclaim(
    prefix: tuple[object, ...], source: Vt31R22SourceSetup
) -> tuple[datetime, str] | None:
    ref = _reference_reclaim(prefix, source)
    local = _local_reclaim(prefix, source)
    choices = [
        (ref, "reference-liquidity-sweep-reclaim"),
        (local, "local-liquidity-sweep-reclaim"),
    ]
    valid = [(t, k) for t, k in choices if t is not None]
    return min(valid, key=lambda x: x[0]) if valid else None


def _adaptive_stop(
    prefix: tuple[object, ...], source: Vt31R22SourceSetup, at: datetime
) -> Decimal:
    bars = [
        b for b in prefix
        if source.structure.raid_at <= cast(datetime, getattr(b, "closed_at")) <= at
    ]
    if not bars:
        return source.structure.swing_extreme
    field = "high" if source.side.value == "short" else "low"
    values = [_d(getattr(b, field)) for b in bars]
    return max(values) if source.side.value == "short" else min(values)


def decide(
    prefix: tuple[object, ...], source: Vt31R22SourceSetup
) -> tuple[Vt31R22ExecutableSetup | None, dict[str, object]]:
    """Return a causal execution decision plus an auditable reasoning trace."""
    as_of = cast(datetime, getattr(prefix[-1], "closed_at"))
    if _minute(as_of) < ENTRY_FLOOR:
        return None, {"state": "wait", "reason": "before-10:30"}
    reclaim = _reclaim(prefix, source)
    if reclaim is None:
        return None, {"state": "wait", "reason": "no-causal-reclaim"}
    reclaim_at, reclaim_kind = reclaim
    candidates = [
        c for c in source.candidates
        if c.formed_at >= reclaim_at
        and ENTRY_FLOOR <= _minute(c.formed_at) < ENTRY_CLOSE
    ]
    if not candidates:
        return None, {"state": "wait", "reason": "no-post-reclaim-pd-array"}

    first_at = min(c.formed_at for c in candidates)
    same_time = [c for c in candidates if c.formed_at == first_at]
    prices = {(c.zone_lower + c.zone_upper) / Decimal(2) for c in same_time}
    if len(prices) != 1:
        return None, {"state": "abstain", "reason": "ambiguous-entry"}
    chosen = sorted(same_time, key=lambda c: c.family.value)[0]
    entry = next(iter(prices))
    decision_at = max(first_at, reclaim_at)
    stop = _adaptive_stop(prefix, source, decision_at)
    target = source.target_price
    if source.side.value == "short":
        valid = target < entry < stop
    else:
        valid = stop < entry < target
    if not valid:
        return None, {"state": "abstain", "reason": "invalid-adaptive-geometry"}

    risk = abs(entry - stop)
    ref_width = source.reference.high - source.reference.low
    target_r = abs(target - entry) / risk
    setup = Vt31R22ExecutableSetup(
        side=source.side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=target,
        selected_family=chosen.family,
        candidate_families=tuple(c.family for c in same_time),
        decision_at=decision_at,
        pending_expires_at=source.pending_expires_at,
        source_setup=source,
        execution_policy_fingerprint="vt31-nas100-intelligence-pilot-v1",
    )
    return setup, {
        "state": "execute",
        "reason": "late-reclaim-plus-source-valid-pd-array",
        "reclaim_kind": reclaim_kind,
        "reclaim_at": reclaim_at.astimezone(UTC).isoformat(),
        "decision_at": decision_at.astimezone(UTC).isoformat(),
        "entry_family": chosen.family.value,
        "entry": format(entry, "f"),
        "stop": format(stop, "f"),
        "target": format(target, "f"),
        "planned_target_r": format(target_r, "f"),
        "risk_to_reference": (
            format(risk / ref_width, "f") if ref_width > 0 else None
        ),
        "management": "no-premature-BE-or-protected-trail",
    }


def _disabled_mc(
    _trades: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, bool]]:
    return (
        {"algorithm": "deferred-intelligence-pilot", "paths": 0},
        {
            "positive_terminal_probability_at_least_0_70": False,
            "p95_max_drawdown_at_most_20r": False,
        },
    )


def _median(trades: list[dict[str, object]], field: str) -> str | None:
    vals = [Decimal(cast(str, t[field])) for t in trades if field in t]
    return None if not vals else format(median(vals), "f")


def replay(ledger_dir: Path, evidence_path: Path) -> dict[str, object]:
    knowledge = build_knowledge(ledger_dir)
    series, account, evidence, checked, evidence_sha, provider = (
        baseline.load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("pilot requires NAS100 evidence")
    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[baseline._day(getattr(bar, "opened_at"))].append(bar)

    trades: list[dict[str, object]] = []
    traces: list[dict[str, object]] = []
    statuses: Counter[str] = Counter()
    abstains: Counter[str] = Counter()

    for day in sorted(by_day):
        bars = tuple(by_day[day])
        reference = tuple(
            b for b in bars
            if (9, 0, 0) <= baseline._wall(getattr(b, "opened_at")) < (10, 0, 0)
        )
        session = tuple(
            b for b in bars
            if (10, 0, 0) <= baseline._wall(getattr(b, "opened_at")) < (11, 0, 0)
        )
        if len(reference) != 60 or len(session) != 60:
            statuses["incomplete-day"] += 1
            continue
        prefix = list(reference)
        selected: Vt31R22ExecutableSetup | None = None
        trace: dict[str, object] | None = None
        last_reason = "no-source-setup"
        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue
            selected, trace = decide(tuple(prefix), evaluation.setup)
            last_reason = cast(str, trace["reason"])
            if trace["state"] in ("execute", "abstain"):
                break
        if selected is None or trace is None or trace["state"] != "execute":
            abstains[last_reason] += 1
            statuses["intelligence-abstain"] += 1
            continue
        outcome = baseline._simulate(bars, selected)
        status = cast(str, outcome["status"])
        statuses[status] += 1
        record = {
            "local_date": baseline._day(selected.decision_at).isoformat(),
            **trace,
            "outcome_status": status,
        }
        if status == "terminal":
            record["exit_reason"] = outcome["exit_reason"]
            record["r_multiple"] = outcome["r_multiple"]
            trades.append(outcome)
        traces.append(record)

    stress = baseline._metrics(trades, friction=FRICTION)
    original_mc = baseline._monte_carlo
    baseline._monte_carlo = _disabled_mc
    try:
        base = baseline.replay(evidence_path)
    finally:
        baseline._monte_carlo = original_mc
    base_stress = cast(dict[str, object], base["stress_0_05r"])
    comparison: dict[str, object] = {
        "baseline": base_stress,
        "intelligence": stress,
        "delta_sample": (
            cast(int, stress["sample"]) - cast(int, base_stress["sample"])
        ),
        "delta_mean_r": format(
            Decimal(cast(str, stress["mean_r"]))
            - Decimal(cast(str, base_stress["mean_r"])),
            "f",
        ),
        "delta_max_drawdown_r": format(
            Decimal(cast(str, stress["max_drawdown_r"]))
            - Decimal(cast(str, base_stress["max_drawdown_r"])),
            "f",
        ),
    }
    if (
        stress["profit_factor"] is not None
        and base_stress["profit_factor"] is not None
    ):
        comparison["delta_profit_factor"] = format(
            Decimal(cast(str, stress["profit_factor"]))
            - Decimal(cast(str, base_stress["profit_factor"])),
            "f",
        )
    else:
        comparison["delta_profit_factor"] = None

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "research_only": True,
        "opens_new_holdout": False,
        "fresh_holdout_consumed": False,
        "live_authorized": False,
        "production_authorized": False,
        "knowledge": knowledge,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
            "bar_count": len(series),
        },
        "capability": {
            "market_days": len(by_day),
            "executed_decisions": len(traces),
            "terminal_trades": len(trades),
            "abstention_counts": dict(sorted(abstains.items())),
            "status_counts": dict(sorted(statuses.items())),
            "median_planned_target_r": _median(trades, "planned_target_r"),
            "median_mfe_r": _median(trades, "mfe_r"),
            "median_mae_r": _median(trades, "mae_r"),
            "causal_decision_trace": True,
            "date_level_outcome_lookup": False,
        },
        "aggregate": baseline._metrics(trades),
        "stress_0_05r": stress,
        "baseline_comparison": comparison,
        "decision_trace": traces,
    }


def self_test() -> None:
    assert MARKET == "NAS100"
    assert ENTRY_FLOOR == 630 and ENTRY_CLOSE == 660
    assert CIBO_ARTIFACT_ID == 10478487667
    assert source_model.AUTHORIZED_MARKET == MARKET
    assert SCHEMA.endswith(".v1")
    print("VT31_NAS100 intelligence pilot self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ledger-dir", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if None in (args.ledger_dir, args.evidence, args.output):
        parser.error("--ledger-dir --evidence --output are required")
    payload = replay(args.ledger_dir, args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "market": MARKET,
                "capability": payload["capability"],
                "stress_0_05r": payload["stress_0_05r"],
                "baseline_comparison": payload["baseline_comparison"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
