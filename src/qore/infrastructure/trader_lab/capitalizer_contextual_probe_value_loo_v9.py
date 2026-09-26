"""Cross-period contextual probe-value model for Capitalizer.

V8 proved that recent winners and generic favorable context are not sufficient
to decide when a 0.20R defensive state should release risk.  V9 learns the
VALUE OF A PROBE from causal pre-entry context, but evaluates that model with
strict leave-one-period-out (LOO) separation.

For each of the three already-consumed two-year windows:
- build training examples from SURFACE_SELECTIVE trades whose base multiplier
  was exactly 0.20R in the OTHER TWO windows;
- summarize only causal pre-entry feature cells;
- require the same cell to show positive expectancy independently in both
  training windows;
- freeze that two-window model;
- replay the held-out window sequentially with no access to its outcomes.

The release action never changes entry admission, MAX3, 2R target or position
geometry. It only raises a base 0.20R allocation to 0.35R (or, for the strong
policy, 0.55R) when a temporally robust cell says a probe has positive value.

The held-out trade outcome never participates in its own decision.  Unchosen
counterfactuals are hidden during replay.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
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
    capitalizer_local_edge_convex_surface_v6 as v6,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context
from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_frozen_holdout_v1 as frozen,
)

IDENTITY = "QORE_CAPITALIZER_CONTEXTUAL_PROBE_VALUE_LOO_V9"
BASE_POSITION_POLICY = "CONTEXT_STABILITY_STAGE"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034
EXPECTED_RESERVED_TRADES = 1088

POLICIES = (
    "SURFACE_CONTROL",
    "LOO_BALANCED_035",
    "LOO_CONSERVATIVE_035",
    "LOO_STRONG_DYNAMIC",
    "LOO_ULTRA_035",
)


@dataclass(frozen=True, slots=True)
class ProbeExample:
    window: str
    symbol: str
    session: str
    entry_at: str
    selected_mode: str
    destination_state: str
    volatility_state: str
    h1_body_alignment: str
    m15_slope_alignment: str
    regime_signature: str
    hazard_score: int
    adverse_votes: int
    normalized_realized_r: str


@dataclass(frozen=True, slots=True)
class CellWindowStats:
    window: str
    support: int
    mean_r: str
    positive_rate: str
    negative_rate: str


@dataclass(frozen=True, slots=True)
class ProbeDecision:
    heldout_window: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    base_multiplier: str
    final_multiplier: str
    model_level: str | None
    model_support: int
    model_combined_mean_r: str | None
    model_min_window_mean_r: str | None
    model_min_window_positive_rate: str | None
    release_applied: bool
    current_outcome_visible_to_decision: bool = False
    heldout_outcomes_visible_to_model: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _hazard_bucket(score: int) -> str:
    if score <= 6:
        return "LE_6"
    if score <= 8:
        return "7_8"
    if score <= 10:
        return "9_10"
    return "GE_11"


def _adverse_bucket(votes: int) -> str:
    if votes <= 0:
        return "0"
    if votes == 1:
        return "1"
    if votes == 2:
        return "2"
    return "3_PLUS"


def _levels_from_values(
    *,
    symbol: str,
    session: str,
    selected_mode: str,
    destination_state: str,
    regime_signature: str,
    hazard_score: int,
    adverse_votes: int,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    hazard = _hazard_bucket(hazard_score)
    adverse = _adverse_bucket(adverse_votes)
    return (
        ("SYMBOL_DEST_MODE", (symbol, destination_state, selected_mode)),
        ("SESSION_DEST_MODE", (session, destination_state, selected_mode)),
        ("SESSION_REGIME_DEST", (session, regime_signature, destination_state)),
        ("MODE_REGIME_DEST", (selected_mode, regime_signature, destination_state)),
        ("SESSION_HAZARD_DEST", (session, hazard, destination_state, adverse)),
        ("DEST_MODE", (destination_state, selected_mode)),
        ("SESSION_DEST", (session, destination_state)),
        ("REGIME_DEST", (regime_signature, destination_state)),
        ("SESSION_HAZARD", (session, hazard, adverse)),
        ("GLOBAL_020", ("GLOBAL_020",)),
    )


def _levels_from_example(
    row: ProbeExample,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return _levels_from_values(
        symbol=row.symbol,
        session=row.session,
        selected_mode=row.selected_mode,
        destination_state=row.destination_state,
        regime_signature=row.regime_signature,
        hazard_score=row.hazard_score,
        adverse_votes=row.adverse_votes,
    )


def _surface_examples(
    *,
    window: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[ProbeExample, ...]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    missing = {(row.symbol, row.entry_at) for row in ordered} - set(contexts)
    if missing:
        raise ValueError(f"{window} missing {len(missing)} MAX3 contexts")

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    result: list[ProbeExample] = []

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
        adverse_votes = sum(item.adverse for item in evidence)
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

        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * base_multiplier
            ),
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

        if base_multiplier == Decimal("0.20"):
            result.append(
                ProbeExample(
                    window=window,
                    symbol=trade.symbol,
                    session=trade.session,
                    entry_at=trade.entry_at,
                    selected_mode=final_mode,
                    destination_state=ctx.destination_state,
                    volatility_state=ctx.volatility_state,
                    h1_body_alignment=ctx.h1_body_alignment,
                    m15_slope_alignment=ctx.m15_slope_alignment,
                    regime_signature=ctx.regime_signature,
                    hazard_score=score,
                    adverse_votes=adverse_votes,
                    normalized_realized_r=unscaled.realized_gross_r,
                )
            )
    return tuple(result)


def _cell_stats(
    rows: tuple[ProbeExample, ...],
    *,
    window: str,
) -> CellWindowStats:
    values = tuple(Decimal(row.normalized_realized_r) for row in rows)
    if not values:
        raise ValueError("probe cell stats require rows")
    support = len(values)
    positives = sum(value > 0 for value in values)
    negatives = sum(value < 0 for value in values)
    return CellWindowStats(
        window=window,
        support=support,
        mean_r=str(sum(values, Decimal("0")) / Decimal(support)),
        positive_rate=str(Decimal(positives) / Decimal(support)),
        negative_rate=str(Decimal(negatives) / Decimal(support)),
    )


def _policy_thresholds(
    policy: str,
) -> tuple[int, Decimal, Decimal, Decimal, bool]:
    if policy == "LOO_BALANCED_035":
        return 4, Decimal("0.10"), Decimal("0"), Decimal("0.45"), False
    if policy == "LOO_CONSERVATIVE_035":
        return 5, Decimal("0.20"), Decimal("0.05"), Decimal("0.50"), False
    if policy == "LOO_STRONG_DYNAMIC":
        return 5, Decimal("0.20"), Decimal("0.05"), Decimal("0.50"), True
    if policy == "LOO_ULTRA_035":
        return 6, Decimal("0.30"), Decimal("0.10"), Decimal("0.55"), False
    raise ValueError(f"unknown V9 policy: {policy}")


def _freeze_model(
    *,
    policy: str,
    training_examples: tuple[ProbeExample, ...],
    training_windows: tuple[str, str],
) -> dict[str, Any]:
    min_support, min_combined_mean, min_window_mean, min_positive_rate, dynamic = (
        _policy_thresholds(policy)
    )
    members: dict[
        tuple[str, tuple[str, ...]],
        dict[str, list[ProbeExample]],
    ] = defaultdict(lambda: defaultdict(list))
    for row in training_examples:
        if row.window not in training_windows:
            raise ValueError("probe training example outside training windows")
        for level, values in _levels_from_example(row):
            members[(level, values)][row.window].append(row)

    cells: dict[str, dict[str, Any]] = {}
    for (level, values), by_window in members.items():
        if any(window not in by_window for window in training_windows):
            continue
        stats = tuple(
            _cell_stats(tuple(by_window[window]), window=window)
            for window in training_windows
        )
        if any(item.support < min_support for item in stats):
            continue
        all_rows = tuple(
            row for window in training_windows for row in by_window[window]
        )
        combined_values = tuple(
            Decimal(row.normalized_realized_r) for row in all_rows
        )
        combined_mean = sum(combined_values, Decimal("0")) / Decimal(
            len(combined_values)
        )
        min_mean = min(Decimal(item.mean_r) for item in stats)
        min_positive = min(Decimal(item.positive_rate) for item in stats)
        eligible = (
            combined_mean >= min_combined_mean
            and min_mean >= min_window_mean
            and min_positive >= min_positive_rate
        )
        if not eligible:
            continue

        strong = (
            dynamic
            and combined_mean >= Decimal("0.75")
            and min_mean >= Decimal("0.25")
            and min_positive >= Decimal("0.55")
        )
        release_to = "0.55" if strong else "0.35"
        cell_id = json.dumps(
            {"level": level, "values": values},
            sort_keys=True,
            separators=(",", ":"),
        )
        cells[cell_id] = {
            "level": level,
            "values": values,
            "release_to": release_to,
            "support": len(all_rows),
            "combined_mean_r": str(combined_mean),
            "min_window_mean_r": str(min_mean),
            "min_window_positive_rate": str(min_positive),
            "window_stats": [asdict(item) for item in stats],
        }

    return {
        "identity": "QORE_CAPITALIZER_CONTEXTUAL_PROBE_VALUE_MODEL_V9",
        "policy": policy,
        "training_windows": training_windows,
        "heldout_window_visible_to_model": False,
        "cell_count": len(cells),
        "cells": cells,
    }


def _lookup_model(
    model: dict[str, Any],
    *,
    symbol: str,
    session: str,
    selected_mode: str,
    destination_state: str,
    regime_signature: str,
    hazard_score: int,
    adverse_votes: int,
) -> dict[str, Any] | None:
    raw_cells = model.get("cells")
    if not isinstance(raw_cells, dict):
        raise ValueError("probe value model missing cells")
    for level, values in _levels_from_values(
        symbol=symbol,
        session=session,
        selected_mode=selected_mode,
        destination_state=destination_state,
        regime_signature=regime_signature,
        hazard_score=hazard_score,
        adverse_votes=adverse_votes,
    ):
        cell_id = json.dumps(
            {"level": level, "values": values},
            sort_keys=True,
            separators=(",", ":"),
        )
        cell = raw_cells.get(cell_id)
        if isinstance(cell, dict):
            return cell
    return None


def _simulate_heldout(
    *,
    heldout_window: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    contextual_model: dict[str, Any],
    probe_model: dict[str, Any] | None,
) -> tuple[dict[str, Any], tuple[ProbeDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    missing = {(row.symbol, row.entry_at) for row in ordered} - set(contexts)
    if missing:
        raise ValueError(f"{heldout_window} missing {len(missing)} contexts")

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[ProbeDecision] = []
    multiplier_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    release_count = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _loss_streak = governor._state(history)

        base_mode, _level, _support = router._lookup(contextual_model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POSITION_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_records = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        evidence = memory._evidence(records=causal_records, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
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

        final_multiplier = base_multiplier
        cell: dict[str, Any] | None = None
        if (
            policy != "SURFACE_CONTROL"
            and base_multiplier == Decimal("0.20")
        ):
            if probe_model is None:
                raise ValueError("probe policy requires frozen model")
            cell = _lookup_model(
                probe_model,
                symbol=trade.symbol,
                session=trade.session,
                selected_mode=final_mode,
                destination_state=ctx.destination_state,
                regime_signature=ctx.regime_signature,
                hazard_score=score,
                adverse_votes=adverse_votes,
            )
            if cell is not None:
                final_multiplier = Decimal(str(cell["release_to"]))
                release_count += 1
                level_counts[str(cell["level"])] += 1

        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * final_multiplier
            ),
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
        multiplier_counts[str(final_multiplier)] += 1
        decisions.append(
            ProbeDecision(
                heldout_window=heldout_window,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                selected_mode=final_mode,
                base_multiplier=str(base_multiplier),
                final_multiplier=str(final_multiplier),
                model_level=None if cell is None else str(cell["level"]),
                model_support=0 if cell is None else int(cell["support"]),
                model_combined_mean_r=(
                    None if cell is None else str(cell["combined_mean_r"])
                ),
                model_min_window_mean_r=(
                    None if cell is None else str(cell["min_window_mean_r"])
                ),
                model_min_window_positive_rate=(
                    None if cell is None else str(cell["min_window_positive_rate"])
                ),
                release_applied=cell is not None,
            )
        )

    ledger = tuple(chosen_scaled)
    return {
        "heldout_window": heldout_window,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "release_count": release_count,
        "release_level_counts": dict(sorted(level_counts.items())),
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
    }, tuple(decisions)


def _annotate(current: dict[str, Any], control: dict[str, Any]) -> None:
    m = current["metrics"]
    c = control["metrics"]
    current["pf_at_least_surface_control"] = (
        Decimal(str(m["profit_factor"])) >= Decimal(str(c["profit_factor"]))
    )
    current["dd_below_surface_control"] = (
        Decimal(str(m["max_drawdown_r"])) < Decimal(str(c["max_drawdown_r"]))
    )
    current["total_r_at_least_surface_control"] = (
        Decimal(str(m["total_r"])) >= Decimal(str(c["total_r"]))
    )
    current["dd_at_or_below_6r"] = (
        Decimal(str(m["max_drawdown_r"])) <= Decimal("6")
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    consumed_reserved_root: Path,
    development_validation_context_root: Path,
    consumed_reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[ProbeDecision, ...]]:
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
        raise ValueError("V9 consumed reserved population mismatch")

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
    reserved_context = v6._load_reserved_contexts(
        consumed_reserved_context_root,
        baseline_keys=reserved_keys,
    )

    contextual_model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )
    windows: dict[
        str,
        tuple[
            dict[str, tuple[milestone.SimulatedTrade, ...]],
            dict[tuple[str, str], context.NativeContextRow],
        ],
    ] = {
        "DEVELOPMENT_2024_2026": (development, dev_context),
        "CONSUMED_VALIDATION_2022_2024": (validation, val_context),
        "CONSUMED_RESERVED_2020_2022": (reserved, reserved_context),
    }

    examples_by_window = {
        window: _surface_examples(
            window=window,
            ledgers=ledgers,
            contexts=contexts,
            model=contextual_model,
        )
        for window, (ledgers, contexts) in windows.items()
    }

    controls: dict[str, dict[str, Any]] = {}
    audits: list[ProbeDecision] = []
    for window, (ledgers, contexts) in windows.items():
        control, audit = _simulate_heldout(
            heldout_window=window,
            policy="SURFACE_CONTROL",
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            probe_model=None,
        )
        controls[window] = control
        audits.extend(audit)

    results: list[dict[str, Any]] = []
    for policy in POLICIES:
        heldouts: dict[str, Any] = {}
        model_cell_counts: dict[str, int] = {}
        for heldout_window, (ledgers, contexts) in windows.items():
            if policy == "SURFACE_CONTROL":
                current = controls[heldout_window]
                model_cell_counts[heldout_window] = 0
            else:
                training_windows = tuple(
                    window for window in windows if window != heldout_window
                )
                if len(training_windows) != 2:
                    raise AssertionError("LOO requires exactly two training windows")
                training_examples = tuple(
                    row
                    for window in training_windows
                    for row in examples_by_window[window]
                )
                probe_model = _freeze_model(
                    policy=policy,
                    training_examples=training_examples,
                    training_windows=(
                        str(training_windows[0]),
                        str(training_windows[1]),
                    ),
                )
                if heldout_window in probe_model["training_windows"]:
                    raise ValueError("heldout window leaked into probe model")
                model_cell_counts[heldout_window] = int(probe_model["cell_count"])
                current, audit = _simulate_heldout(
                    heldout_window=heldout_window,
                    policy=policy,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    probe_model=probe_model,
                )
                audits.extend(audit)
            _annotate(current, controls[heldout_window])
            heldouts[heldout_window] = current

        robust_pf_dd = all(
            row["pf_at_least_surface_control"]
            and row["dd_below_surface_control"]
            for row in heldouts.values()
        )
        robust_full = all(
            row["pf_at_least_surface_control"]
            and row["dd_below_surface_control"]
            and row["total_r_at_least_surface_control"]
            for row in heldouts.values()
        )
        all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
        results.append(
            {
                "policy": policy,
                "heldouts": heldouts,
                "model_cell_counts": model_cell_counts,
                "robust_pf_up_dd_down_all_loo_windows": robust_pf_dd,
                "robust_pf_dd_total_r_all_loo_windows": robust_full,
                "all_loo_windows_dd6": all_dd6,
            }
        )

    robust_rows = tuple(
        row for row in results if row["robust_pf_up_dd_down_all_loo_windows"]
    )
    robust_full_rows = tuple(
        row for row in results if row["robust_pf_dd_total_r_all_loo_windows"]
    )
    dd6_rows = tuple(row for row in robust_rows if row["all_loo_windows_dd6"])

    return {
        "identity": IDENTITY,
        "evaluation": "THREE_WAY_LEAVE_ONE_PERIOD_OUT",
        "windows": list(windows),
        "all_windows_consumed_before_v9": True,
        "next_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "surface_020_example_counts": {
            window: len(rows) for window, rows in examples_by_window.items()
        },
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust_rows),
        "robust_pf_dd_total_r_policy_count": len(robust_full_rows),
        "robust_all_loo_windows_dd6_policy_count": len(dd6_rows),
        "heldout_outcomes_visible_to_model": False,
        "model_uses_only_other_two_periods": True,
        "runtime_decisions_use_preentry_context_only": True,
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
            "FREEZE_V9_MODEL_ON_ALL_CONSUMED_WINDOWS_THEN_OPEN_2018_2020"
            if robust_rows
            else "BUILD_CAUSAL_PROBE_RANKER_WITH_CONTINUOUS_FEATURES_AND_CROSS_PERIOD_CALIBRATION"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[ProbeDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-contextual-probe-value-loo-v9.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-contextual-probe-value-loo-v9-decisions.jsonl"
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
