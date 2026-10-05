"""Universal whole-position target-extension frontier for VT31 NAS100.

Consumed-evidence Architect-B research only.

This frontier tests a volume-agnostic target decision made from causal
pre-entry cognition. No partial exit is required. When an eligible state is
present, the entire trade targets DOL2, defined as the opposite frozen
09:00 reference boundary (DOL1) plus 0.25 frozen reference width.

Variants:
- BASELINE_DOL1
- DEEP_DOL2
- FVG_DEEP_DOL2
- FVG_DEEP_SUPPORTIVE_DOL2

The extension destination is selected before fill from causal state only.
Admission, entry, initial stop, 3R breakeven and 16:00 lifecycle are unchanged.
No sizing, leverage, compounding, capital weighting or absolute volume enters
the edge calculation.
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

SCHEMA = "qore.vt31.nas100.universal_target_extension_frontier.v1"
MARKET = "NAS100"
EXTENSION_REF = Decimal("0.25")
VARIANTS = (
    "BASELINE_DOL1",
    "DEEP_DOL2",
    "FVG_DEEP_DOL2",
    "FVG_DEEP_SUPPORTIVE_DOL2",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _reference_width(day_bars: tuple[object, ...]) -> Decimal | None:
    reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
    if len(reference) != 60:
        return None
    high = max(_d(getattr(bar, "high")) for bar in reference)
    low = min(_d(getattr(bar, "low")) for bar in reference)
    width = high - low
    return width if width > 0 else None


def _eligible(
    *,
    variant: str,
    entry_family: str,
    cognition: FullCognitivePositionState,
) -> bool:
    if variant == "BASELINE_DOL1":
        return False
    if variant == "DEEP_DOL2":
        return cognition.destination_state == "DEEP"
    if variant == "FVG_DEEP_DOL2":
        return (
            entry_family == "fair-value-gap"
            and cognition.destination_state == "DEEP"
        )
    if variant == "FVG_DEEP_SUPPORTIVE_DOL2":
        return (
            entry_family == "fair-value-gap"
            and cognition.destination_state == "DEEP"
            and cognition.management_context.value == "SUPPORTIVE"
        )
    raise ValueError(variant)


def _extended_setup(
    selected: Vt31R22ExecutableSetup,
    *,
    reference_width: Decimal,
) -> Vt31R22ExecutableSetup:
    direction = Decimal(1) if selected.side.value == "long" else Decimal(-1)
    dol2 = selected.target_price + direction * reference_width * EXTENSION_REF
    return Vt31R22ExecutableSetup(
        side=selected.side,
        entry_price=selected.entry_price,
        stop_price=selected.stop_price,
        target_price=dol2,
        three_r_price=selected.three_r_price,
        selected_family=selected.selected_family,
        candidate_families=selected.candidate_families,
        decision_at=selected.decision_at,
        pending_expires_at=selected.pending_expires_at,
        source_setup=selected.source_setup,
        execution_policy_fingerprint=selected.execution_policy_fingerprint,
    )


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
        raise ValueError("universal target extension requires NAS100")

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
    extended_counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        width = _reference_width(day_bars)
        if width is None:
            status["invalid-reference-width"] += 1
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
        entry_family = selected.selected_family.value
        trade_id = cognitive._trade_id(
            local_day=local_day,
            selected=selected,
        )
        baseline = specialist.baseline._simulate(day_bars, selected)

        for variant in VARIANTS:
            extend = _eligible(
                variant=variant,
                entry_family=entry_family,
                cognition=cognition,
            )
            setup = (
                _extended_setup(selected, reference_width=width)
                if extend
                else selected
            )
            outcome = specialist.baseline._simulate(day_bars, setup)
            status[f"{variant}:{outcome['status']}"] += 1
            if outcome["status"] != "terminal":
                continue
            if extend:
                extended_counts[variant] += 1

            row = dict(outcome)
            row["trade_id"] = trade_id
            row["local_date"] = local_day.isoformat()
            row["side"] = selected.side.value
            row["entry_family"] = entry_family
            row["management_context"] = cognition.management_context.value
            row["destination_state"] = cognition.destination_state
            row["target_extension_selected"] = extend
            row["target_identity"] = "DOL2" if extend else "DOL1"
            row["reference_width"] = format(width, "f")
            row["extension_ref"] = (
                format(EXTENSION_REF, "f") if extend else "0"
            )
            row["baseline_r"] = baseline.get("r_multiple")
            row["managed_r"] = outcome.get("r_multiple")
            row["delta_r"] = (
                format(
                    _d(outcome["r_multiple"]) - _d(baseline["r_multiple"]),
                    "f",
                )
                if baseline.get("status") == "terminal"
                and outcome.get("status") == "terminal"
                else None
            )
            trades[variant].append(row)

    baseline_rows = trades["BASELINE_DOL1"]
    reports: dict[str, object] = {}
    for variant, rows in trades.items():
        reports[variant] = {
            "terminal_count": len(rows),
            "extended_trade_count": extended_counts[variant],
            "normalized_metrics": cognitive._normalized_metrics(rows),
            "monte_carlo": specialist._monte_carlo(rows),
            "winner_preservation_vs_baseline": (
                None
                if variant == "BASELINE_DOL1"
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
        "extension_contract": {
            "extension_ref": format(EXTENSION_REF, "f"),
            "destination": "DOL2_PLUS_0_25_FROZEN_REFERENCE_WIDTH",
            "decision_time": "pre-fill-causal-cognition",
            "whole_position": True,
            "partial_exit_required": False,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "variant_reports": reports,
        "trade_rows": trades,
        "status_counts": dict(sorted(status.items())),
        "governance": {
            "consumed_evidence_only": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "baseline_3r_breakeven_preserved": True,
            "lifecycle_changed": False,
            "target_selected_pre_fill": True,
            "future_extension_runtime_input": False,
            "terminal_pnl_runtime_input": False,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "absolute_volume_used": False,
            "provider_volume_rule_used": False,
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
                "variant_reports": payload["variant_reports"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
