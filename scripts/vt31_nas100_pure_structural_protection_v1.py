"""VT31 NAS100 pure structural-protection frontier V1.

Revalidates the Architect-B LBB_PATH_SHALLOW_PS1 mechanism under the Owner
sovereign rule that R is evaluation-only.

No runtime R threshold exists in either variant.

Variants:
- PURE_MARKET_BASELINE: structural invalidation / structural target / lifecycle.
- LBB_PATH_SHALLOW_PS1_PURE: same baseline plus one confirmed M1 protective
  swing, effective on the next M1 bar, only for the pre-entry cognition state:
  last structure=breaker AND CURRENT_PATH_NOT_COMPRESSED AND destination=SHALLOW.

The protective swing is market geometry, not an R threshold.
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

import vt31_nas100_cognitive_structural_protection_frontier_v1 as cognitive
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_high_density_structural_protection_v1 as legacy_protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_pure_market_exit_baseline_v1 as pure_base
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    assess_full_cognitive_position,
)

SCHEMA = "qore.vt31.nas100.pure_structural_protection.v1"
MARKET = "NAS100"
VARIANTS = ("PURE_MARKET_BASELINE", "LBB_PATH_SHALLOW_PS1_PURE")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _survivor_eligible(
    *,
    state: dict[str, object],
    cognition: FullCognitivePositionState,
) -> bool:
    return bool(
        state["last_structure_event_family"] == "breaker"
        and cognitive._is_path_not_compressed(cognition)
        and cognition.destination_state == "SHALLOW"
    )


def _simulate_one_structural_move(
    day_bars: tuple[object, ...],
    setup: object,
    *,
    eligible: bool,
) -> dict[str, object]:
    if not eligible:
        result = pure_base._pure_market_simulate(day_bars, setup)
        result["structural_protection_armed"] = False
        result["runtime_r_thresholds_consulted"] = False
        return result

    side = str(getattr(getattr(setup, "side"), "value"))
    entry = _d(getattr(setup, "entry_price"))
    initial_stop = _d(getattr(setup, "stop_price"))
    target = _d(getattr(setup, "target_price"))
    risk_points = abs(entry - initial_stop)
    if risk_points <= 0:
        return {"status": "censored-invalid-geometry"}

    fill_index = v2b._fill_index(day_bars, setup)
    if fill_index is None:
        return {"status": "no-fill"}

    first = day_bars[fill_index]
    low = _d(getattr(first, "low"))
    high = _d(getattr(first, "high"))
    hit_stop = low <= initial_stop if side == "long" else high >= initial_stop
    hit_target = high >= target if side == "long" else low <= target
    if hit_stop or hit_target:
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    pending_stop: Decimal | None = None
    structural_move_committed = False
    previous = first
    filled_at = cast(datetime, getattr(first, "closed_at"))
    exit_price: Decimal | None = None
    exit_at: datetime | None = None
    exit_reason: str | None = None
    post_fill = tuple(day_bars[fill_index:])

    for local_index in range(1, len(post_fill)):
        bar = post_fill[local_index]
        if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        # A swing confirmed by the previous closed M1 becomes active now.
        if pending_stop is not None and not structural_move_committed:
            if legacy_protection._improves_stop(
                side,
                current_stop,
                pending_stop,
                target,
            ):
                current_stop = pending_stop
                structural_move_committed = True
            pending_stop = None

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            return {"status": "censored-same-bar-stop-target"}
        if hit_stop:
            exit_price = current_stop
            exit_reason = (
                "structural-protection-stop"
                if structural_move_committed
                else "structural-invalidation"
            )
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break
        if hit_target:
            exit_price = target
            exit_reason = "structural-target"
            exit_at = cast(datetime, getattr(bar, "closed_at"))
            break

        if not structural_move_committed and pending_stop is None:
            candidate = legacy_protection._protective_swing_level(
                post_fill,
                local_index,
                side,
            )
            if candidate is not None and legacy_protection._improves_stop(
                side,
                current_stop,
                candidate,
                target,
            ):
                pending_stop = candidate

    if exit_price is None:
        eligible_bars = [
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar)
            < specialist.LIFECYCLE_MINUTE
        ]
        if not eligible_bars:
            return {"status": "censored-no-lifecycle-close"}
        final = eligible_bars[-1]
        exit_price = _d(getattr(final, "close"))
        exit_reason = "16:00-lifecycle"
        exit_at = cast(datetime, getattr(final, "closed_at"))

    r_multiple = pure_base._terminal_r(
        side=side,
        entry=entry,
        price=exit_price,
        risk=risk_points,
    )
    return {
        "status": "terminal",
        "local_date": _day(getattr(setup, "decision_at")).isoformat(),
        "side": side,
        "signal_at": cast(datetime, getattr(setup, "decision_at"))
        .astimezone(UTC)
        .isoformat(),
        "filled_at": filled_at.astimezone(UTC).isoformat(),
        "exit_at": cast(datetime, exit_at).astimezone(UTC).isoformat(),
        "entry_family": str(getattr(getattr(setup, "selected_family"), "value")),
        "entry": format(entry, "f"),
        "initial_stop": format(initial_stop, "f"),
        "final_stop": format(current_stop, "f"),
        "structural_target": format(target, "f"),
        "exit_price": format(exit_price, "f"),
        "exit_reason": exit_reason,
        "r_multiple": format(r_multiple, "f"),
        "structural_protection_armed": structural_move_committed,
        "runtime_r_thresholds_consulted": False,
    }


def _halfyear(local_date: str) -> str:
    year, month = (int(value) for value in local_date.split("-")[:2])
    return f"{year}H{1 if month <= 6 else 2}"


def _group_metrics(
    rows: list[dict[str, object]],
    *,
    key: str,
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        value = (
            _halfyear(str(row["local_date"]))
            if key == "halfyear"
            else str(row[key])
        )
        grouped[value].append(row)
    return {
        name: cognitive._normalized_metrics(items)
        for name, items in sorted(grouped.items())
    }


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("pure structural protection requires NAS100")

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
    status: Counter[str] = Counter()
    survivor_eligible_count = 0

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue
        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status["no-source-timeline"] += 1
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
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognition = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )
        eligible = _survivor_eligible(state=state, cognition=cognition)
        survivor_eligible_count += int(eligible)

        baseline = pure_base._pure_market_simulate(day_bars, selected)
        managed = _simulate_one_structural_move(
            day_bars,
            selected,
            eligible=eligible,
        )
        trade_id = cognitive._trade_id(
            local_day=local_day,
            selected=selected,
        )

        for variant, outcome in (
            ("PURE_MARKET_BASELINE", baseline),
            ("LBB_PATH_SHALLOW_PS1_PURE", managed),
        ):
            status[f"{variant}:{outcome['status']}"] += 1
            if outcome["status"] != "terminal":
                continue
            row = dict(outcome)
            row["trade_id"] = trade_id
            row["partition"] = partition
            row["management_context"] = cognition.management_context.value
            row["destination_state"] = cognition.destination_state
            row["survivor_eligible"] = eligible
            trades[variant].append(row)

    baseline_rows = trades["PURE_MARKET_BASELINE"]
    reports: dict[str, object] = {}
    for variant, rows in trades.items():
        reports[variant] = {
            "terminal_count": len(rows),
            "normalized_metrics": cognitive._normalized_metrics(rows),
            "monte_carlo": specialist._monte_carlo(rows),
            "winner_preservation_vs_pure_baseline": (
                None
                if variant == "PURE_MARKET_BASELINE"
                else cognitive._winner_preservation(
                    baseline_rows,
                    rows,
                )
            ),
            "side_metrics": _group_metrics(rows, key="side"),
            "halfyear_metrics": _group_metrics(rows, key="halfyear"),
            "entry_family_metrics": _group_metrics(
                rows,
                key="entry_family",
            ),
            "armed_count": sum(
                row.get("structural_protection_armed") is True
                for row in rows
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
        "partition": partition,
        "market": MARKET,
        "survivor_identity": "LBB_PATH_SHALLOW_PS1",
        "survivor_eligible_count": survivor_eligible_count,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variant_reports": reports,
        "status_counts": dict(sorted(status.items())),
        "runtime_governance": {
            "r_used_for_admission": False,
            "r_used_for_entry": False,
            "r_used_for_invalidation": False,
            "r_used_for_stop_movement": False,
            "r_used_for_breakeven": False,
            "r_used_for_target": False,
            "r_used_for_exit": False,
            "r_used_for_trailing": False,
            "r_used_for_partials": False,
            "r_used_for_volume": False,
            "sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "volume_agnostic": True,
            "r_role": "post_trade_evaluation_only",
        },
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "protection_source": "confirmed-M1-protective-swing",
            "protection_effective_next_bar": True,
            "maximum_structural_protection_moves": 1,
            "runtime_r_thresholds_used": False,
            "normalized_equal_r_economics": True,
            "absolute_volume_used": False,
            "partial_exit_required": False,
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
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "survivor_eligible_count": payload["survivor_eligible_count"],
                "variant_reports": payload["variant_reports"],
                "runtime_governance": payload["runtime_governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
