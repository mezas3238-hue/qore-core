"""Cognitive structural-protection frontier for VT31 NAS100.

Architect B research only. Trade admission, entry and structural destination are
frozen. The frontier applies at most one confirmed M1 protective-swing stop
improvement to already-admitted trades whose *pre-entry* full-cognition state
matches signatures that were negative in all four consumed folds.

No entry is filtered. No sizing, leverage, capital weighting, absolute volume
or partial-exit assumption is used.
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

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    assess_full_cognitive_position,
)

SCHEMA = "qore.vt31.nas100.cognitive_structural_protection_frontier.v1"
MARKET = "NAS100"
VARIANTS = (
    "BASELINE",
    "BREAKER_NONDEEP_PS1",
    "LAST_BREAKER_BREAKER_PS1",
    "PATH_NOT_COMPRESSED_PS1",
    "NEGATIVE_UNION_PS1",
    "NEGATIVE_UNION_PS2",
)
PATH_NOT_COMPRESSED = (
    "REASONING_CONTRADICTION:"
    "SITUATION:CURRENT_PATH_NOT_COMPRESSED"
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _is_breaker_nondeep(
    *,
    entry_family: str,
    cognition: FullCognitivePositionState,
) -> bool:
    return (
        entry_family == "breaker"
        and cognition.destination_state in {"NEUTRAL", "SHALLOW"}
    )


def _is_last_breaker_breaker(
    *,
    entry_family: str,
    state: dict[str, object],
) -> bool:
    return (
        entry_family == "breaker"
        and state["last_structure_event_family"] == "breaker"
    )


def _is_path_not_compressed(
    cognition: FullCognitivePositionState,
) -> bool:
    return PATH_NOT_COMPRESSED in cognition.signal_codes


def _required_confirmations(
    *,
    variant: str,
    entry_family: str,
    state: dict[str, object],
    cognition: FullCognitivePositionState,
) -> int | None:
    if variant == "BASELINE":
        return None

    breaker_nondeep = _is_breaker_nondeep(
        entry_family=entry_family,
        cognition=cognition,
    )
    last_breaker_breaker = _is_last_breaker_breaker(
        entry_family=entry_family,
        state=state,
    )
    path_not_compressed = _is_path_not_compressed(cognition)

    if variant == "BREAKER_NONDEEP_PS1":
        return 1 if breaker_nondeep else None
    if variant == "LAST_BREAKER_BREAKER_PS1":
        return 1 if last_breaker_breaker else None
    if variant == "PATH_NOT_COMPRESSED_PS1":
        return 1 if path_not_compressed else None
    if variant == "NEGATIVE_UNION_PS1":
        return (
            1
            if (
                breaker_nondeep
                or last_breaker_breaker
                or path_not_compressed
            )
            else None
        )
    if variant == "NEGATIVE_UNION_PS2":
        return (
            2
            if (
                breaker_nondeep
                or last_breaker_breaker
                or path_not_compressed
            )
            else None
        )
    raise ValueError(variant)


def _normalized_metrics(
    trades: list[dict[str, object]],
) -> dict[str, object]:
    values = [
        _d(trade["r_multiple"]) - specialist.FRICTION
        for trade in trades
    ]
    return cognition_lab._metrics(values)


def _trade_id(
    *,
    local_day: date,
    selected: object,
) -> str:
    return "|".join(
        (
            local_day.isoformat(),
            cast(datetime, getattr(selected, "decision_at"))
            .astimezone(UTC)
            .isoformat(),
            str(getattr(getattr(selected, "side"), "value")),
            str(
                getattr(
                    getattr(selected, "selected_family"),
                    "value",
                )
            ),
        )
    )


def _winner_preservation(
    baseline: list[dict[str, object]],
    variant: list[dict[str, object]],
) -> dict[str, object]:
    base = {
        str(row["trade_id"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in baseline
    }
    candidate = {
        str(row["trade_id"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in variant
    }
    baseline_winners = {
        key: value for key, value in base.items() if value > 0
    }
    if not baseline_winners:
        return {
            "baseline_winner_count": 0,
            "winner_count_preservation": None,
            "winner_r_preservation": None,
            "terminal_sample_preservation": (
                Decimal(len(candidate)) / Decimal(len(base))
                if base
                else None
            ),
        }

    preserved_count = sum(
        key in candidate and candidate[key] > 0
        for key in baseline_winners
    )
    baseline_winner_r = sum(
        baseline_winners.values(),
        Decimal(0),
    )
    candidate_winner_r = sum(
        (
            max(candidate.get(key, Decimal(0)), Decimal(0))
            for key in baseline_winners
        ),
        Decimal(0),
    )
    return {
        "baseline_winner_count": len(baseline_winners),
        "winner_count_preservation": format(
            Decimal(preserved_count)
            / Decimal(len(baseline_winners)),
            "f",
        ),
        "winner_r_preservation": format(
            candidate_winner_r / baseline_winner_r,
            "f",
        ),
        "terminal_sample_preservation": (
            format(
                Decimal(len(candidate)) / Decimal(len(base)),
                "f",
            )
            if base
            else None
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("cognitive protection frontier requires NAS100")

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
    triggered: dict[str, int] = {variant: 0 for variant in VARIANTS}
    armed: dict[str, int] = {variant: 0 for variant in VARIANTS}
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
        if situation.fingerprint() != state["situation_fingerprint"]:
            raise AssertionError("cognition situation fingerprint drift")
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognitive_state = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )
        entry_family = selected.selected_family.value
        trade_id = _trade_id(
            local_day=local_day,
            selected=selected,
        )

        for variant in VARIANTS:
            required = _required_confirmations(
                variant=variant,
                entry_family=entry_family,
                state=state,
                cognition=cognitive_state,
            )
            if required is not None:
                triggered[variant] += 1
            outcome = protection._simulate_single_structural_trail(
                day_bars,
                selected,
                required_confirmations=required,
            )
            status[f"{variant}:{outcome['status']}"] += 1
            if outcome["status"] != "terminal":
                continue
            enriched = dict(outcome)
            enriched["trade_id"] = trade_id
            enriched["entry_family"] = entry_family
            enriched["destination_state"] = (
                cognitive_state.destination_state
            )
            enriched["management_context"] = (
                cognitive_state.management_context.value
            )
            enriched["support_score"] = cognitive_state.support_score
            enriched["caution_score"] = cognitive_state.caution_score
            enriched["path_not_compressed"] = _is_path_not_compressed(
                cognitive_state
            )
            enriched["last_structure_event_family"] = state[
                "last_structure_event_family"
            ]
            enriched["protection_triggered"] = required is not None
            enriched["required_confirmations"] = required
            trades[variant].append(enriched)
            if bool(outcome.get("structural_trail_armed")):
                armed[variant] += 1

    baseline = trades["BASELINE"]
    variant_metrics: dict[str, object] = {}
    for variant in VARIANTS:
        values = trades[variant]
        variant_metrics[variant] = {
            "terminal_count": len(values),
            "triggered_count": triggered[variant],
            "structural_trail_armed_count": armed[variant],
            "normalized_metrics": _normalized_metrics(values),
            "monte_carlo": specialist._monte_carlo(values),
            "winner_preservation_vs_baseline": (
                _winner_preservation(baseline, values)
            ),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"]) for row in values
                    ).items()
                )
            ),
        }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variant_metrics": variant_metrics,
        "trade_rows": trades,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "target_changed": False,
            "initial_stop_changed": False,
            "stop_widening_allowed": False,
            "single_structural_trail_move_max": True,
            "trail_effective_only_after_closed_m1_confirmation": True,
            "stable_negative_signatures_predeclared": True,
            "terminal_pnl_runtime_input": False,
            "future_journey_runtime_input": False,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
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
                "variant_metrics": payload["variant_metrics"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
