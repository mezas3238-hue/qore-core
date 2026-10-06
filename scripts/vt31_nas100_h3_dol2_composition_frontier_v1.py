"""VT31 NAS100 H3 + DOL2 cognitive-protection composition frontier V1.

Consumed/burned evidence development only.

This frontier measures interaction rather than assuming additivity between:
- H3 full-cognition post-1R position management;
- soft-DOL1 FULL_COGNITION DOL2 extension;
- two-confirmation M1 structural protection after DOL1 acceptance.

Predeclared variants:
- DOL1_HARD_EXIT
- H3_ONLY
- W3_DOL2_PS2_ONLY
- W5_DOL2_PS2_ONLY
- H3_W3_DOL2_PS2
- H3_W5_DOL2_PS2

No sizing, leverage, compounding, capital weighting, fold identity, or future
outcome label may influence an action.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_dol2_cognitive_protection_frontier_v1 as dol2_protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as h3
import vt31_nas100_sovereign_r_management_frontier_v1 as r_frontier
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_target_depth_economic_frontier_v2 as depth

SCHEMA = "qore.vt31.nas100.h3_dol2_composition_frontier.v1"
WINDOWS = (3, 5)
HORIZON = 3
PS_CONFIRMATIONS = 2

ENTRY_DIAGNOSTIC_FIELDS = (
    "decision_minute_ny",
    "last_structure_event_family",
    "last_structure_event_age_minutes",
    "reference_reclaim_age_minutes",
    "sequence_stale_8_14",
    "current_path_vs_previous",
    "current_path_compressed",
    "reference_width_vs_prior5",
    "reference_volatility_state",
    "prior_day_state",
    "h4_state",
    "h1_state",
    "m15_state",
    "premarket_state",
    "cash_open_state",
    "position_in_prior_day_range",
    "raid_depth_ref",
    "recent_path_efficiency",
    "recent_overlap_rate",
    "risk_ref",
    "destination_distance_ref",
    "confirmation_latency_minutes",
    "entry_evidence_age_minutes",
    "management_context_state",
    "journey_capacity_state",
    "target_plan",
)
SEQUENCE_CONTEXT_FIELDS = (
    "entry_family",
    "side",
    "last_structure_event_family",
    "reference_volatility_state",
    "prior_day_state",
    "h1_state",
    "m15_state",
    "current_path_compressed",
    "sequence_stale_8_14",
    "position_in_prior_day_range",
    "management_context_state",
)
DIAGNOSTIC_VARIANTS = {
    "H3_W3_DOL2_PS2",
    "H3_W5_DOL2_PS2",
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _composite_name(window: int) -> str:
    return f"H3_W{window}_DOL2_PS2"


def _target_only_name(window: int) -> str:
    return f"W{window}_DOL2_PS2_ONLY"


def _attach_entry_context(
    row: dict[str, object],
    state: dict[str, object],
) -> dict[str, object]:
    row["entry_context"] = {
        key: state.get(key)
        for key in ENTRY_DIAGNOSTIC_FIELDS
    }
    return row


def _context_value(row: dict[str, object], field: str) -> str:
    if field in {"entry_family", "side"}:
        value = row.get(field)
    else:
        context = cast(dict[str, object], row.get("entry_context", {}))
        value = context.get(field)
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _context_counts(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    return {
        field: dict(
            sorted(
                Counter(_context_value(row, field) for row in rows).items()
            )
        )
        for field in SEQUENCE_CONTEXT_FIELDS
    }


def _context_outcome_attribution(
    rows: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for field in SEQUENCE_CONTEXT_FIELDS:
        grouped: dict[str, list[Decimal]] = {}
        for row in rows:
            key = _context_value(row, field)
            stressed = _d(row["r_multiple"]) - specialist.FRICTION
            grouped.setdefault(key, []).append(stressed)
        profiles = []
        for value, values in grouped.items():
            sample = len(values)
            losses = sum(item < 0 for item in values)
            total = sum(values, Decimal(0))
            profiles.append(
                {
                    "value": value,
                    "sample": sample,
                    "losses": losses,
                    "loss_rate": format(
                        Decimal(losses) / Decimal(sample),
                        "f",
                    ),
                    "mean_stressed_r": format(
                        total / Decimal(sample),
                        "f",
                    ),
                    "total_stressed_r": format(total, "f"),
                }
            )
        result[field] = sorted(
            profiles,
            key=lambda item: (
                _d(item["mean_stressed_r"]),
                -int(item["sample"]),
                str(item["value"]),
            ),
        )
    return result


def _sequence_diagnostics(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))

    streaks: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    for row in ordered:
        stressed = _d(row["r_multiple"]) - specialist.FRICTION
        if stressed < 0:
            current.append(row)
        elif current:
            streaks.append(current)
            current = []
    if current:
        streaks.append(current)

    longest = max(streaks, key=len, default=[])
    loss_rows = [
        row
        for row in ordered
        if _d(row["r_multiple"]) - specialist.FRICTION < 0
    ]

    def window(size: int) -> dict[str, object] | None:
        if len(ordered) < size:
            return None
        candidates = []
        for start in range(len(ordered) - size + 1):
            items = ordered[start : start + size]
            total = sum(
                (
                    _d(row["r_multiple"]) - specialist.FRICTION
                    for row in items
                ),
                Decimal(0),
            )
            candidates.append((total, items))
        total, items = min(candidates, key=lambda item: item[0])
        return {
            "size": size,
            "stressed_total_r": format(total, "f"),
            "start_signal_at": str(items[0]["signal_at"]),
            "end_signal_at": str(items[-1]["signal_at"]),
            "loss_count": sum(
                _d(row["r_multiple"]) - specialist.FRICTION < 0
                for row in items
            ),
            "context_counts": _context_counts(items),
        }

    loss_pairs = [
        (ordered[index - 1], ordered[index])
        for index in range(1, len(ordered))
        if _d(ordered[index - 1]["r_multiple"]) - specialist.FRICTION < 0
        and _d(ordered[index]["r_multiple"]) - specialist.FRICTION < 0
    ]
    transition_similarity = {}
    for field in SEQUENCE_CONTEXT_FIELDS:
        matches = sum(
            _context_value(left, field) == _context_value(right, field)
            for left, right in loss_pairs
        )
        transition_similarity[field] = {
            "loss_pair_count": len(loss_pairs),
            "same_context_count": matches,
            "same_context_rate": (
                None
                if not loss_pairs
                else format(
                    Decimal(matches) / Decimal(len(loss_pairs)),
                    "f",
                )
            ),
        }

    return {
        "observation_only": True,
        "action_authority": False,
        "outcome_labels_runtime_authority": False,
        "trade_count": len(ordered),
        "loss_count": len(loss_rows),
        "longest_losing_streak": {
            "length": len(longest),
            "start_signal_at": (
                None if not longest else str(longest[0]["signal_at"])
            ),
            "end_signal_at": (
                None if not longest else str(longest[-1]["signal_at"])
            ),
            "stressed_total_r": format(
                sum(
                    (
                        _d(row["r_multiple"]) - specialist.FRICTION
                        for row in longest
                    ),
                    Decimal(0),
                ),
                "f",
            ),
            "context_counts": _context_counts(longest),
        },
        "worst_rolling_5": window(5),
        "worst_rolling_10": window(10),
        "all_loss_context_counts": _context_counts(loss_rows),
        "consecutive_loss_context_similarity": transition_similarity,
        "context_outcome_attribution": _context_outcome_attribution(ordered),
    }


def _simulate_composite(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    window: int,
    pretarget_breaker_ps_confirmations: int | None = None,
    pretarget_breaker_ps_authorizer: (
        Callable[[object, Decimal, Decimal], bool] | None
    ) = None,
    pretarget_cognitive_exit_authorizer: (
        Callable[[object, Decimal], bool] | None
    ) = None,
) -> dict[str, object]:
    if pretarget_breaker_ps_confirmations not in {None, 1, 2}:
        raise ValueError(
            "pretarget_breaker_ps_confirmations must be None, 1, or 2"
        )

    side = str(getattr(getattr(executable, "side"), "value"))
    entry_family = str(
        getattr(getattr(executable, "selected_family"), "value")
    )
    entry = _d(getattr(executable, "entry_price"))
    initial_stop = _d(getattr(executable, "stop_price"))
    dol1 = _d(getattr(executable, "target_price"))
    risk = abs(entry - initial_stop)
    source = getattr(executable, "source_setup")
    width = _d(source.reference.high) - _d(source.reference.low)
    if risk <= 0 or width <= 0:
        return {"status": "censored-invalid-geometry"}

    direction = Decimal(1) if side == "long" else Decimal(-1)
    dol2 = dol1 + direction * width * Decimal("0.25")

    fill_index = v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return {"status": "no-fill"}
    eligible = tuple(
        bar
        for bar in day_bars[fill_index:]
        if specialist.baseline._local_minute(bar)
        < specialist.LIFECYCLE_MINUTE
    )
    if not eligible:
        return {"status": "censored-no-lifecycle"}

    first = eligible[0]
    if depth._stop_hit(side, first, initial_stop) or depth._target_hit(
        side, first, dol1
    ):
        return {"status": "censored-fill-bar-path"}

    one_r_index, one_r_status = h3.persistence._first_unambiguous_1r_touch(
        eligible,
        side=side,
        entry=entry,
        stop=initial_stop,
        risk=risk,
    )
    h3_observation_index = (
        None if one_r_index is None else one_r_index + HORIZON
    )

    current_stop = initial_stop
    pending_be = False
    be_armed = False
    pending_ps: Decimal | None = None
    ps_committed = False
    ps_confirmations = 0

    pending_breaker_ps: Decimal | None = None
    pending_cognitive_exit = False
    cognitive_exit_armed = False
    breaker_ps_committed = False
    breaker_ps_confirmations = 0
    breaker_ps_enabled = (
        entry_family == "breaker"
        and pretarget_breaker_ps_confirmations is not None
    )

    dol1_touch_index: int | None = None
    dol1_accepted_index: int | None = None
    extension_active = False
    extension_cognition_allowed = False
    extension_cognition_state = "NOT_EVALUATED"
    extension_persistence_state: str | None = None

    h3_persistence_state: str | None = None
    h3_action = "NONE"
    h3_reasoning_action: str | None = None
    h3_management_ready: bool | None = None
    h3_maximum_ready: bool | None = None

    previous = first
    filled_at = getattr(first, "closed_at")
    exit_price: Decimal | None = None
    exit_at = None
    exit_reason: str | None = None

    for index in range(1, len(eligible)):
        bar = eligible[index]
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        # A cognitive EXIT decided on the prior fully closed M1 executes only
        # at the next M1 open. This prevents same-bar hindsight.
        if pending_cognitive_exit:
            exit_price = _d(getattr(bar, "open"))
            exit_at = getattr(bar, "opened_at")
            exit_reason = "composite-pretarget-cognitive-exit"
            cognitive_exit_armed = True
            pending_cognitive_exit = False
            break

        # Actions decided on a prior closed M1 become active now.
        if pending_breaker_ps is not None and not breaker_ps_committed:
            active_target = dol2 if extension_active else dol1
            if dol2_protection.protection._improves_stop(
                side,
                current_stop,
                pending_breaker_ps,
                active_target,
            ):
                current_stop = pending_breaker_ps
                breaker_ps_committed = True
            pending_breaker_ps = None

        if pending_be and not be_armed:
            if dol2_protection.protection._improves_stop(
                side, current_stop, entry, dol2
            ):
                current_stop = entry
            be_armed = True
            pending_be = False

        if pending_ps is not None and not ps_committed:
            if dol2_protection.protection._improves_stop(
                side, current_stop, pending_ps, dol2
            ):
                current_stop = pending_ps
                ps_committed = True
            pending_ps = None

        if depth._stop_hit(side, bar, current_stop):
            exit_price = current_stop
            exit_at = getattr(bar, "closed_at")
            if ps_committed:
                exit_reason = "composite-protective-swing-stop"
            elif breaker_ps_committed:
                exit_reason = "composite-breaker-pretarget-protective-stop"
            elif be_armed:
                exit_reason = "composite-h3-breakeven"
            else:
                exit_reason = "structural-invalidation"
            break

        if extension_active and depth._target_hit(side, bar, dol2):
            exit_price = dol2
            exit_at = getattr(bar, "closed_at")
            exit_reason = "dol2-extended-target"
            break

        close = _d(getattr(bar, "close"))

        # H3 full cognition is allowed to act whether DOL1 has been touched or
        # not. It uses only the closed bars available through this observation.
        if (
            h3_observation_index is not None
            and index == h3_observation_index
            and h3_persistence_state is None
        ):
            post_touch = eligible[one_r_index + 1 : h3_observation_index + 1]
            closes_r = [
                h3._terminal_r(
                    side=side,
                    entry=entry,
                    price=_d(getattr(item, "close")),
                    risk=risk,
                )
                for item in post_touch
            ]
            h3_persistence_state = h3.persistence._persistence_state(closes_r)
            (
                _,
                current_reasoning,
                cognition,
                management_ready,
                maximum_ready,
            ) = h3._current_cognition(
                day_bars=day_bars,
                executable=executable,
                state=state,
                observation_at=getattr(bar, "closed_at"),
                persistence_state=h3_persistence_state,
                horizon=HORIZON,
            )
            h3_reasoning_action = current_reasoning.action
            h3_management_ready = management_ready
            h3_maximum_ready = maximum_ready

            if not management_ready:
                h3_action = "HOLD_BASELINE_CONTEXTUAL_MANAGEMENT_BLOCKED"
            elif h3_persistence_state in {
                "PERSISTENT_1R_FLOOR",
                "RECOVERED_1R_FLOOR",
            }:
                h3_action = "HOLD_RUNNER"
            elif h3_persistence_state == "ENTRY_OR_WORSE":
                exit_price = close
                exit_at = getattr(bar, "closed_at")
                exit_reason = "composite-h3-depleted-exit"
                h3_action = "EXIT_DEPLETED_AT_OBSERVATION_CLOSE"
                break
            elif (
                h3_persistence_state == "POSITIVE_BELOW_1R"
                and (
                    cognition.management_context
                    is h3.ManagementContext.CAUTIOUS
                    or cognition.destination_state == "SHALLOW"
                    or current_reasoning.action != "EXECUTE"
                )
            ):
                pending_be = True
                h3_action = "ARM_BE_NEXT_M1"
            else:
                h3_action = "HOLD_RUNNER"

        if (
            breaker_ps_enabled
            and not extension_active
            and not breaker_ps_committed
            and pending_breaker_ps is None
        ):
            candidate = dol2_protection.protection._protective_swing_level(
                eligible,
                index,
                side,
            )
            if candidate is not None and dol2_protection.protection._improves_stop(
                side,
                current_stop,
                candidate,
                dol1,
            ):
                breaker_ps_confirmations += 1
                if (
                    breaker_ps_confirmations
                    >= cast(int, pretarget_breaker_ps_confirmations)
                    and (
                        pretarget_breaker_ps_authorizer is None
                        or pretarget_breaker_ps_authorizer(
                            bar,
                            candidate,
                            current_stop,
                        )
                    )
                ):
                    pending_breaker_ps = candidate

        if extension_active:
            if not ps_committed and pending_ps is None:
                candidate = dol2_protection.protection._protective_swing_level(
                    eligible,
                    index,
                    side,
                )
                if candidate is not None and dol2_protection.protection._improves_stop(
                    side,
                    current_stop,
                    candidate,
                    dol2,
                ):
                    ps_confirmations += 1
                    if ps_confirmations >= PS_CONFIRMATIONS:
                        pending_ps = candidate
            continue

        # Soft DOL1: a touch is only a checkpoint, never acceptance.
        if dol1_touch_index is None:
            if depth._target_hit(side, bar, dol1):
                dol1_touch_index = index
            elif (
                pretarget_cognitive_exit_authorizer is not None
                and pretarget_cognitive_exit_authorizer(
                    bar,
                    current_stop,
                )
            ):
                pending_cognitive_exit = True
            continue

        if index <= dol1_touch_index:
            continue

        bars_after_touch = index - dol1_touch_index
        if depth._accepted(side, close, dol1):
            dol1_accepted_index = index
            (
                cognition,
                current_reasoning,
                extension_persistence_state,
                extension_cognition_state,
            ) = depth._acceptance_cognition(
                day_bars=day_bars,
                executable=executable,
                state=state,
                eligible=eligible,
                acceptance_index=index,
            )
            extension_cognition_allowed = depth._selector_allows(
                selector="FULL_COGNITION",
                target_name="DOL2",
                cognition=cognition,
                current_reasoning=current_reasoning,
                persistence_state=extension_persistence_state,
            )
            if extension_cognition_allowed:
                extension_active = True
                continue
            exit_price = close
            exit_at = getattr(bar, "closed_at")
            exit_reason = "accepted-dol1-cognition-bank"
            break

        if bars_after_touch >= window:
            exit_price = close
            exit_at = getattr(bar, "closed_at")
            exit_reason = "soft-dol1-acceptance-timeout"
            break

    if exit_price is None:
        final = eligible[-1]
        exit_price = _d(getattr(final, "close"))
        exit_at = getattr(final, "closed_at")
        exit_reason = "16:00-lifecycle"

    return {
        "status": "terminal",
        "local_date": specialist._day(
            getattr(executable, "decision_at")
        ).isoformat(),
        "side": side,
        "signal_at": getattr(executable, "decision_at").isoformat(),
        "filled_at": filled_at.isoformat(),
        "exit_at": exit_at.isoformat(),
        "entry_family": entry_family,
        "exit_reason": exit_reason,
        "r_multiple": format(
            depth._terminal_r(
                side=side,
                entry=entry,
                price=exit_price,
                risk=risk,
            ),
            "f",
        ),
        "h3_first_1r_touch_status": one_r_status,
        "h3_persistence_state": h3_persistence_state,
        "h3_action": h3_action,
        "h3_current_reasoning_action": h3_reasoning_action,
        "h3_management_ready": h3_management_ready,
        "h3_maximum_intelligence_ready": h3_maximum_ready,
        "soft_dol1_window_m1": window,
        "dol1_touched": dol1_touch_index is not None,
        "dol1_accepted": dol1_accepted_index is not None,
        "extension_activated": extension_active,
        "extension_cognition_allowed": extension_cognition_allowed,
        "extension_cognition_state": extension_cognition_state,
        "extension_persistence_state": extension_persistence_state,
        "ps_confirmations_seen": ps_confirmations,
        "ps_committed": ps_committed,
        "pretarget_breaker_ps_confirmations_required": (
            pretarget_breaker_ps_confirmations
        ),
        "pretarget_breaker_ps_confirmations_seen": (
            breaker_ps_confirmations
        ),
        "pretarget_breaker_ps_committed": breaker_ps_committed,
        "pretarget_cognitive_exit_armed": cognitive_exit_armed,
        "runtime_r_strategy_used": True,
        "runtime_volume_decision_authority": False,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    names = (
        "H3_ONLY",
        *(_target_only_name(w) for w in WINDOWS),
        *(_composite_name(w) for w in WINDOWS),
    )
    rows_by_variant: dict[str, list[dict[str, object]]] = {
        name: [] for name in names
    }

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        baseline = specialist._simulate_structural_boundary_only(
            day_bars, executable
        )
        if baseline.get("status") != "terminal":
            return baseline

        h3_only = h3._simulate(
            day_bars,
            executable,
            state,
            horizon=HORIZON,
        )
        if h3_only.get("status") != "terminal":
            raise AssertionError(
                f"H3_ONLY changed terminal eligibility: {h3_only}"
            )
        h3_only["target_plan"] = state["target_plan"]
        _attach_entry_context(h3_only, state)
        rows_by_variant["H3_ONLY"].append(h3_only)

        for window in WINDOWS:
            target_only = dol2_protection._simulate(
                day_bars,
                executable,
                state,
                window=window,
                confirmations_required=PS_CONFIRMATIONS,
            )
            if target_only.get("status") != "terminal":
                raise AssertionError(
                    f"{_target_only_name(window)} changed terminal eligibility: "
                    f"{target_only}"
                )
            target_only["target_plan"] = state["target_plan"]
            _attach_entry_context(target_only, state)
            rows_by_variant[_target_only_name(window)].append(target_only)

            composite = _simulate_composite(
                day_bars,
                executable,
                state,
                window=window,
            )
            if composite.get("status") != "terminal":
                raise AssertionError(
                    f"{_composite_name(window)} changed terminal eligibility: "
                    f"{composite}"
                )
            composite["target_plan"] = state["target_plan"]
            _attach_entry_context(composite, state)
            rows_by_variant[_composite_name(window)].append(composite)

        return baseline

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(list[dict[str, object]], base_payload["trades"])
    ids = [str(row["signal_at"]) for row in baseline]
    reports: dict[str, object] = {
        "DOL1_HARD_EXIT": {
            "trade_count": len(baseline),
            "stress_0_05r": base_payload["stress_0_05r"],
            "monte_carlo": base_payload["monte_carlo"],
            "halfyear_stress": base_payload["halfyear_stress"],
        }
    }

    for name, rows in rows_by_variant.items():
        if [str(row["signal_at"]) for row in rows] != ids:
            raise AssertionError(f"{name} changed sovereign terminal population")
        reports[name] = {
            "trade_count": len(rows),
            "stress_0_05r": specialist._metrics(
                rows,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": specialist._monte_carlo(rows),
            "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
            "winner_preservation_vs_dol1": r_frontier._winner_preservation(
                baseline,
                rows,
            ),
            "exit_reasons": dict(
                sorted(
                    Counter(str(row["exit_reason"]) for row in rows).items()
                )
            ),
            "extension_activated_count": sum(
                row.get("extension_activated") is True for row in rows
            ),
            "ps_committed_count": sum(
                row.get("ps_committed") is True
                or row.get("protection_committed") is True
                for row in rows
            ),
            "h3_action_counts": dict(
                sorted(
                    Counter(
                        str(
                            row.get(
                                "h3_action",
                                row.get("full_cognition_action", "NA"),
                            )
                        )
                        for row in rows
                    ).items()
                )
            ),
            "sequence_diagnostics": (
                _sequence_diagnostics(rows)
                if name in DIAGNOSTIC_VARIANTS
                else None
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": reports,
        "governance": {
            "h3_horizon_predeclared": HORIZON,
            "soft_dol1_windows_predeclared": list(WINDOWS),
            "dol2_target_predeclared": True,
            "protective_swing_confirmations_predeclared": PS_CONFIRMATIONS,
            "composition_measured_not_assumed": True,
            "same_sovereign_terminal_population": True,
            "entry_changed": False,
            "initial_stop_never_widened": True,
            "protection_effective_next_m1": True,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fold_identity_used_for_action": False,
            "future_outcome_used_for_action": False,
            "sequence_diagnostics_observation_only": True,
            "sequence_diagnostics_action_authority": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
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
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
