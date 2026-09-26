"""Cross-period causal abstention for Capitalizer defensive probes.

V10/V11 falsified risk RELEASE from the existing 0.20R defensive state.
V12 tests the opposite action: ABSTAIN only when two independent training
periods both rank the current enriched Factor/Journey state in a predeclared
lower tail whose training expectancy is negative in both periods.

This is a selected-ledger causal diagnostic. It does not backfill an abstained
MAX3 slot with an opportunity that the source replay originally displaced.
Any viable V12 rule must therefore be re-run through full source competition
before candidate freeze.

No current outcome, heldout label, future exit or unchosen counterfactual is
visible to the decision.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_local_edge_convex_surface_v6 as edge_v6,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)

IDENTITY = "QORE_CAPITALIZER_FACTOR_JOURNEY_CONFLICT_ABSTENTION_V12"
POLICIES = (
    "SURFACE_CONTROL",
    "ABSTAIN_Q10",
    "ABSTAIN_Q20",
    "ABSTAIN_Q30",
    "ABSTAIN_Q40",
)
POLICY_Q = {
    "ABSTAIN_Q10": 0.10,
    "ABSTAIN_Q20": 0.20,
    "ABSTAIN_Q30": 0.30,
    "ABSTAIN_Q40": 0.40,
}
MIN_DENSITY_RETENTION = Decimal("0.90")


@dataclass(frozen=True, slots=True)
class AbstainDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    base_multiplier: str
    model_percentiles: tuple[str, str] | None
    model_lower_tail_mean_r: tuple[str, str] | None
    model_lower_tail_support: tuple[int, int] | None
    abstain: bool
    current_outcome_visible_to_decision: bool = False
    heldout_outcomes_visible_to_models: bool = False


def _lower_tail(
    model: v10.PeriodModel,
    *,
    quantile: float,
) -> tuple[Decimal, int]:
    threshold = v10._quantile(model.loo_scores, quantile)
    labels = tuple(
        Decimal(row.realized_r or "0")
        for score, row in zip(model.loo_scores, model.points, strict=True)
        if score <= threshold
    )
    if not labels:
        return Decimal("0"), 0
    return sum(labels, Decimal("0")) / Decimal(len(labels)), len(labels)


def _should_abstain(
    models: tuple[v10.PeriodModel, v10.PeriodModel],
    *,
    point: v10.ProbePoint,
    policy: str,
) -> tuple[
    bool,
    tuple[float, float],
    tuple[Decimal, Decimal],
    tuple[int, int],
]:
    quantile = POLICY_Q[policy]
    scores = tuple(v10._predict(model.points, point) for model in models)
    percentiles = tuple(
        v10._percentile(model, score)
        for model, score in zip(models, scores, strict=True)
    )
    lower = tuple(_lower_tail(model, quantile=quantile) for model in models)
    means = (lower[0][0], lower[1][0])
    support = (lower[0][1], lower[1][1])
    decision = (
        max(percentiles) <= quantile
        and max(means) < 0
        and min(support) >= v10.MIN_TAIL_SUPPORT
    )
    return decision, (percentiles[0], percentiles[1]), means, support


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    models: tuple[v10.PeriodModel, v10.PeriodModel] | None,
) -> tuple[dict[str, Any], tuple[AbstainDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (direct._aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[AbstainDecision] = []
    multipliers: Counter[str] = Counter()
    abstained = 0

    for trade in ordered:
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        reject = False
        percentiles: tuple[float, float] | None = None
        means: tuple[Decimal, Decimal] | None = None
        support: tuple[int, int] | None = None
        if (
            policy != "SURFACE_CONTROL"
            and pre.base_multiplier == Decimal("0.20")
        ):
            if models is None:
                raise ValueError("V12 abstention requires two training models")
            reject, percentiles, means, support = _should_abstain(
                models,
                point=pre.point,
                policy=policy,
            )

        decisions.append(
            AbstainDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                base_multiplier=str(pre.base_multiplier),
                model_percentiles=(
                    None if percentiles is None
                    else (str(percentiles[0]), str(percentiles[1]))
                ),
                model_lower_tail_mean_r=(
                    None if means is None
                    else (str(means[0]), str(means[1]))
                ),
                model_lower_tail_support=support,
                abstain=reject,
            )
        )
        if reject:
            abstained += 1
            continue

        unscaled = by_mode[pre.mode][(trade.symbol, trade.entry_at)]
        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * pre.base_multiplier
            ),
        )
        chosen.append(scaled)
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        multipliers[str(pre.base_multiplier)] += 1

    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "original_selected_trades": len(ordered),
        "abstained": abstained,
        "density_retention": str(Decimal(len(ledger)) / Decimal(len(ordered))),
        "metrics": milestone._metrics(ledger),
        "multiplier_counts": dict(sorted(multipliers.items())),
    }, tuple(decisions)


def _load_windows(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[
    dict[str, tuple[dict[str, tuple[milestone.SimulatedTrade, ...]], dict[Any, Any]]],
    dict[str, Any],
]:
    development = router._load_selected(
        development_root,
        expected=v10.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=v10.EXPECTED_VALIDATION_TRADES,
    )
    raw_reserved = {
        mode.value: direct._load_mode(reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }
    if {len(rows) for rows in reserved.values()} != {v10.EXPECTED_RESERVED_TRADES}:
        raise ValueError("V12 reserved population mismatch")
    dev_context = router._load_contexts(
        development_validation_context_root,
        role="dev",
    )
    val_context = router._load_contexts(
        development_validation_context_root,
        role="holdout",
    )
    reserved_keys = {
        (row.symbol, row.entry_at)
        for row in reserved[milestone.ProtectionMode.ORIGINAL.value]
    }
    reserved_context = edge_v6._load_reserved_contexts(
        reserved_context_root,
        baseline_keys=reserved_keys,
    )
    contextual_model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )
    windows = {
        v10.DEVELOPMENT_PERIOD: (development, dev_context),
        "CONSUMED_VALIDATION_2022_2024": (validation, val_context),
        "CONSUMED_RESERVED_2020_2022": (reserved, reserved_context),
    }
    return windows, contextual_model


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[AbstainDecision, ...]]:
    windows, contextual_model = _load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    examples = {
        period: v10._surface_examples(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
        )
        for period, (ledgers, contexts) in windows.items()
    }
    models = {
        period: v10._fit_period(points, period=period)
        for period, points in examples.items()
    }

    controls: dict[str, dict[str, Any]] = {}
    audits: list[AbstainDecision] = []
    for period, (ledgers, contexts) in windows.items():
        control, audit = _simulate(
            period=period,
            policy="SURFACE_CONTROL",
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            models=None,
        )
        controls[period] = control
        audits.extend(audit)

    results: list[dict[str, Any]] = []
    for policy in POLICIES:
        heldouts: dict[str, Any] = {}
        for heldout, (ledgers, contexts) in windows.items():
            if policy == "SURFACE_CONTROL":
                current = controls[heldout]
            else:
                training = tuple(period for period in windows if period != heldout)
                current, audit = _simulate(
                    period=heldout,
                    policy=policy,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    models=(models[training[0]], models[training[1]]),
                )
                audits.extend(audit)

            v10._annotate(current, controls[heldout])
            current["density_at_or_above_floor"] = (
                Decimal(current["density_retention"]) >= MIN_DENSITY_RETENTION
            )
            heldouts[heldout] = current

        strict = tuple(heldouts[p] for p in v10.STRICT_OOS_PERIODS)
        all_full = all(
            row["pf_at_least_surface_control"]
            and row["dd_below_surface_control"]
            and row["total_r_at_least_surface_control"]
            and row["density_at_or_above_floor"]
            for row in heldouts.values()
        )
        strict_full = all(
            row["pf_at_least_surface_control"]
            and row["dd_below_surface_control"]
            and row["total_r_at_least_surface_control"]
            and row["density_at_or_above_floor"]
            for row in strict
        )
        all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
        strict_dd6 = all(row["dd_at_or_below_6r"] for row in strict)
        results.append(
            {
                "policy": policy,
                "heldouts": heldouts,
                "all_consumed_full_gate": all_full,
                "strict_oos_full_gate": strict_full,
                "all_consumed_dd6": all_dd6,
                "strict_oos_dd6": strict_dd6,
            }
        )

    candidates = tuple(
        row
        for row in results
        if row["all_consumed_full_gate"]
        and row["strict_oos_full_gate"]
        and row["all_consumed_dd6"]
        and row["strict_oos_dd6"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "SELECTED_LEDGER_DUAL_MODEL_LOWER_TAIL_ABSTENTION",
        "strict_oos_periods": list(v10.STRICT_OOS_PERIODS),
        "development_period": v10.DEVELOPMENT_PERIOD,
        "minimum_density_retention": str(MIN_DENSITY_RETENTION),
        "policy_count": len(POLICIES),
        "results": results,
        "candidate_count": len(candidates),
        "selected_ledger_diagnostic_only": True,
        "full_source_recompetition_required_before_freeze": True,
        "current_outcome_visible_to_decision": False,
        "heldout_outcomes_visible_to_models": False,
        "abstention_only_when_both_training_lower_tails_negative": True,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "REPLAY_V12_RULE_THROUGH_FULL_SOURCE_COMPETITION"
            if candidates
            else "BUILD_SEQUENCE_FAILURE_MEMORY_ABSTENTION_V13"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[AbstainDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-factor-journey-conflict-abstention-v12.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-factor-journey-conflict-abstention-v12-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
