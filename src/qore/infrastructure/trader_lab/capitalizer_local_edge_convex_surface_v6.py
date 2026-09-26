"""Local-edge convex exposure surface for Capitalizer.

This is a NEW architecture designed after the first-use 2020-2022 holdout was
consumed and failed the hard DD gate.  It must therefore be validated on a new
non-overlapping holdout if it survives consumed-window research.

Core idea
---------
SURFACE_SELECTIVE can become sticky at 0.20R while the portfolio is in
drawdown.  Reserved-window forensics showed that the 0.20 bucket suppressed
more positive recovery R than negative R it avoided, while 0.35/0.55 remained
net protective.

This module keeps the frozen contextual position-management stack and the
original adversity surface, then applies a causal LOCAL EDGE controller:

- SESSION edge: last 12 already-closed chosen outcomes in the same session.
- Context edge: posterior evidence already available from EXACT,
  SYMBOL_DEST, SESSION_DEST and GLOBAL_DEST scopes.

Risk can tighten one step when local evidence is adverse, or release one step
when BOTH session and multi-scope context evidence are favorable.  The current
trade outcome and all unchosen counterfactual outcomes remain hidden.

All valid entries remain admitted.  Target=2R and MAX3 remain unchanged.
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
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_frozen_holdout_v1 as frozen,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context

IDENTITY = "QORE_CAPITALIZER_LOCAL_EDGE_CONVEX_SURFACE_V6"
BASE_POSITION_POLICY = "CONTEXT_STABILITY_STAGE"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034
EXPECTED_RESERVED_TRADES = 1088

SESSION_RECENT = 12
SESSION_MIN_SUPPORT = 8

POLICIES = (
    "SURFACE_CONTROL",
    "SESSION_DEFENSE",
    "LOCAL_RELEASE",
    "LOCAL_CONVEX_BALANCED",
    "LOCAL_CONVEX_STRONG",
)

RISK_LADDER = (
    Decimal("0.10"),
    Decimal("0.20"),
    Decimal("0.35"),
    Decimal("0.55"),
    Decimal("0.75"),
    Decimal("1"),
)


@dataclass(frozen=True, slots=True)
class LocalEdgeDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    current_drawdown_r: str
    hazard_score: int
    adverse_votes: int
    favorable_votes: int
    severe_votes: int
    session_support: int
    session_mean_r: str | None
    session_negative_rate: str | None
    session_adverse: bool
    session_severe: bool
    session_favorable: bool
    base_multiplier: str
    final_multiplier: str
    adjustment: str
    current_outcome_visible_to_decision: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _load_reserved_contexts(
    root: Path,
    *,
    baseline_keys: set[tuple[str, str]],
) -> dict[tuple[str, str], context.NativeContextRow]:
    all_context = frozen._load_contexts_reserved(root)
    missing = baseline_keys - set(all_context)
    if missing:
        raise ValueError(f"reserved context missing {len(missing)} MAX3 identities")
    return {key: all_context[key] for key in baseline_keys}


def _session_stats(
    records: tuple[memory.MemoryRecord, ...],
    *,
    session: str,
) -> tuple[int, Decimal | None, Decimal | None]:
    selected = tuple(row for row in records if row.session == session)[-SESSION_RECENT:]
    support = len(selected)
    if support < SESSION_MIN_SUPPORT:
        return support, None, None
    values = tuple(Decimal(row.normalized_realized_r) for row in selected)
    mean_r = sum(values, Decimal("0")) / Decimal(support)
    negative_rate = Decimal(sum(value < 0 for value in values)) / Decimal(support)
    return support, mean_r, negative_rate


def _scope_votes(
    evidence: tuple[memory.ScopeEvidence, ...],
) -> tuple[int, int, int]:
    adverse = sum(item.adverse for item in evidence)
    severe = sum(item.severe for item in evidence)
    favorable = 0
    for item in evidence:
        if (
            item.posterior_mean_r is not None
            and item.posterior_negative_rate is not None
            and Decimal(item.posterior_mean_r) > 0
            and Decimal(item.posterior_negative_rate) < Decimal("0.50")
        ):
            favorable += 1
    return adverse, severe, favorable


def _session_flags(
    mean_r: Decimal | None,
    negative_rate: Decimal | None,
) -> tuple[bool, bool, bool]:
    if mean_r is None or negative_rate is None:
        return False, False, False
    adverse = mean_r < 0 and negative_rate > Decimal("0.50")
    severe = mean_r <= Decimal("-0.15") and negative_rate >= Decimal("0.60")
    favorable = mean_r > 0 and negative_rate < Decimal("0.50")
    return adverse, severe, favorable


def _step(multiplier: Decimal, *, direction: int, steps: int = 1) -> Decimal:
    try:
        index = RISK_LADDER.index(multiplier)
    except ValueError as exc:
        raise ValueError(f"unsupported risk multiplier {multiplier}") from exc
    target = max(0, min(len(RISK_LADDER) - 1, index + direction * steps))
    return RISK_LADDER[target]


def _local_multiplier(
    *,
    policy: str,
    base: Decimal,
    current_dd: Decimal,
    session_adverse: bool,
    session_severe: bool,
    session_favorable: bool,
    adverse_votes: int,
    severe_votes: int,
    favorable_votes: int,
) -> tuple[Decimal, str]:
    if policy == "SURFACE_CONTROL":
        return base, "NONE"

    if policy == "SESSION_DEFENSE":
        if session_severe and current_dd >= Decimal("2"):
            return _step(base, direction=-1), "SESSION_SEVERE_TIGHTEN"
        if session_adverse and current_dd >= Decimal("4"):
            return _step(base, direction=-1), "SESSION_ADVERSE_TIGHTEN"
        return base, "NONE"

    if policy == "LOCAL_RELEASE":
        if (
            session_favorable
            and favorable_votes >= 2
            and adverse_votes == 0
        ):
            cap = Decimal("0.75") if current_dd >= Decimal("4") else Decimal("1")
            return min(_step(base, direction=1), cap), "LOCAL_FAVORABLE_RELEASE"
        return base, "NONE"

    if policy == "LOCAL_CONVEX_BALANCED":
        if (
            current_dd >= Decimal("2")
            and (session_severe or severe_votes >= 2)
        ):
            return _step(base, direction=-1), "LOCAL_SEVERE_TIGHTEN"
        if (
            current_dd >= Decimal("4")
            and session_adverse
            and adverse_votes >= 2
        ):
            return _step(base, direction=-1), "LOCAL_ADVERSE_TIGHTEN"
        if (
            session_favorable
            and favorable_votes >= 2
            and adverse_votes == 0
        ):
            cap = Decimal("0.75") if current_dd >= Decimal("4") else Decimal("1")
            return min(_step(base, direction=1), cap), "LOCAL_FAVORABLE_RELEASE"
        return base, "NONE"

    if policy == "LOCAL_CONVEX_STRONG":
        if (
            current_dd >= Decimal("3")
            and session_severe
            and severe_votes >= 1
        ):
            return _step(base, direction=-1, steps=2), "LOCAL_SEVERE_TIGHTEN_2"
        if (
            current_dd >= Decimal("2")
            and (session_severe or severe_votes >= 2)
        ):
            return _step(base, direction=-1), "LOCAL_SEVERE_TIGHTEN"
        if (
            session_favorable
            and favorable_votes >= 3
            and adverse_votes == 0
        ):
            cap = Decimal("0.75") if current_dd >= Decimal("4") else Decimal("1")
            return min(_step(base, direction=1), cap), "LOCAL_FAVORABLE_RELEASE"
        return base, "NONE"

    raise ValueError(f"unknown local-edge policy: {policy}")


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[LocalEdgeDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    if {(row.symbol, row.entry_at) for row in ordered} != set(contexts):
        raise ValueError(f"{role} direct/context identities differ")

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[LocalEdgeDecision] = []
    multiplier_counts: Counter[str] = Counter()
    adjustment_counts: Counter[str] = Counter()

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]

        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _loss_streak = governor._state(history)

        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POSITION_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_records = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        evidence = memory._evidence(records=causal_records, ctx=ctx)
        adverse_votes, severe_votes, favorable_votes = _scope_votes(evidence)
        hazards = frozen._frozen_hazards(
            ctx=ctx,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
        )
        score = frozen._frozen_score(hazards)
        base_multiplier = frozen._frozen_multiplier(
            current_dd=current_dd,
            score=score,
            adverse_votes=adverse_votes,
        )

        session_support, session_mean, session_negative = _session_stats(
            causal_records,
            session=trade.session,
        )
        session_adverse, session_severe, session_favorable = _session_flags(
            session_mean,
            session_negative,
        )
        multiplier, adjustment = _local_multiplier(
            policy=policy,
            base=base_multiplier,
            current_dd=current_dd,
            session_adverse=session_adverse,
            session_severe=session_severe,
            session_favorable=session_favorable,
            adverse_votes=adverse_votes,
            severe_votes=severe_votes,
            favorable_votes=favorable_votes,
        )

        scaled = replace(
            unscaled,
            realized_gross_r=str(Decimal(unscaled.realized_gross_r) * multiplier),
        )
        chosen_scaled.append(scaled)
        records.append(
            memory.MemoryRecord(
                symbol=ctx.symbol,
                session=ctx.session,
                destination_state=ctx.destination_state,
                context_signature=ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        multiplier_counts[str(multiplier)] += 1
        adjustment_counts[adjustment] += 1
        decisions.append(
            LocalEdgeDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                selected_mode=final_mode,
                current_drawdown_r=str(current_dd),
                hazard_score=score,
                adverse_votes=adverse_votes,
                favorable_votes=favorable_votes,
                severe_votes=severe_votes,
                session_support=session_support,
                session_mean_r=None if session_mean is None else str(session_mean),
                session_negative_rate=(
                    None if session_negative is None else str(session_negative)
                ),
                session_adverse=session_adverse,
                session_severe=session_severe,
                session_favorable=session_favorable,
                base_multiplier=str(base_multiplier),
                final_multiplier=str(multiplier),
                adjustment=adjustment,
            )
        )

    ledger = tuple(chosen_scaled)
    return {
        "role": role,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
        "adjustment_counts": dict(sorted(adjustment_counts.items())),
    }, tuple(decisions)


def _annotate(
    current: dict[str, Any],
    control: dict[str, Any],
) -> None:
    metrics = current["metrics"]
    base = control["metrics"]
    current["pf_at_least_surface_control"] = (
        Decimal(str(metrics["profit_factor"])) >= Decimal(str(base["profit_factor"]))
    )
    current["dd_below_surface_control"] = (
        Decimal(str(metrics["max_drawdown_r"]))
        < Decimal(str(base["max_drawdown_r"]))
    )
    current["total_r_at_least_surface_control"] = (
        Decimal(str(metrics["total_r"])) >= Decimal(str(base["total_r"]))
    )
    current["total_r_retention_vs_surface"] = str(
        Decimal(str(metrics["total_r"])) / Decimal(str(base["total_r"]))
    )
    current["dd_at_or_below_6r"] = (
        Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    consumed_reserved_root: Path,
    development_validation_context_root: Path,
    consumed_reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[LocalEdgeDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=EXPECTED_VALIDATION_TRADES,
    )
    raw_reserved = {
        mode.value: direct._load_mode(consumed_reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }
    if {len(rows) for rows in reserved.values()} != {EXPECTED_RESERVED_TRADES}:
        raise ValueError("consumed reserved population mismatch")

    dev_context = router._load_contexts(
        development_validation_context_root,
        role="dev",
    )
    validation_context = router._load_contexts(
        development_validation_context_root,
        role="holdout",
    )
    reserved_keys = {
        (row.symbol, row.entry_at)
        for row in reserved[milestone.ProtectionMode.ORIGINAL.value]
    }
    reserved_context = _load_reserved_contexts(
        consumed_reserved_context_root,
        baseline_keys=reserved_keys,
    )

    model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )

    windows = (
        ("DEVELOPMENT_2024_2026", development, dev_context),
        ("CONSUMED_VALIDATION_2022_2024", validation, validation_context),
        ("CONSUMED_RESERVED_2020_2022", reserved, reserved_context),
    )

    results: list[dict[str, Any]] = []
    audits: list[LocalEdgeDecision] = []
    controls: dict[str, dict[str, Any]] = {}
    for role, ledgers, contexts in windows:
        control, control_audit = _simulate(
            role=role,
            policy="SURFACE_CONTROL",
            ledgers=ledgers,
            contexts=contexts,
            model=model,
        )
        controls[role] = control
        audits.extend(control_audit)

    for policy in POLICIES:
        policy_windows: dict[str, Any] = {}
        for role, ledgers, contexts in windows:
            if policy == "SURFACE_CONTROL":
                current = controls[role]
                audit: tuple[LocalEdgeDecision, ...] = ()
            else:
                current, audit = _simulate(
                    role=role,
                    policy=policy,
                    ledgers=ledgers,
                    contexts=contexts,
                    model=model,
                )
                audits.extend(audit)
            _annotate(current, controls[role])
            policy_windows[role] = current

        robust_pf_dd = all(
            window["pf_at_least_surface_control"]
            and window["dd_below_surface_control"]
            for window in policy_windows.values()
        )
        robust_full = all(
            window["pf_at_least_surface_control"]
            and window["dd_below_surface_control"]
            and window["total_r_at_least_surface_control"]
            for window in policy_windows.values()
        )
        all_dd6 = all(
            window["dd_at_or_below_6r"]
            for window in policy_windows.values()
        )
        results.append(
            {
                "policy": policy,
                "windows": policy_windows,
                "robust_pf_up_dd_down_all_consumed_windows": robust_pf_dd,
                "robust_pf_dd_total_r_all_consumed_windows": robust_full,
                "all_consumed_windows_dd6": all_dd6,
            }
        )

    robust = tuple(
        row for row in results
        if row["robust_pf_up_dd_down_all_consumed_windows"]
    )
    robust_full = tuple(
        row for row in results
        if row["robust_pf_dd_total_r_all_consumed_windows"]
    )
    dd6 = tuple(row for row in robust if row["all_consumed_windows_dd6"])

    return {
        "identity": IDENTITY,
        "design_windows": [
            "2024-09-17_TO_2026-09-17",
            "2022-09-17_TO_2024-09-17",
            "2020-09-17_TO_2022-09-17",
        ],
        "all_design_windows_consumed": True,
        "next_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "development_trades": EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": EXPECTED_VALIDATION_TRADES,
        "consumed_reserved_trades": EXPECTED_RESERVED_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust),
        "robust_pf_dd_total_r_policy_count": len(robust_full),
        "robust_all_windows_dd6_policy_count": len(dd6),
        "session_memory_uses_prior_closed_chosen_outcomes_only": True,
        "context_memory_uses_prior_closed_chosen_outcomes_only": True,
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "all_entries_preserved": True,
        "target_r": "2.00",
        "max3_preserved": True,
        "automatic_policy_promotion": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_PARETO_LOCAL_EDGE_POLICY_AND_OPEN_2018_2020_HOLDOUT"
            if robust
            else "REBUILD_CLUSTER_STATE_WITH_CAUSAL_SESSION_LOSS_PRESSURE"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[LocalEdgeDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-local-edge-convex-surface-v6.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-local-edge-convex-surface-v6-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("consumed_reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("consumed_reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.consumed_reserved_root,
        args.development_validation_context_root,
        args.consumed_reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
