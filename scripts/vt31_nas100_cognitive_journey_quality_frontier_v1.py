"""Journey-quality frontier for VT31 NAS100 Architect B.

Combines the 4/4 development survivor
LAST_BREAKER + PATH_NOT_COMPRESSED + SHALLOW -> PS1
with an orthogonal whole-position +0.25R lock for other admitted Breaker
SHALLOW trades only after a closed M1 earns +1R.

The lock may additionally require checkpoint overlap < 0.25, a causal journey
quality hypothesis already present in prior VT31 research.

No entry filtering, sizing, partial exits, capital weighting or absolute volume.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_cognitive_journey_lock_frontier_v1 as lock
import vt31_nas100_cognitive_structural_protection_frontier_v1 as ps
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_ny_journey_bifurcation_forensics_v1 as journey
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    assess_full_cognitive_position,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
)

SCHEMA = "qore.vt31.nas100.cognitive_journey_quality_frontier.v1"
MARKET = "NAS100"
CHECKPOINT_R = Decimal("1.00")
LOCK_R = Decimal("0.25")
OVERLAP_THRESHOLD = Decimal("0.25")

VARIANTS = (
    "BASELINE",
    "SURVIVOR_PS1",
    "SURVIVOR_PLUS_BREAKER_SHALLOW_ALL_LOCK025",
    "SURVIVOR_PLUS_BREAKER_SHALLOW_OVERLAP_LT025_LOCK025",
)

PATH_NOT_COMPRESSED = (
    "REASONING_CONTRADICTION:"
    "SITUATION:CURRENT_PATH_NOT_COMPRESSED"
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _survivor_eligible(
    *,
    state: dict[str, object],
    cognition: FullCognitivePositionState,
) -> bool:
    return bool(
        state["last_structure_event_family"] == "breaker"
        and PATH_NOT_COMPRESSED in cognition.signal_codes
        and cognition.destination_state == "SHALLOW"
    )


def _breaker_shallow(
    *,
    entry_family: str,
    cognition: FullCognitivePositionState,
) -> bool:
    return (
        entry_family == "breaker"
        and cognition.destination_state == "SHALLOW"
    )


def _simulate_quality_lock(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    *,
    require_low_overlap: bool,
) -> dict[str, object]:
    side = setup.side.value
    entry = setup.entry_price
    initial_stop = setup.stop_price
    target = setup.target_price
    three_r = setup.three_r_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = __import__(
        "vt31_nas100_intelligence_policy_lab_v2b"
    )._fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    if lock._touch_stop(first, side=side, level=initial_stop) or lock._touch_target(
        first,
        side=side,
        level=target,
    ):
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    baseline_be_armed = False
    lock_armed = False
    checkpoint_seen = False
    checkpoint_overlap: Decimal | None = None
    checkpoint_efficiency: Decimal | None = None
    checkpoint_body_ratio: Decimal | None = None
    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
    observed: list[object] = []
    terminal: Decimal | None = None
    exit_reason: str | None = None
    exit_at: datetime | None = None

    for bar in day_bars[fill_index + 1 :]:
        if (
            specialist.baseline._local_minute(bar)
            >= specialist.LIFECYCLE_MINUTE
        ):
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        hit_stop = lock._touch_stop(
            bar,
            side=side,
            level=current_stop,
        )
        hit_target = lock._touch_target(
            bar,
            side=side,
            level=target,
        )
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            if current_stop != initial_stop:
                terminal = lock._protective_fill_r(
                    bar,
                    side=side,
                    entry=entry,
                    risk=risk,
                    protective_level=current_stop,
                    lock_r=lock._stop_r(
                        side=side,
                        entry=entry,
                        risk=risk,
                        stop=current_stop,
                    ),
                )
            else:
                terminal = Decimal("-1")
            exit_reason = (
                "journey-quality-lock-stop"
                if lock_armed
                else (
                    "breakeven-stop"
                    if current_stop == entry
                    else "initial-stop"
                )
            )
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            terminal = abs(target - entry) / risk
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        observed.append(bar)

        if not checkpoint_seen:
            close_r = journey._favorable_close_r(
                bar,
                side=side,
                entry=entry,
                risk=risk,
            )
            if close_r >= CHECKPOINT_R:
                checkpoint_seen = True
                checkpoint_overlap = journey._overlap_rate(tuple(observed))
                checkpoint_efficiency = journey._path_efficiency(
                    tuple(observed),
                    side=side,
                    entry=entry,
                )
                checkpoint_body_ratio = journey._directional_body_ratio(
                    tuple(observed),
                    side=side,
                )
                low_overlap = checkpoint_overlap < OVERLAP_THRESHOLD
                if (not require_low_overlap) or low_overlap:
                    protective_level = (
                        entry + risk * LOCK_R
                        if side == "long"
                        else entry - risk * LOCK_R
                    )
                    if protection._improves_stop(
                        side,
                        current_stop,
                        protective_level,
                        target,
                    ):
                        current_stop = protective_level
                        lock_armed = True

        if not baseline_be_armed:
            high = _d(getattr(bar, "high"))
            low = _d(getattr(bar, "low"))
            touched_three_r = (
                high >= three_r if side == "long" else low <= three_r
            )
            if touched_three_r:
                baseline_be_armed = True
                if protection._improves_stop(
                    side,
                    current_stop,
                    entry,
                    target,
                ):
                    current_stop = entry

    if terminal is None:
        eligible = [
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar)
            < specialist.LIFECYCLE_MINUTE
        ]
        if not eligible:
            return {"status": "censored-no-lifecycle-close"}
        final = eligible[-1]
        terminal = lock._close_r(
            final,
            side=side,
            entry=entry,
            risk=risk,
        )
        exit_reason = "16:00-lifecycle"
        exit_at = cast(datetime, getattr(final, "closed_at"))

    return {
        "status": "terminal",
        "local_date": _day(setup.decision_at).isoformat(),
        "side": side,
        "signal_at": setup.decision_at.astimezone(UTC).isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": cast(datetime, exit_at).astimezone(UTC).isoformat(),
        "entry_family": setup.selected_family.value,
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "checkpoint_seen": checkpoint_seen,
        "checkpoint_overlap": (
            None
            if checkpoint_overlap is None
            else format(checkpoint_overlap, "f")
        ),
        "checkpoint_path_efficiency": (
            None
            if checkpoint_efficiency is None
            else format(checkpoint_efficiency, "f")
        ),
        "checkpoint_directional_body_ratio": (
            None
            if checkpoint_body_ratio is None
            else format(checkpoint_body_ratio, "f")
        ),
        "journey_quality_lock_armed": lock_armed,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("journey-quality frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = oco.Vt31R22ExecutionPolicy()
    trades: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }
    eligible_counts: Counter[str] = Counter()
    armed_counts: Counter[str] = Counter()
    checkpoint_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            continue
        selected, _ = oco._select_oco(day_bars, timeline, policy)
        if selected is None:
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = selected.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            timeline.source,
            selected,
            observation_at,
        )
        situation = cognition_lab._reconstruct_situation(
            state=state,
            selected=selected,
            source=timeline.source,
            observation_at=observation_at,
        )
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognition = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )
        survivor = _survivor_eligible(
            state=state,
            cognition=cognition,
        )
        breaker_shallow = _breaker_shallow(
            entry_family=selected.selected_family.value,
            cognition=cognition,
        )
        trade_id = ps._trade_id(
            local_day=local_day,
            selected=selected,
        )

        for variant in VARIANTS:
            if variant == "BASELINE":
                outcome = specialist.baseline._simulate(
                    day_bars,
                    selected,
                )
            elif survivor:
                eligible_counts[variant] += 1
                outcome = protection._simulate_single_structural_trail(
                    day_bars,
                    selected,
                    required_confirmations=1,
                )
            elif (
                variant
                in {
                    "SURVIVOR_PLUS_BREAKER_SHALLOW_ALL_LOCK025",
                    "SURVIVOR_PLUS_BREAKER_SHALLOW_OVERLAP_LT025_LOCK025",
                }
                and breaker_shallow
            ):
                eligible_counts[variant] += 1
                outcome = _simulate_quality_lock(
                    day_bars,
                    selected,
                    require_low_overlap=(
                        variant.endswith("OVERLAP_LT025_LOCK025")
                    ),
                )
            else:
                outcome = specialist.baseline._simulate(
                    day_bars,
                    selected,
                )

            if outcome["status"] != "terminal":
                continue
            row = dict(outcome)
            row["trade_id"] = trade_id
            row["survivor_eligible"] = survivor
            row["breaker_shallow"] = breaker_shallow
            trades[variant].append(row)
            if bool(outcome.get("structural_trail_armed")):
                armed_counts[variant] += 1
            if bool(outcome.get("journey_quality_lock_armed")):
                armed_counts[variant] += 1
            if bool(outcome.get("checkpoint_seen")):
                checkpoint_counts[variant] += 1

    baseline = trades["BASELINE"]
    metrics: dict[str, object] = {}
    for variant, rows in trades.items():
        metrics[variant] = {
            "terminal_count": len(rows),
            "cognitive_eligible_count": eligible_counts[variant],
            "checkpoint_seen_count": checkpoint_counts[variant],
            "protection_armed_count": armed_counts[variant],
            "normalized_metrics": ps._normalized_metrics(rows),
            "monte_carlo": specialist._monte_carlo(rows),
            "winner_preservation_vs_baseline": ps._winner_preservation(
                baseline,
                rows,
            ),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"]) for row in rows
                    ).items()
                )
            ),
        }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "checkpoint_r": format(CHECKPOINT_R, "f"),
        "lock_r": format(LOCK_R, "f"),
        "overlap_threshold": format(OVERLAP_THRESHOLD, "f"),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variants": metrics,
        "governance": {
            "consumed_evidence_only": True,
            "development_frontier_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "target_changed": False,
            "initial_stop_changed": False,
            "survivor_ps1_predeclared": True,
            "overlap_lt025_hypothesis_preexisting": True,
            "checkpoint_uses_closed_m1_only": True,
            "protection_effective_next_m1": True,
            "whole_position_stop_management": True,
            "partial_exit_required": False,
            "absolute_volume_used": False,
            "normalized_equal_r_economics": True,
            "capital_weighting_used": False,
            "position_sizing_used": False,
            "fold_identity_runtime_input": False,
            "terminal_pnl_runtime_input": False,
            "future_journey_runtime_input": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variants": payload["variants"],
                "overlap_threshold": payload["overlap_threshold"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
