#!/usr/bin/env python3
"""Replay current CIBO engines directly from a frozen Trader Lab decision trace.

The trace is treated as immutable historical evidence. Predecision rows rebuild
canonical Phase22 candidates and regime evidence. Structural outcomes are placed
only in the disjoint chronological outcome schedule, never in epoch fingerprints
or engine decisions.

This runner is NON_CERTIFYING_REUSED_HOLDOUT research only. It performs no
broker mutation and claims no LIVE/production/generalization authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_regime import (
    phase20_demo_regime_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_phase22_fresh_capital_projection import (
    project_phase22_fresh_capital_input,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution_receipt import (
    PROVIDER_NUMERIC_FREEZE_FILE_SHA256,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    Phase22HistoricalRegimeEvidence,
    execute_phase22_chronological_replay,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    Phase22ChronologicalReplayPlan,
    Phase22DecisionEpochPlan,
    Phase22OutcomeEvent,
    Phase22PredecisionCandidate,
)
from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    load_phase22_sealed_provider_numeric,
)


_STRIP_CONTEXT_KEYS = {
    "phase22_candidate",
    "sizing_authority",
    "trader_sizing_authority",
    "provider_numeric_freeze",
}


def _dec(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise CiboCapitalManagementError("trace replay numeric value not finite")
    return result


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError("trace replay timestamp must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            "trace replay timestamp must be timezone-aware"
        )
    return result


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _decision_context(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    raw = row["trader_opportunity"].get("decision_context", [])
    result = []
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            raise CiboCapitalManagementError(
                "trace replay decision_context row invalid"
            )
        key, value = item
        if key in _STRIP_CONTEXT_KEYS:
            continue
        if not isinstance(key, str) or not isinstance(value, str):
            raise CiboCapitalManagementError(
                "trace replay decision_context must be string pairs"
            )
        result.append((key, value))
    return tuple(result)


def _fresh_from_row(row: dict[str, Any]) -> Phase22FreshOpportunity:
    opp = row["trader_opportunity"]
    outcome = row["evaluation_outcome"]
    decision_sha = str(row["decision_evidence_sha256"])
    return Phase22FreshOpportunity(
        trader_id=TraderLineage(str(row["trader_id"])),
        qore_symbol=str(row["qore_symbol"]),
        signal_fingerprint=str(row["signal_fingerprint"]),
        signal_at=_dt(row["market_decision_at"]),
        entry_at=_dt(outcome["entry_at"]),
        exit_at=_dt(outcome["exit_at"]),
        side=str(opp["side"]),
        entry_price=_dec(opp["intended_entry"]),
        structural_stop=_dec(opp["stop_loss"]),
        technical_target=_dec(opp["take_profit"]),
        exit_reason=str(outcome["exit_reason"]),
        gross_structural_outcome_r=_dec(
            outcome["gross_structural_outcome_r"]
        ),
        methodology_sha256=decision_sha,
        source_evidence_ids=(decision_sha,),
        decision_context=_decision_context(row),
    )


def _regime_input(row: dict[str, Any]) -> dict[str, Any]:
    receipts = row["ce2i"]["runtime_receipts"]
    matches = [
        item
        for item in receipts
        if item.get("engine_name") == "select_ce2i_tools_for_regime"
    ]
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "trace replay requires one regime-selector receipt per row"
        )
    payload = matches[0].get("input_payload")
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "trace replay regime-selector input missing"
        )
    return payload


def _build_plan(
    *,
    trace: dict[str, Any],
    provider_payload: dict[str, Any],
) -> tuple[
    Phase22ChronologicalReplayPlan,
    tuple[Phase22HistoricalRegimeEvidence, ...],
]:
    provider = load_phase22_sealed_provider_numeric(provider_payload)
    rows = trace.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            "trace replay opportunities missing"
        )

    by_epoch: dict[str, list[tuple[dict[str, Any], Phase22PredecisionCandidate]]] = (
        defaultdict(list)
    )
    outcomes = []
    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "trace replay opportunity row must be object"
            )
        fresh = _fresh_from_row(row)
        projection = project_phase22_fresh_capital_input(
            fresh=fresh,
            spec=provider.spec_for(fresh.qore_symbol),
            provider_numeric_freeze_sha256=PROVIDER_NUMERIC_FREEZE_FILE_SHA256,
        )
        candidate = Phase22PredecisionCandidate(
            signal_fingerprint=fresh.signal_fingerprint,
            trader_id=fresh.trader_id.value,
            qore_symbol=fresh.qore_symbol,
            signal_at=fresh.signal_at,
            entry_at=fresh.entry_at,
            projection=projection,
        )
        epoch_id = str(row["decision_epoch_id"])
        by_epoch[epoch_id].append((row, candidate))
        outcomes.append(
            Phase22OutcomeEvent(
                signal_fingerprint=fresh.signal_fingerprint,
                trader_id=fresh.trader_id.value,
                qore_symbol=fresh.qore_symbol,
                entry_at=fresh.entry_at,
                exit_at=fresh.exit_at,
                gross_structural_outcome_r=(
                    fresh.gross_structural_outcome_r
                ),
                exit_reason=fresh.exit_reason,
            )
        )

    epochs = []
    regimes = []
    policy_sha = phase20_demo_regime_policy_sha256()
    for epoch_id, entries in by_epoch.items():
        entries.sort(key=lambda item: item[1].signal_fingerprint)
        market_at = _dt(entries[0][0]["market_decision_at"])
        if any(
            _dt(row["market_decision_at"]) != market_at
            for row, _candidate in entries
        ):
            raise CiboCapitalManagementError(
                "trace replay epoch market clock drift"
            )
        epochs.append(
            Phase22DecisionEpochPlan(
                decision_epoch_id=epoch_id,
                market_decision_at=market_at,
                candidates=tuple(item[1] for item in entries),
            )
        )

        inputs = [_regime_input(row) for row, _candidate in entries]
        first = inputs[0]
        comparable = (
            "liquidity",
            "volatility",
            "correlation",
            "provider_condition",
            "position_path_adverse",
            "evidence_stale",
        )
        if any(
            any(item.get(key) != first.get(key) for key in comparable)
            for item in inputs[1:]
        ):
            raise CiboCapitalManagementError(
                "trace replay regime input drift inside epoch"
            )
        evidence_ids = tuple(
            sorted(
                {
                    str(row["decision_evidence_sha256"])
                    for row, _candidate in entries
                }
            )
        )
        regime_payload = {
            "decision_epoch_id": epoch_id,
            "market_decision_at": market_at.isoformat(),
            **{key: first.get(key) for key in comparable},
            "provider_numeric_freeze_sha256": (
                PROVIDER_NUMERIC_FREEZE_FILE_SHA256
            ),
            "source_evidence_ids": list(evidence_ids),
        }
        stale = bool(first.get("evidence_stale", False))
        regimes.append(
            Phase22HistoricalRegimeEvidence(
                decision_epoch_id=epoch_id,
                observed_at=market_at,
                liquidity=LiquidityState(str(first["liquidity"])),
                volatility=VolatilityState(str(first["volatility"])),
                correlation=CorrelationState(str(first["correlation"])),
                provider_condition=ProviderCondition(
                    str(first["provider_condition"])
                ),
                concentration_limit_by_group=(),
                evidence_sha256=_sha(regime_payload),
                source_evidence_ids=evidence_ids,
                regime_policy_sha256=policy_sha,
                provider_numeric_freeze_sha256=(
                    PROVIDER_NUMERIC_FREEZE_FILE_SHA256
                ),
                market_history_sufficient=not stale,
                counterfactual_provider_model=True,
                historical_provider_state_claimed=False,
                position_path_adverse=bool(
                    first.get("position_path_adverse", False)
                ),
                evidence_stale=stale,
                outcome_fields_used=False,
                target_aware=False,
                productive_authority=False,
            )
        )

    epochs.sort(key=lambda item: (item.market_decision_at, item.decision_epoch_id))
    outcomes.sort(
        key=lambda item: (
            item.exit_at,
            item.signal_fingerprint,
        )
    )
    regimes.sort(
        key=lambda item: (
            item.observed_at,
            item.decision_epoch_id,
        )
    )
    plan = Phase22ChronologicalReplayPlan(
        fresh_batch_sha256=str(trace["trace_sha256"]),
        epochs=tuple(epochs),
        outcome_events=tuple(outcomes),
        trader_ids=CANONICAL_PHASE22_TRADER_IDS,
        future_outcomes_excluded_from_epoch_hashes=True,
        productive_authority=False,
    )
    return plan, tuple(regimes)


def _baseline_metrics(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    row = payload.get("all_trader_cibo_core")
    if not isinstance(row, dict):
        raise CiboCapitalManagementError(
            "trace replay baseline missing all_trader_cibo_core"
        )
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--provider-numeric", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    provider_payload = json.loads(
        args.provider_numeric.read_text(encoding="utf-8")
    )
    baseline_payload = (
        json.loads(args.baseline.read_text(encoding="utf-8"))
        if args.baseline
        else None
    )

    plan, regimes = _build_plan(
        trace=trace,
        provider_payload=provider_payload,
    )
    started = datetime.now(UTC)
    execution = execute_phase22_chronological_replay(
        plan=plan,
        regime_evidence=regimes,
        replay_started_at=started,
        lab_allow_nonpositive_expectation=True,
        lab_cibo_free_tool_choice=True,
        lab_burned_context_quality_gate=True,
        lab_enable_t02_released_capacity=True,
    )

    baseline = _baseline_metrics(baseline_payload)
    current = {
        "initial_capital_usd": format(
            execution.initial_realized_capital_usd, "f"
        ),
        "ending_capital_usd": format(
            execution.final_realized_capital_usd, "f"
        ),
        "net_realized_pnl_usd": format(
            execution.final_realized_capital_usd
            - execution.initial_realized_capital_usd,
            "f",
        ),
        "max_realized_drawdown_usd": format(
            execution.max_realized_capital_drawdown_usd,
            "f",
        ),
        "selected_count": execution.selected_count,
        "allowed_count": execution.allowed_count,
        "reduced_count": execution.reduced_count,
        "rejected_count": execution.rejected_count,
        "settled_count": execution.settled_count,
    }
    comparison: dict[str, Any] | None = None
    if baseline is not None:
        comparison = {
            "ending_capital_delta_usd": format(
                _dec(current["ending_capital_usd"])
                - _dec(baseline["ending_capital_usd"]),
                "f",
            ),
            "net_realized_pnl_delta_usd": format(
                _dec(current["net_realized_pnl_usd"])
                - _dec(baseline["net_realized_pnl_usd"]),
                "f",
            ),
            "max_drawdown_delta_usd": format(
                _dec(current["max_realized_drawdown_usd"])
                - _dec(baseline["max_realized_drawdown_usd"]),
                "f",
            ),
            "executed_count_delta": (
                execution.settled_count
                - int(baseline["executed_count"])
            ),
        }

    result = {
        "schema": "qore.cibo.trace-current-engine-replay.v1",
        "validation_mode": "NON_CERTIFYING_REUSED_HOLDOUT_TRACE_REPLAY",
        "trace_sha256": trace["trace_sha256"],
        "replay_started_at": started.isoformat(),
        "epoch_count": len(plan.epochs),
        "opportunity_count": len(plan.outcome_events),
        "current": current,
        "baseline": baseline,
        "comparison": comparison,
        "governance": {
            "outcomes_used_for_predecision": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
        },
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
