"""Cognitive journey-lock frontier for VT31 NAS100.

Architect B consumed-evidence research only.

The frontier keeps Silver Bullet, admission, entry, target and initial
invalidation frozen. It tests whole-position protection after a CLOSED M1 has
earned +1R. The new stop becomes effective only on the next M1.

Eligibility is restricted to pre-entry cognition signatures already found
negative across all four consumed folds. No sizing, partial execution, leverage,
capital weighting, fold identity or future label participates in runtime logic.
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

import vt31_nas100_cognitive_structural_protection_frontier_v1 as ps
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
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

SCHEMA = "qore.vt31.nas100.cognitive_journey_lock_frontier.v1"
MARKET = "NAS100"
CHECKPOINT_R = Decimal("1.00")

VARIANTS = {
    "BASELINE": None,
    "LBB_PATH_SHALLOW_PS1": ("PS1_LBB_PATH_SHALLOW", None),
    "BREAKER_SHALLOW_BE100": ("LOCK_BREAKER_SHALLOW", Decimal("0.00")),
    "BREAKER_SHALLOW_LOCK025_100": (
        "LOCK_BREAKER_SHALLOW",
        Decimal("0.25"),
    ),
    "LBB_PATH_SHALLOW_LOCK025_100": (
        "LOCK_LBB_PATH_SHALLOW",
        Decimal("0.25"),
    ),
    "LBB_PATH_LOCK025_100": (
        "LOCK_LBB_PATH",
        Decimal("0.25"),
    ),
}

PATH_NOT_COMPRESSED = (
    "REASONING_CONTRADICTION:"
    "SITUATION:CURRENT_PATH_NOT_COMPRESSED"
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touch_stop(bar: object, *, side: str, level: Decimal) -> bool:
    low = _d(getattr(bar, "low"))
    high = _d(getattr(bar, "high"))
    return low <= level if side == "long" else high >= level


def _touch_target(bar: object, *, side: str, level: Decimal) -> bool:
    low = _d(getattr(bar, "low"))
    high = _d(getattr(bar, "high"))
    return high >= level if side == "long" else low <= level


def _stop_r(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    stop: Decimal,
) -> Decimal:
    if side == "long":
        return (stop - entry) / risk
    return (entry - stop) / risk


def _close_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    close = _d(getattr(bar, "close"))
    if side == "long":
        return (close - entry) / risk
    return (entry - close) / risk


def _protective_fill_r(
    bar: object,
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    protective_level: Decimal,
    lock_r: Decimal,
) -> Decimal:
    opened = _d(getattr(bar, "open"))
    if side == "long" and opened < protective_level:
        return (opened - entry) / risk
    if side == "short" and opened > protective_level:
        return (entry - opened) / risk
    return lock_r


def _selector(
    *,
    mode: str,
    state: dict[str, object],
    cognition: FullCognitivePositionState,
    entry_family: str,
) -> bool:
    path_not_compressed = PATH_NOT_COMPRESSED in cognition.signal_codes
    last_breaker = state["last_structure_event_family"] == "breaker"
    shallow = cognition.destination_state == "SHALLOW"

    if mode == "LOCK_BREAKER_SHALLOW":
        return entry_family == "breaker" and shallow
    if mode == "LOCK_LBB_PATH_SHALLOW":
        return last_breaker and path_not_compressed and shallow
    if mode == "LOCK_LBB_PATH":
        return last_breaker and path_not_compressed
    if mode == "PS1_LBB_PATH_SHALLOW":
        return last_breaker and path_not_compressed and shallow
    raise ValueError(f"unsupported cognitive journey mode={mode}")


def _simulate_lock(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    *,
    lock_r: Decimal,
) -> dict[str, object]:
    side = setup.side.value
    entry = setup.entry_price
    initial_stop = setup.stop_price
    target = setup.target_price
    three_r = setup.three_r_price
    risk = setup.initial_risk
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = v2b._fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    if _touch_stop(first, side=side, level=initial_stop) or _touch_target(
        first,
        side=side,
        level=target,
    ):
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    journey_lock_armed = False
    journey_lock_checkpoint_at: datetime | None = None
    baseline_be_armed = False
    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
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

        hit_stop = _touch_stop(
            bar,
            side=side,
            level=current_stop,
        )
        hit_target = _touch_target(
            bar,
            side=side,
            level=target,
        )
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            if current_stop != initial_stop:
                terminal = _protective_fill_r(
                    bar,
                    side=side,
                    entry=entry,
                    risk=risk,
                    protective_level=current_stop,
                    lock_r=_stop_r(
                        side=side,
                        entry=entry,
                        risk=risk,
                        stop=current_stop,
                    ),
                )
            else:
                terminal = Decimal("-1")
            exit_reason = (
                "journey-lock-stop"
                if journey_lock_armed
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

        # A closed M1 earns the checkpoint. Protection is effective next M1.
        if not journey_lock_armed:
            close_r = _close_r(
                bar,
                side=side,
                entry=entry,
                risk=risk,
            )
            if close_r >= CHECKPOINT_R:
                protective_level = (
                    entry + risk * lock_r
                    if side == "long"
                    else entry - risk * lock_r
                )
                if protection._improves_stop(
                    side,
                    current_stop,
                    protective_level,
                    target,
                ):
                    current_stop = protective_level
                    journey_lock_armed = True
                    journey_lock_checkpoint_at = cast(
                        datetime,
                        getattr(bar, "closed_at"),
                    )

        # Preserve the baseline 3R breakeven mechanism.
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
        terminal = _close_r(
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
        "journey_lock_armed": journey_lock_armed,
        "journey_lock_checkpoint_at": (
            None
            if journey_lock_checkpoint_at is None
            else journey_lock_checkpoint_at.astimezone(UTC).isoformat()
        ),
        "journey_lock_r": format(lock_r, "f"),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("cognitive journey lock requires NAS100")

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
    status: Counter[str] = Counter()
    eligible_counts: Counter[str] = Counter()
    armed_counts: Counter[str] = Counter()
    trades: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
    }

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
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status[f"oco-{selection_status}"] += 1
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
        if situation.fingerprint() != state["situation_fingerprint"]:
            raise AssertionError("journey-lock situation fingerprint drift")
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognitive_state = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )
        entry_family = selected.selected_family.value
        trade_id = ps._trade_id(
            local_day=local_day,
            selected=selected,
        )

        for variant, spec in VARIANTS.items():
            eligible = False
            if spec is None:
                outcome = specialist.baseline._simulate(
                    day_bars,
                    selected,
                )
            else:
                mode, lock_r = spec
                eligible = _selector(
                    mode=mode,
                    state=state,
                    cognition=cognitive_state,
                    entry_family=entry_family,
                )
                if eligible:
                    eligible_counts[variant] += 1
                if mode == "PS1_LBB_PATH_SHALLOW":
                    outcome = protection._simulate_single_structural_trail(
                        day_bars,
                        selected,
                        required_confirmations=(1 if eligible else None),
                    )
                elif eligible:
                    assert lock_r is not None
                    outcome = _simulate_lock(
                        day_bars,
                        selected,
                        lock_r=lock_r,
                    )
                else:
                    outcome = specialist.baseline._simulate(
                        day_bars,
                        selected,
                    )

            status[f"{variant}:{outcome['status']}"] += 1
            if outcome["status"] != "terminal":
                continue
            enriched = dict(outcome)
            enriched["trade_id"] = trade_id
            enriched["cognitive_eligible"] = eligible
            enriched["destination_state"] = (
                cognitive_state.destination_state
            )
            enriched["last_structure_event_family"] = state[
                "last_structure_event_family"
            ]
            enriched["path_not_compressed"] = (
                PATH_NOT_COMPRESSED in cognitive_state.signal_codes
            )
            trades[variant].append(enriched)
            if bool(outcome.get("journey_lock_armed")):
                armed_counts[variant] += 1
            if bool(outcome.get("structural_trail_armed")):
                armed_counts[variant] += 1

    baseline = trades["BASELINE"]
    variants: dict[str, object] = {}
    for variant, rows in trades.items():
        variants[variant] = {
            "terminal_count": len(rows),
            "cognitive_eligible_count": eligible_counts[variant],
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
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variants": variants,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "target_changed": False,
            "initial_stop_changed": False,
            "journey_checkpoint_closed_m1_only": True,
            "journey_protection_effective_next_m1": True,
            "whole_position_stop_management": True,
            "partial_exit_required": False,
            "absolute_volume_used": False,
            "provider_volume_rule_used": False,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
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
                "checkpoint_r": payload["checkpoint_r"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
