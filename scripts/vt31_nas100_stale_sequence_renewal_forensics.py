"""Forensics for causal renewal after a stale VT31_NAS100 sequence.

The stale state itself was defined before its economic read by Market State V2:
reference reclaim latency 8-14 minutes at the first executable source setup.

This module does NOT create a runtime policy.  It asks a narrower causal
question: after that setup becomes stale, does NAS100 produce a genuinely new,
observable local structural confirmation followed by a fresh same-side FVG
before 11:00, while the original structural hypothesis remains valid?

Post-stale bars are consumed incrementally and an event is observable only
after its closing bar.  Outcome simulation is a research label and is never
fed back into event detection.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_r1_candidate as baseline

from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryFamily,
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.stale_sequence_renewal_forensics.v1"
SOURCE_SCHEMA = "qore.vt31.nas100.market_state_lab.v2"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
POLICY_ID = "vt31-nas100-renewed-local-structure-fresh-fvg-forensics-v1"
POLICY_FINGERPRINT = hashlib.sha256(POLICY_ID.encode()).hexdigest()


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _local_minute(bar: object) -> int:
    opened = cast(datetime, getattr(bar, "opened_at"))
    local = opened.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    return local.hour * 60 + local.minute


def _touches_original_invalidation(
    bar: object,
    side: str,
    stop: Decimal,
) -> bool:
    if side == "long":
        return _d(getattr(bar, "low")) <= stop
    return _d(getattr(bar, "high")) >= stop


def _touches_target(bar: object, side: str, target: Decimal) -> bool:
    if side == "long":
        return _d(getattr(bar, "high")) >= target
    return _d(getattr(bar, "low")) <= target


def _renewed_structure(
    bars: tuple[object, ...],
    side: str,
) -> tuple[int, int, Decimal, Decimal] | None:
    """Find first post-WAIT local structural confirmation causally."""
    if len(bars) < 2:
        return None
    extreme_index = 0
    first = bars[0]
    if side == "short":
        extreme = _d(getattr(first, "high"))
        anchor = _d(getattr(first, "low"))
        for index in range(1, len(bars)):
            bar = bars[index]
            if _d(getattr(bar, "high")) > extreme:
                extreme = _d(getattr(bar, "high"))
                anchor = _d(getattr(bar, "low"))
                extreme_index = index
                continue
            if _d(getattr(bar, "close")) < anchor:
                return index, extreme_index, extreme, anchor
        return None

    extreme = _d(getattr(first, "low"))
    anchor = _d(getattr(first, "high"))
    for index in range(1, len(bars)):
        bar = bars[index]
        if _d(getattr(bar, "low")) < extreme:
            extreme = _d(getattr(bar, "low"))
            anchor = _d(getattr(bar, "high"))
            extreme_index = index
            continue
        if _d(getattr(bar, "close")) > anchor:
            return index, extreme_index, extreme, anchor
    return None


def _fresh_fvg(
    bars: tuple[object, ...],
    side: str,
    not_before_index: int,
) -> tuple[int, Decimal, Decimal] | None:
    """Return first three-bar FVG whose formation is after renewed structure."""
    start = max(2, not_before_index)
    for third_index in range(start, len(bars)):
        first = bars[third_index - 2]
        third = bars[third_index]
        if side == "short":
            lower = _d(getattr(third, "high"))
            upper = _d(getattr(first, "low"))
            if lower < upper:
                return third_index, lower, upper
        else:
            lower = _d(getattr(first, "high"))
            upper = _d(getattr(third, "low"))
            if lower < upper:
                return third_index, lower, upper
    return None


def _source_at_signal(
    day_bars: tuple[object, ...],
    signal_at: datetime,
    evidence_fingerprint: str,
) -> tuple[Vt31R22SourceSetup, Vt31R22ExecutableSetup] | None:
    reference = tuple(
        bar
        for bar in day_bars
        if (9, 0, 0) <= baseline._wall(getattr(bar, "opened_at")) < (10, 0, 0)
    )
    if len(reference) != 60:
        return None
    prefix = list(reference)
    policy = Vt31R22ExecutionPolicy()
    for bar in day_bars:
        wall = baseline._wall(getattr(bar, "opened_at"))
        if not (10, 0, 0) <= wall < (11, 0, 0):
            continue
        prefix.append(bar)
        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=getattr(bar, "closed_at"),
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence_fingerprint,
        )
        if evaluation.setup is None:
            continue
        executable, _ = make_executable_setup(evaluation.setup, policy)
        if executable is None:
            return None
        if executable.decision_at == signal_at:
            return evaluation.setup, executable
        if executable.decision_at > signal_at:
            return None
    return None


def _renewal_candidate(
    post_wait: tuple[object, ...],
    source: Vt31R22SourceSetup,
    original: Vt31R22ExecutableSetup,
) -> tuple[Vt31R22ExecutableSetup | None, dict[str, object]]:
    side = source.side.value
    target = source.target_price
    original_stop = original.stop_price

    invalidated_at: datetime | None = None
    target_reached_at: datetime | None = None
    for bar in post_wait:
        if invalidated_at is None and _touches_original_invalidation(
            bar, side, original_stop
        ):
            invalidated_at = cast(datetime, getattr(bar, "closed_at"))
        if target_reached_at is None and _touches_target(bar, side, target):
            target_reached_at = cast(datetime, getattr(bar, "closed_at"))

    structure = _renewed_structure(post_wait, side)
    if structure is None:
        return None, {
            "renewed_structure": False,
            "fresh_fvg": False,
            "reason": "no-renewed-local-structure-before-11",
        }
    confirmation_index, extreme_index, renewed_extreme, structural_level = structure
    confirmation_at = cast(datetime, getattr(post_wait[confirmation_index], "closed_at"))

    if invalidated_at is not None and invalidated_at <= confirmation_at:
        return None, {
            "renewed_structure": True,
            "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
            "fresh_fvg": False,
            "reason": "original-hypothesis-invalidated-before-renewal-confirmation",
        }
    if target_reached_at is not None and target_reached_at <= confirmation_at:
        return None, {
            "renewed_structure": True,
            "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
            "fresh_fvg": False,
            "reason": "destination-already-reached-before-renewal-confirmation",
        }

    fvg = _fresh_fvg(post_wait, side, confirmation_index)
    if fvg is None:
        return None, {
            "renewed_structure": True,
            "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
            "fresh_fvg": False,
            "reason": "no-fresh-fvg-after-renewal-confirmation",
        }
    fvg_index, zone_lower, zone_upper = fvg
    formed_at = cast(datetime, getattr(post_wait[fvg_index], "closed_at"))

    if invalidated_at is not None and invalidated_at <= formed_at:
        return None, {
            "renewed_structure": True,
            "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
            "fresh_fvg": True,
            "fresh_fvg_formed_at": formed_at.astimezone(UTC).isoformat(),
            "reason": "original-hypothesis-invalidated-before-fresh-fvg",
        }
    if target_reached_at is not None and target_reached_at <= formed_at:
        return None, {
            "renewed_structure": True,
            "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
            "fresh_fvg": True,
            "fresh_fvg_formed_at": formed_at.astimezone(UTC).isoformat(),
            "reason": "destination-already-reached-before-fresh-fvg",
        }

    entry = (zone_lower + zone_upper) / Decimal(2)
    stop = renewed_extreme
    risk = abs(entry - stop)
    if side == "short":
        valid = target < entry < stop
        three_r = entry - risk * Decimal(3)
    else:
        valid = stop < entry < target
        three_r = entry + risk * Decimal(3)
    if not valid or risk <= 0:
        return None, {
            "renewed_structure": True,
            "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
            "fresh_fvg": True,
            "fresh_fvg_formed_at": formed_at.astimezone(UTC).isoformat(),
            "reason": "invalid-renewed-entry-stop-target-geometry",
        }

    candidate = Vt31R22ExecutableSetup(
        side=source.side,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=three_r,
        selected_family=Vt31R22EntryFamily.FAIR_VALUE_GAP,
        candidate_families=(Vt31R22EntryFamily.FAIR_VALUE_GAP,),
        decision_at=formed_at,
        pending_expires_at=source.pending_expires_at,
        source_setup=source,
        execution_policy_fingerprint=POLICY_FINGERPRINT,
    )
    reference_width = source.reference.high - source.reference.low
    return candidate, {
        "renewed_structure": True,
        "renewed_confirmation_at": confirmation_at.astimezone(UTC).isoformat(),
        "renewed_extreme": format(renewed_extreme, "f"),
        "renewed_structural_level": format(structural_level, "f"),
        "fresh_fvg": True,
        "fresh_fvg_formed_at": formed_at.astimezone(UTC).isoformat(),
        "fvg_zone_lower": format(zone_lower, "f"),
        "fvg_zone_upper": format(zone_upper, "f"),
        "entry": format(entry, "f"),
        "stop": format(stop, "f"),
        "target": format(target, "f"),
        "risk_ref": format(risk / reference_width, "f"),
        "planned_target_r": format(abs(target - entry) / risk, "f"),
        "minutes_wait_to_confirmation": int(
            (confirmation_at - original.decision_at).total_seconds() // 60
        ),
        "minutes_wait_to_fvg": int(
            (formed_at - original.decision_at).total_seconds() // 60
        ),
        "reason": "renewed-local-structure-plus-fresh-fvg",
    }


def _economics(outcomes: list[dict[str, object]]) -> dict[str, object]:
    terminal = [
        {
            "r_multiple": cast(str, row["r_multiple"]),
            "signal_at": cast(str, row["signal_at"]),
        }
        for row in outcomes
        if row.get("status") == "terminal"
    ]
    return baseline._metrics(terminal, friction=FRICTION)


def run(
    market_state_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    state = json.loads(market_state_path.read_text())
    if state.get("schema") != SOURCE_SCHEMA:
        raise ValueError("unexpected Market State schema")
    contract = cast(dict[str, object], state["causal_contract"])
    if contract.get("date_level_outcome_lookup") is not False:
        raise ValueError("causal governance mismatch")

    series, account, evidence, checked, evidence_sha, provider = (
        baseline.load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("renewal forensics requires NAS100 evidence")

    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[baseline._day(getattr(bar, "opened_at"))].append(bar)

    stale_rows = [
        row
        for row in cast(list[dict[str, Any]], state["state_matrix"])
        if row.get("reclaim_latency_bin") == "8-14"
    ]
    statuses: Counter[str] = Counter()
    traces: list[dict[str, object]] = []
    outcomes: list[dict[str, object]] = []

    for row in stale_rows:
        local_day = __import__("datetime").date.fromisoformat(cast(str, row["local_date"]))
        day_bars = tuple(by_day.get(local_day, ()))
        signal_at = datetime.fromisoformat(cast(str, row["signal_at"]))
        reconstructed = _source_at_signal(day_bars, signal_at, evidence)
        if reconstructed is None:
            statuses["source-reconstruction-mismatch"] += 1
            traces.append(
                {
                    "local_date": row["local_date"],
                    "signal_at": row["signal_at"],
                    "status": "source-reconstruction-mismatch",
                }
            )
            continue
        source, original = reconstructed
        post_wait = tuple(
            bar
            for bar in day_bars
            if getattr(bar, "opened_at") >= original.decision_at
            and _local_minute(bar) < 11 * 60
        )
        candidate, telemetry = _renewal_candidate(post_wait, source, original)
        reason = cast(str, telemetry["reason"])
        statuses[reason] += 1
        trace: dict[str, object] = {
            "local_date": row["local_date"],
            "original_signal_at": row["signal_at"],
            "original_side": row["side"],
            "original_reclaim_latency_bin": row["reclaim_latency_bin"],
            "event_detector_uses_only_closed_bars_as_they_arrive": True,
            **telemetry,
        }
        if candidate is not None:
            outcome = baseline._simulate(day_bars, candidate)
            trace["renewal_outcome_status"] = outcome["status"]
            if outcome.get("status") == "terminal":
                trace["renewal_r_multiple"] = outcome["r_multiple"]
                trace["renewal_mfe_r"] = outcome["mfe_r"]
                trace["renewal_mae_r"] = outcome["mae_r"]
            outcomes.append(outcome)
        traces.append(trace)

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "partition": state["partition"],
        "research_only": True,
        "runtime_policy_selected": False,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "causal_governance": {
            "stale_state_is_predecision_market_state_v2_field": True,
            "renewal_events_observable_incrementally_from_closed_m1": True,
            "date_level_outcome_lookup": False,
            "future_outcome_used_by_event_detector": False,
            "outcome_simulation_is_research_label_only": True,
            "old_stale_entry_is_never_delayed_or_backfilled": True,
        },
        "renewal_hypothesis": {
            "wait_state": "reclaim_latency_bin=8-14",
            "require_original_hypothesis_not_invalidated": True,
            "require_destination_not_already_reached": True,
            "require_new_local_structure_after_wait": True,
            "require_fresh_same-side_fvg_after_new_structure": True,
            "entry": "fresh-fvg-consequent-encroachment",
            "stop": "renewed-local-structure-extreme",
            "target": "original-opposite-frozen-09-reference-boundary",
            "management": "baseline-3R-to-BE-for-forensics-only",
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "stale_source_rows": len(stale_rows),
        "status_counts": dict(sorted(statuses.items())),
        "renewal_candidate_count": len(outcomes),
        "renewal_terminal_economics": _economics(outcomes),
        "traces": traces,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-state", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.market_state, args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "stale_source_rows": payload["stale_source_rows"],
                "renewal_candidate_count": payload["renewal_candidate_count"],
                "status_counts": payload["status_counts"],
                "renewal_terminal_economics": payload["renewal_terminal_economics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
