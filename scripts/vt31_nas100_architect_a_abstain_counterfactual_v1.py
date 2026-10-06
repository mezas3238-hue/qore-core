"""VT31 NAS100 Architect A abstain counterfactual forensics V1.

Consumed/burned evidence research only.

The current reasoning engine treats every contradiction as sovereign ABSTAIN.
This lab asks whether that is causally too coarse. For the first hard-ABSTAIN
state of each source event, it simulates the exact already-formed executable
setup with the frozen source structural boundary and records the result only as
a research label.

The future outcome is never supplied back to runtime reasoning. The goal is to
identify contradiction classes that are consistently protective versus classes
that may be false-negative admission vetoes and therefore deserve a separately
predeclared causal refinement.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.architect_a_abstain_counterfactual.v1"
MIN_GROUP_SAMPLE = 3


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return specialist._metrics(rows, friction=specialist.FRICTION)


def _key(parts: tuple[str, ...]) -> str:
    return "|".join(parts)


def _group_rows(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        state = cast(dict[str, object], row["pre_entry_state"])
        family = str(row["entry_family"])
        h1 = str(state["h1_state"])
        volatility = str(state["reference_volatility_state"])
        last_structure = str(state["last_structure_event_family"])
        contradictions = tuple(
            sorted(str(x) for x in cast(list[object], state["reasoning_contradictions"]))
        )
        exact = "+".join(contradictions)
        groups[_key(("exact", exact))].append(row)
        for reason in contradictions:
            groups[_key(("reason", reason))].append(row)
            groups[_key(("family_reason", family, reason))].append(row)
            groups[_key(("h1_reason", h1, reason))].append(row)
            groups[
                _key(("family_h1_reason", family, h1, reason))
            ].append(row)
            groups[
                _key(("volatility_reason", volatility, reason))
            ].append(row)
            groups[
                _key(("last_structure_reason", last_structure, reason))
            ].append(row)

    result: dict[str, dict[str, object]] = {}
    for key, values in sorted(groups.items()):
        if len(values) < MIN_GROUP_SAMPLE:
            continue
        result[key] = {
            "sample": len(values),
            "stress_0_05r": _metrics(values),
            "family_counts": dict(
                sorted(Counter(str(v["entry_family"]) for v in values).items())
            ),
        }
    return result


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        specialist.load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != "NAS100":
        raise ValueError("Architect A counterfactual requires NAS100 evidence")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[specialist._day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = specialist.Vt31R22ExecutionPolicy()

    terminal_denied: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    abstain_reason_counts: Counter[str] = Counter()
    actual_execute_days = 0
    wait_observations = 0

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        prefix = list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]

        for bar in session:
            prefix.append(bar)
            evaluation = specialist.evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue

            executable, _ = specialist.make_executable_setup(
                evaluation.setup,
                policy,
            )
            if executable is None:
                status["source-not-executable"] += 1
                break

            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= specialist._wall(getattr(item, "opened_at"))
                < (11, 0, 0)
            )
            observation_at = cast(datetime, getattr(bar, "closed_at"))
            state = specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
                session_prefix,
                evaluation.setup,
                executable,
                observation_at,
            )
            action = str(state["action"])
            if action == "WAIT":
                wait_observations += 1
                continue
            if action == "EXECUTE":
                actual_execute_days += 1
                break
            if action != "ABSTAIN":
                raise ValueError(f"unsupported reasoning action: {action}")

            contradictions = [
                str(x)
                for x in cast(list[object], state["reasoning_contradictions"])
            ]
            for reason in contradictions:
                abstain_reason_counts[reason] += 1

            counter_setup = specialist.Vt31R22ExecutableSetup(
                side=executable.side,
                entry_price=executable.entry_price,
                stop_price=executable.stop_price,
                target_price=executable.target_price,
                three_r_price=executable.three_r_price,
                selected_family=executable.selected_family,
                candidate_families=executable.candidate_families,
                decision_at=observation_at,
                pending_expires_at=executable.pending_expires_at,
                source_setup=executable.source_setup,
                execution_policy_fingerprint=(
                    executable.execution_policy_fingerprint
                ),
            )
            outcome = specialist.baseline._simulate(day_bars, counter_setup)
            counter_status = str(outcome["status"])
            status[f"abstain-counterfactual:{counter_status}"] += 1
            if counter_status == "terminal":
                row = dict(outcome)
                row["entry_family"] = executable.selected_family.value
                row["counterfactual_decision_at"] = (
                    observation_at.astimezone(UTC).isoformat()
                )
                row["pre_entry_state"] = {
                    key: state[key]
                    for key in (
                        "decision_at",
                        "decision_minute_ny",
                        "last_structure_event_family",
                        "last_structure_event_age_minutes",
                        "reference_reclaim_age_minutes",
                        "current_path_vs_previous",
                        "current_path_compressed",
                        "reference_width_vs_prior5",
                        "reference_volatility_state",
                        "prior_day_state",
                        "h4_state",
                        "h1_state",
                        "premarket_state",
                        "cash_open_state",
                        "position_in_prior_day_range",
                        "raid_depth_ref",
                        "recent_path_efficiency",
                        "recent_overlap_rate",
                        "risk_ref",
                        "planned_target_r",
                        "destination_distance_ref",
                        "confirmation_latency_minutes",
                        "entry_evidence_age_minutes",
                        "reasoning_contradictions",
                        "reasoning_uncertainty",
                        "situation_fingerprint",
                    )
                }
                terminal_denied.append(row)
            break

    terminal_denied.sort(
        key=lambda row: str(row["counterfactual_decision_at"])
    )
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "actual_execute_days": actual_execute_days,
        "wait_observations": wait_observations,
        "abstain_reason_counts": dict(sorted(abstain_reason_counts.items())),
        "counterfactual_status_counts": dict(sorted(status.items())),
        "counterfactual_terminal_count": len(terminal_denied),
        "counterfactual_terminal_metrics": _metrics(terminal_denied),
        "groups": _group_rows(terminal_denied),
        "counterfactual_terminal_rows": terminal_denied,
        "governance": {
            "consumed_evidence_only": True,
            "current_runtime_reasoning_changed": False,
            "first_hard_abstain_per_source_event_only": True,
            "counterfactual_uses_already_formed_setup": True,
            "counterfactual_uses_source_structural_exit": True,
            "future_outcome_used_for_runtime_admission": False,
            "future_outcome_used_only_as_research_label": True,
            "fold_identity_used_for_runtime_admission": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
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
                "actual_execute_days": payload["actual_execute_days"],
                "abstain_reason_counts": payload["abstain_reason_counts"],
                "counterfactual_terminal_count": (
                    payload["counterfactual_terminal_count"]
                ),
                "counterfactual_terminal_metrics": (
                    payload["counterfactual_terminal_metrics"]
                ),
                "group_count": len(cast(dict[str, object], payload["groups"])),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
