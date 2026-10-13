"""R2-CE: frozen-control vs WAIT-aligned cohort diagnostic for VT08 CRT PURE.

Research only. Read docs/research/VT08-CRT-PURE-R2CE-WAIT-COHORT-ALIGNMENT-FREEZE-001.md.
No trader sizing/volume/capital authority; no certification or deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas as r2bc,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bh_audusd_entry_viability_wf as r2bh,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2by_audusd_cognitive_experience_wf as r2by,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bz_usdjpy_cognitive_experience_wf as r2bz,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cc_audusd_cognitive_wait_resolution_wf as r2cc,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cd_usdjpy_cognitive_wait_resolution_wf as r2cd,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)

IDENTITY = "VT08_CRT_PURE_R2CE_WAIT_COHORT_ALIGNMENT_DIAGNOSTIC_001"
SCHEMA = "qore.vt08.crt_pure.r2ce_wait_cohort_alignment.v1"
MIN_DENSITY_PER_YEAR = 170.0
ARMS = ("CONTROL_ALL", "WAIT_ALIGNED_DIAGNOSTIC")
# These numbers refer only to frozen earlier runs; they are checks, not outcomes.
REFERENCE = {
    "AUDUSD": {"trades": 1067, "pf": 1.07424084, "r": 28.1440},
    "USDJPY": {"trades": 511, "pf": 1.01154342, "r": 2.2637},
}



FROZEN_LEDGER_RUNS = {
    "AUDUSD": 36173116494,
    "USDJPY": 36173125334,
}


def _parse_trade(payload: dict[str, Any]) -> Model1LabTrade:
    return Model1LabTrade(
        **{**payload, "reference_ids": tuple(payload["reference_ids"])}
    )


def _load_frozen_delayed(market: str, path: Path) -> tuple[Any, ...]:
    """Rehydrate full R2-CC/CD delayed ledgers; no broker API or new candles."""
    module: Any = r2cc if market == "AUDUSD" else r2cd
    restored: list[Any] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"{market} non-object ledger line {line_no}")
            source_payload = payload["source"]
            original = _parse_trade(source_payload["trade"])
            source: Any
            if market == "AUDUSD":
                source = r2bh.ViabilityRecord(
                    trade=original,
                    features=tuple(
                        (str(pair[0]), str(pair[1]))
                        for pair in source_payload["features"]
                    ),
                    dead_on_arrival=bool(source_payload["dead_on_arrival"]),
                )
            elif market == "USDJPY":
                source = r2bz.CognitiveRecord(
                    trade=original,
                    key=str(source_payload["key"]),
                    dead_on_arrival=bool(source_payload["dead_on_arrival"]),
                )
            else:
                raise ValueError(f"Unknown frozen market: {market}")
            delayed_payload = payload["delayed_trade"]
            delayed_trade = (
                None if delayed_payload is None else _parse_trade(delayed_payload)
            )
            restored.append(
                module.DelayedRecord(
                    source=source,
                    journey_state=str(payload["journey_state"]),
                    delayed_trade=delayed_trade,
                    delayed_doa=payload["delayed_doa"],
                    terminal_reason=payload["terminal_reason"],
                )
            )
    if not restored:
        raise ValueError(f"{market}: empty frozen delayed ledger")
    return tuple(restored)


def _verify_frozen_report(
    comparison: dict[str, Any],
    reference_path: Path,
) -> dict[str, Any]:
    """Fail closed if the offline reconstructed control differs from source replay."""
    source = json.loads(reference_path.read_text(encoding="utf-8"))
    original = source["combined_oos_cognitive_portfolio"]
    checks: dict[str, Any] = {}
    for key in (
        "trades",
        "total_r",
        "profit_factor",
        "max_drawdown_r",
        "dead_on_arrival_rate",
    ):
        actual = comparison[key]
        expected = original[key]
        valid = (
            actual == expected
            if isinstance(actual, int)
            else abs(float(actual) - float(expected)) < 1e-6
        )
        checks[key] = {"matched": valid, "observed": actual, "expected": expected}
        if not valid:
            raise ValueError(
                f"Frozen R2-CC/CD report mismatch on {key}: "
                f"observed={actual}, expected={expected}"
            )
    if comparison["origin_counts"] != original["origin_counts"]:
        raise ValueError("Frozen source origin-count mismatch")
    return checks


def _initial_action(
    decision: Callable[[Any, Any], Any],
    model: Any,
    row: Any,
) -> CrtPureReasoningAction:
    action = cast(CrtPureReasoningAction, decision(model, row).action)
    if action not in (
        CrtPureReasoningAction.EXECUTE,
        CrtPureReasoningAction.WAIT,
        CrtPureReasoningAction.ABSTAIN,
    ):
        raise ValueError(f"Unexpected initial cognitive action: {action}")
    return action


def _wait_training_cohort(
    training: tuple[Any, ...],
    initial_model: Any,
    initial_decision: Callable[[Any, Any], Any],
    delayed_by_key: dict[Any, Any],
    record_key: Callable[[Any], Any],
) -> tuple[tuple[Any, ...], dict[str, int]]:
    """Diagnostic in-sample cohort selection on prior 4Y, never OOS outcomes."""
    selected: list[Any] = []
    counts: Counter[str] = Counter()
    for row in training:
        action = _initial_action(initial_decision, initial_model, row)
        counts[action.value] += 1
        if action is CrtPureReasoningAction.WAIT:
            delayed = delayed_by_key[record_key(row)]
            if delayed.delayed_trade is None:
                counts["WAIT_TERMINAL"] += 1
            else:
                counts["WAIT_DELAYED_VIABLE"] += 1
                selected.append(delayed)
    if counts["WAIT"] != counts["WAIT_TERMINAL"] + counts["WAIT_DELAYED_VIABLE"]:
        raise ValueError("TRAIN WAIT cohort accounting mismatch")
    return tuple(selected), dict(sorted(counts.items()))


def _reference_check(market: str, control: dict[str, Any]) -> dict[str, Any]:
    expected = REFERENCE[market]
    observed_pf = float(control["profit_factor"] or 0.0)
    observed_r = float(control["total_r"])
    okay = (
        control["trades"] == expected["trades"]
        and abs(observed_pf - expected["pf"]) < 0.0002
        and abs(observed_r - expected["r"]) < 0.03
    )
    return {
        "matches_frozen_publication": okay,
        "expected": expected,
        "observed": {"trades": control["trades"], "pf": observed_pf, "r": observed_r},
    }


def _aud_initial_decision(model: Any, row: Any) -> Any:
    return r2by._decision(model=model, record=row)


def run_market(
    market: str,
    *,
    frozen_ledger: Path | None = None,
    frozen_report: Path | None = None,
) -> dict[str, Any]:
    records: tuple[Any, ...]
    initial_decision: Callable[[Any, Any], Any]
    initial_fit: Callable[[tuple[Any, ...]], tuple[Any, dict[str, Any]]]
    year_start: Callable[[int], datetime]
    slice_records: Callable[[tuple[Any, ...], datetime, datetime], tuple[Any, ...]]
    if market == "AUDUSD":
        module: Any = r2cc
        start, end, training_years = r2bh.START, r2bh.END, r2bh.TRAINING_YEARS
        initial_decision = _aud_initial_decision
        initial_fit = r2by._fit
        year_start = r2bh._year_start
        slice_records = r2bh._slice
        load_market = r2by.MARKET
    elif market == "USDJPY":
        module = r2cd
        start, end, training_years = r2bc.START, r2bc.END, r2bz.TRAINING_YEARS
        initial_decision = r2bz._decision
        initial_fit = r2bz._fit
        year_start = r2bz._year_start
        slice_records = r2bz._slice
        load_market = r2bz.MARKET
    else:
        raise ValueError(f"Unsupported market: {market}")

    if frozen_ledger is not None:
        delayed_rows = _load_frozen_delayed(market, frozen_ledger)
        records = tuple(row.source for row in delayed_rows)
        source_diagnostics: dict[str, Any] = {
            "frozen_run_id": FROZEN_LEDGER_RUNS[market],
            "ledger_records": len(records),
            "ledger_sha256": hashlib.sha256(frozen_ledger.read_bytes()).hexdigest(),
            "provider_read": "NONE_FROZEN_ARTIFACT_ONLY",
        }
    else:
        if market == "AUDUSD":
            records, source_diagnostics = r2bh._build_records()
        else:
            records, source_diagnostics = r2bz._build_records()

    # Fail closed against silent overwritten hypotheses in the old dictionary join.
    record_keys = tuple(module._record_key(row) for row in records)
    if len(set(record_keys)) != len(records):
        raise ValueError(
            f"{market}: duplicate source/confirmation/entry hypothesis identity; "
            "a dictionary join would silently overwrite a record"
        )

    if frozen_ledger is None:
        m5 = load_m5_window(
            load_market,
            start=start - timedelta(days=2),
            end_exclusive=end + timedelta(days=1),
        )
        by_time = {bar.opened_at: bar for bar in aggregate_complete_m15(m5)}
        if len(by_time) == 0:
            raise ValueError(f"{market}: no complete M15 evidence")
        delayed_rows = tuple(
            module._delayed_record(record, by_time=by_time)
            for record in records
        )
    delayed_by_key = {
        module._record_key(row.source): row for row in delayed_rows
    }
    if len(delayed_by_key) != len(records):
        raise ValueError(f"{market}: non-unique delayed-record identity")

    combined: dict[str, list[Any]] = {arm: [] for arm in ARMS}
    folds: list[dict[str, Any]] = []
    positive_years: Counter[str] = Counter()
    pooled_second: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
    pooled_initial: Counter[str] = Counter()
    pooled_terminal: Counter[str] = Counter()
    pooled_transitions: Counter[str] = Counter()
    pooled_state: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}

    for year in range(start.year + training_years, end.year):
        train_start, oos_start, oos_end = (
            year_start(year - training_years),
            year_start(year),
            year_start(year + 1),
        )
        if not train_start < oos_start < oos_end:
            raise ValueError("Nonchronological fold")
        training = cast(Any, slice_records)(records, train_start, oos_start)
        oos = cast(Any, slice_records)(records, oos_start, oos_end)
        model, fit_meta = cast(Any, initial_fit)(training)

        control_training = tuple(delayed_by_key[module._record_key(row)] for row in training)
        aligned_training, historical_actions = _wait_training_cohort(
            training, model, initial_decision, delayed_by_key, module._record_key
        )
        control_journey, control_fit = module._fit_journey(control_training)
        aligned_journey, aligned_fit = module._fit_journey(aligned_training)
        memories = {
            "CONTROL_ALL": control_journey,
            "WAIT_ALIGNED_DIAGNOSTIC": aligned_journey,
        }
        fold_portfolio: dict[str, list[Any]] = {arm: [] for arm in ARMS}
        initial_counts: Counter[str] = Counter()
        terminal_counts: Counter[str] = Counter()
        secondary_counts: dict[str, Counter[str]] = {
            arm: Counter() for arm in ARMS
        }
        transitions: Counter[str] = Counter()
        states: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
        wait_eligible = 0

        for row in oos:
            action = _initial_action(initial_decision, model, row)
            initial_counts[action.value] += 1
            pooled_initial[action.value] += 1
            if action is CrtPureReasoningAction.EXECUTE:
                for arm in ARMS:
                    fold_portfolio[arm].append(
                        module.ExecutedRecord(
                            row.trade, row.dead_on_arrival, "INITIAL_EXECUTE"
                        )
                    )
                continue
            if action is CrtPureReasoningAction.ABSTAIN:
                continue

            delayed = delayed_by_key[module._record_key(row)]
            if delayed.delayed_trade is None:
                terminal = delayed.terminal_reason or "UNCLASSIFIED_TERMINAL"
                terminal_counts[terminal] += 1
                pooled_terminal[terminal] += 1
                continue

            wait_eligible += 1
            decision_actions: dict[str, str] = {}
            for arm in ARMS:
                second = module._second_decision(memories[arm], delayed)
                second_action = second.action
                if second_action not in (
                    CrtPureReasoningAction.EXECUTE,
                    CrtPureReasoningAction.WAIT,
                    CrtPureReasoningAction.ABSTAIN,
                ):
                    raise ValueError("Invalid second cognitive action")
                secondary_counts[arm][second_action.value] += 1
                pooled_second[arm][second_action.value] += 1
                states[arm][f"{delayed.journey_state}:{second_action.value}"] += 1
                pooled_state[arm][f"{delayed.journey_state}:{second_action.value}"] += 1
                decision_actions[arm] = second_action.value
                if second_action is CrtPureReasoningAction.EXECUTE:
                    if delayed.delayed_doa is None:
                        raise ValueError("executed delayed trade missing DOA")
                    fold_portfolio[arm].append(
                        module.ExecutedRecord(
                            delayed.delayed_trade,
                            delayed.delayed_doa,
                            "WAIT_DELAYED_EXECUTE",
                        )
                    )
            transition = (
                decision_actions["CONTROL_ALL"] + " -> "
                + decision_actions["WAIT_ALIGNED_DIAGNOSTIC"]
            )
            transitions[transition] += 1
            pooled_transitions[transition] += 1

        if sum(initial_counts.values()) != len(oos):
            raise ValueError(f"{market}: initial action accounting mismatch")
        if initial_counts["WAIT"] != sum(terminal_counts.values()) + wait_eligible:
            raise ValueError(f"{market}: missing WAIT path")
        if sum(transitions.values()) != wait_eligible:
            raise ValueError(f"{market}: second-action transitions lost")
        metrics: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            if sum(secondary_counts[arm].values()) != wait_eligible:
                raise ValueError(f"{market}: second action accounting mismatch")
            if len(fold_portfolio[arm]) != (
                initial_counts["EXECUTE"] + secondary_counts[arm]["EXECUTE"]
            ):
                raise ValueError(f"{market}: executed portfolio count mismatch")
            frozen = sorted(
                fold_portfolio[arm], key=lambda item: item.trade.entry_opened_at
            )
            combined[arm].extend(frozen)
            metrics[arm] = module._metrics(tuple(frozen))
            positive_years[arm] += float(metrics[arm]["total_r"]) > 0

        folds.append(
            {
                "year": year,
                "training_start": train_start.isoformat(),
                "oos_start": oos_start.isoformat(),
                "initial_fit": fit_meta,
                "historical_cohort_actions_IN_SAMPLE_DIAGNOSTIC": historical_actions,
                "training_eligible_CONTROL_ALL": sum(
                    row.delayed_trade is not None for row in control_training
                ),
                "training_eligible_WAIT_ALIGNED": len(aligned_training),
                "journey_fit": {
                    "CONTROL_ALL": control_fit,
                    "WAIT_ALIGNED_DIAGNOSTIC": aligned_fit,
                },
                "oos_opportunities": len(oos),
                "oos_initial_actions": dict(initial_counts),
                "oos_wait_terminal": dict(terminal_counts),
                "oos_wait_eligible_second_decision": wait_eligible,
                "oos_second_actions": {
                    arm: dict(secondary_counts[arm]) for arm in ARMS
                },
                "oos_second_transition": dict(transitions),
                "oos_journey_state_actions": {
                    arm: dict(states[arm]) for arm in ARMS
                },
                "oos_portfolios": metrics,
            }
        )

    results = {
        arm: module._metrics(
            tuple(sorted(combined[arm], key=lambda item: item.trade.entry_opened_at))
        )
        for arm in ARMS
    }
    years = len(folds)
    if years == 0:
        raise ValueError(f"{market}: no walk-forward folds")
    reference = _reference_check(market, results["CONTROL_ALL"])
    direct_reproduction = (
        _verify_frozen_report(results["CONTROL_ALL"], frozen_report)
        if frozen_report is not None
        else None
    )
    if not reference["matches_frozen_publication"]:
        raise ValueError(
            f"{market}: CONTROL_ALL failed frozen R2-CC/R2-CD reproduction: {reference}"
        )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market,
        "source_diagnostics": source_diagnostics,
        "source_records": len(records),
        "window_start": start.isoformat(),
        "window_end_exclusive": end.isoformat(),
        "fold_count": years,
        "reproduction_check": reference,
        "frozen_source_report_reproduction": direct_reproduction,
        "results": results,
        "trades_per_year": {
            arm: round(results[arm]["trades"] / years, 8) for arm in ARMS
        },
        "density_ge_170": {
            arm: results[arm]["trades"] / years >= MIN_DENSITY_PER_YEAR
            for arm in ARMS
        },
        "positive_year_fraction": {
            arm: round(positive_years[arm] / years, 8) for arm in ARMS
        },
        "initial_action_counts": dict(pooled_initial),
        "wait_terminal_reasons": dict(pooled_terminal),
        "second_action_counts": {arm: dict(pooled_second[arm]) for arm in ARMS},
        "second_action_transitions": dict(pooled_transitions),
        "journey_state_second_actions": {
            arm: dict(pooled_state[arm]) for arm in ARMS
        },
        "folds": folds,
        "historical_wait_cohort_selection": "IN_SAMPLE_ON_PRIOR_4Y_DIAGNOSTIC_ONLY",
        "candidate_certified": False,
        "fresh_holdout_used": False,
        "automatic_promotion": False,
        "research_only": True,
        "sizing_and_volume_authority": "FORBIDDEN",
        "merge_authorized": False,
        "demo_live_production_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--market", choices=("AUDUSD", "USDJPY"), required=True)
    parser.add_argument("--frozen-ledger", type=Path)
    parser.add_argument("--frozen-report", type=Path)
    args = parser.parse_args()
    if (args.frozen_ledger is None) != (args.frozen_report is None):
        parser.error("--frozen-ledger and --frozen-report must be supplied together")
    report = run_market(
        args.market,
        frozen_ledger=args.frozen_ledger,
        frozen_report=args.frozen_report,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print("VT08_R2CE_WAIT_COHORT_DIAGNOSTIC=" + json.dumps({
        "market": report["market"],
        "results": report["results"],
        "trades_per_year": report["trades_per_year"],
        "reproduction_check": report["reproduction_check"],
    }, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
