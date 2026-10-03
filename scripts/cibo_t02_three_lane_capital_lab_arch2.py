"""Architect-2 exact three-lane Core/Compound/Compound-Portfolio replay.

Research-only diagnostic. Reuses the frozen V4 population and current provider
counterfactual model. It does not mutate Trader edge, broker state, LIVE,
production, real capital, or certification state.

The control executes the canonical frozen CIBO selector. The treatment keeps
that selector as shadow evidence but sends every legal candidate to CMA +
sovereign QORE Risk so no Trader lane can be eliminated by a Trader-level prior.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    build_cibo_capability_cognitive_coverage,
)
from qore.infrastructure.cibo_phase22_fresh_capital_projection import (
    project_phase22_fresh_capital_input,
)
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    execute_phase22_chronological_replay,
)
from qore.infrastructure.cibo_phase22_v4_chronological_replay_plan import (
    build_phase22_chronological_replay_plan,
)
from qore.infrastructure.cibo_phase22_v4_execution_inputs import (
    load_phase22_sealed_fresh_batch,
    load_phase22_sealed_provider_numeric,
    project_phase22_execution_inputs,
)
from qore.infrastructure.cibo_phase22_v4_historical_regime import (
    PHASE22_REGIME_SYMBOLS,
    build_phase22_historical_regime_evidence,
    load_phase22_historical_regime_corpora,
)
from qore.infrastructure.cibo_profitability_lab_decision_trace import (
    build_cibo_profitability_decision_trace,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    CALIBRATION_MODE,
    POLICY_ID,
)
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    _full_metrics,
    _run_minimal_seed_baseline,
    _tool_audit,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
    POOL_SCOPE_ACCOUNT,
    POOL_SCOPE_TRADER_LOCAL,
    CompoundResearchRedeployAuthorization,
    run_compound_portfolio_lane,
)

TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
GENC = tuple(f"GEN-C{i}" for i in range(1, 15))


def _json_object(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _research_context_by_signal(
    path: Path,
    *,
    source_batch_sha256: str,
    allowed_signals: set[str],
) -> tuple[dict[str, tuple[tuple[str, str], ...]], dict[str, Any]]:
    payload = _json_object(path)
    if payload.get("schema") != "qore.cibo.phase22.reused-context-map.v1":
        raise ValueError("unexpected reused context-map schema")
    if payload.get("mode") != "NON_CERTIFYING_REUSED_HOLDOUT":
        raise ValueError("reused context map must be non-certifying")
    if payload.get("source_batch_sha256") != source_batch_sha256:
        raise ValueError("reused context map source batch drift")
    governance = payload.get("governance")
    if not isinstance(governance, dict):
        raise ValueError("reused context map governance missing")
    for key in (
        "source_batch_mutated",
        "fresh_oos_claimed",
        "certification_claimed",
        "outcome_fields_used_for_context",
        "broker_mutation",
        "live",
        "production",
        "real_capital",
        "merge_authority",
    ):
        if governance.get(key) is not False:
            raise ValueError(f"reused context map governance drift: {key}")

    raw_rows = payload.get("context_rows")
    if not isinstance(raw_rows, dict) or not raw_rows:
        raise ValueError("reused context map rows missing")
    contexts: dict[str, tuple[tuple[str, str], ...]] = {}
    for signal, raw in raw_rows.items():
        if signal not in allowed_signals:
            raise ValueError("reused context map contains foreign signal")
        if not isinstance(raw, dict):
            raise ValueError("reused context map row must be object")
        items = raw.get("decision_context")
        if not isinstance(items, list) or not items:
            raise ValueError("reused context map decision_context missing")
        context: list[tuple[str, str]] = []
        for item in items:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], str)
            ):
                raise ValueError("reused context map entry invalid")
            context.append((item[0], item[1]))
        contexts[str(signal)] = tuple(context)

    expected = int(payload.get("matched_turtle_opportunity_count", 0))
    if expected != len(contexts) or expected != 486:
        raise ValueError("reused context map must cover exact 486 Turtle rows")
    return contexts, {
        "schema": payload["schema"],
        "source_batch_sha256": payload["source_batch_sha256"],
        "matched_turtle_opportunity_count": expected,
        "matched_by_trader": payload.get("matched_by_trader"),
        "source_batch_mutated": False,
        "outcome_fields_used_for_context": False,
    }


def _source_roots(values: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw_path = value.partition("=")
        if not sep or not symbol or not raw_path:
            raise ValueError("source root must be SYMBOL=PATH")
        if symbol in parsed:
            raise ValueError(f"duplicate source root: {symbol}")
        parsed[symbol] = Path(raw_path)
    if set(parsed) != set(PHASE22_REGIME_SYMBOLS):
        raise ValueError("exact five regime source roots required")
    return parsed


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _trader_rows(*, execution: Any, compound: Any) -> list[dict[str, Any]]:
    risk: dict[str, Counter[str]] = defaultdict(Counter)
    for row in execution.books.executed_risk.executed_risk:
        risk[row.trader_id][row.risk_decision.value] += 1

    pnl: dict[str, Decimal] = defaultdict(Decimal)
    entries: Counter[str] = Counter()
    for row in execution.books.cma_settlement.settlements:
        entries[row.trader_id] += 1
        pnl[row.trader_id] += row.realized_net_pnl_usd

    compound_entries = dict(compound.trader_compound_entries)
    compound_pnl = dict(compound.trader_incremental_pnl_usd)

    rows: list[dict[str, Any]] = []
    for trader in TRADERS:
        core_count = entries[trader]
        c_count = int(compound_entries.get(trader, 0))
        rows.append(
            {
                "trader_id": trader,
                "risk_allow": risk[trader]["ALLOW"],
                "risk_reduce": risk[trader]["REDUCE"],
                "risk_reject": risk[trader]["REJECT"],
                "core_entries": core_count,
                "compound_entries": c_count,
                "total_entries": core_count + c_count,
                "core_pnl_usd": format(pnl[trader], "f"),
                "compound_incremental_pnl_usd": format(
                    compound_pnl.get(trader, Decimal(0)), "f"
                ),
                "full_pnl_usd": format(
                    pnl[trader] + compound_pnl.get(trader, Decimal(0)), "f"
                ),
                "participation_pass": core_count > 0,
            }
        )
    return rows


def _coverage(
    *,
    fresh: Any,
    replay_started_at: datetime,
    tool_audit: Any,
    compound: Any,
    decision_trace: dict[str, object],
) -> dict[str, Any]:
    cognitive = build_cibo_capability_cognitive_coverage(
        source_batch_sha256=fresh.declared_batch_sha256,
        observed_at=replay_started_at,
    )
    trace_rows = decision_trace.get("opportunities")
    if not isinstance(trace_rows, list) or not trace_rows:
        raise ValueError("runtime decision trace is required for CF coverage")
    runtime_cf_complete = all(
        isinstance(row, dict)
        and isinstance(row.get("cognitive_orchestration"), dict)
        and row["cognitive_orchestration"].get("runtime_economic_consultation")
        == "PRESENT"
        and len(
            row["cognitive_orchestration"].get(
                "runtime_consulted_faculties",
                [],
            )
        )
        == 19
        for row in trace_rows
    )
    runtime_cognitive_complete = runtime_cf_complete and all(
        row["cognitive_orchestration"].get("mission_director_invoked") is True
        and row["cognitive_orchestration"].get("functional_coordinator_invoked") is True
        and row["cognitive_orchestration"].get("mission_disposition") == "continue"
        and len(row["cognitive_orchestration"].get("mission_faculties", [])) == 19
        and row["cognitive_orchestration"].get("executive_brain_invoked") is False
        and row["cognitive_orchestration"].get("executive_brain_status")
        == "QUARANTINED_RESEARCH_ONLY"
        and row["cognitive_orchestration"].get("legacy_stack_quarantine_preserved")
        is True
        for row in trace_rows
    )
    cf_rows = [
        {
            "capability": f"CF{i:02d}",
            "stage": "COGNITIVE",
            "status": "APPLIED" if runtime_cognitive_complete else "NOT_INTEGRATED",
            "reason": (
                "Mission Director plus CF01-CF19 Coordinator are on the causal "
                "predecision path while legacy Executive Brain remains quarantined"
                if runtime_cognitive_complete
                else "runtime cognitive orchestration incomplete"
            ),
        }
        for i in range(1, 20)
    ]

    t_rows = [
        {
            "capability": row.tool_code,
            "stage": "CE2I",
            "status": row.status.value,
            "reason": row.reason,
            "applied_count": row.applied_count,
            "enabled_epochs": row.enabled_epochs,
        }
        for row in tool_audit
    ]

    compound_by = {
        str(row["function_code"]).split("_", 1)[0]: row
        for row in compound.function_accountability
    }
    genc_rows: list[dict[str, Any]] = []
    for code in GENC:
        raw = compound_by.get(code)
        if raw is not None:
            genc_rows.append(
                {
                    "capability": code,
                    "stage": "CAPITAL_SCIENCE",
                    "status": raw["status"],
                    "reason": raw["reason"],
                    "executed_count": raw["executed_count"],
                }
            )
        else:
            genc_rows.append(
                {
                    "capability": code,
                    "stage": "CAPITAL_SCIENCE",
                    "status": "NOT_INTEGRATED",
                    "reason": (
                        "P0 all-Trader treatment has not yet wired this legal-stage "
                        "capability into the economic replay"
                    ),
                    "executed_count": 0,
                }
            )

    full_complete = (
        cognitive.all_functional_faculties_consulted
        and runtime_cognitive_complete
        and all(row["status"] != "NOT_INTEGRATED" for row in t_rows)
        and all(row["status"] != "NOT_INTEGRATED" for row in genc_rows)
    )
    return {
        "schema": "qore.cibo.profitability-lab.full-stack-coverage.p0.v1",
        "cf01_cf19_complete": cognitive.all_functional_faculties_consulted,
        "cf01_cf19_runtime_economic_consultation_complete": runtime_cf_complete,
        "cognitive_runtime_orchestration_complete": runtime_cognitive_complete,
        "t01_t20_registered": cognitive.all_ce2i_tools_registered,
        "full_stack_runtime_coverage_complete": full_complete,
        "rows": cf_rows + t_rows + genc_rows,
        "broker_mutation": False,
        "live": False,
        "real_capital": False,
        "production": False,
        "certification_claimed": False,
    }


def _compound_research_authorizations(
    plan: Any,
) -> tuple[CompoundResearchRedeployAuthorization, ...]:
    """Predeclare research-only redeploy permission without claiming Fresh OOS.

    This helper reads decision-epoch identity only. It never reads outcome events
    or settlement results. Candidate-level economics remain governed downstream
    by the frozen V2 policy, CMA and sovereign QORE Risk.
    """

    return tuple(
        CompoundResearchRedeployAuthorization(
            signal_fingerprint=candidate.signal_fingerprint,
            known_at=epoch.market_decision_at,
            evidence_id=(
                f"compound-research:{POLICY_ID}:"
                f"{epoch.decision_epoch_id}:{candidate.signal_fingerprint}"
            ),
            policy_id=POLICY_ID,
            calibration_mode=CALIBRATION_MODE,
        )
        for epoch in plan.epochs
        for candidate in epoch.candidates
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--provider-numeric", type=Path, required=True)
    parser.add_argument("--context-map", type=Path)
    parser.add_argument("--provider-numeric-freeze-sha256", required=True)
    parser.add_argument("--source-root", action="append", required=True)
    parser.add_argument("--replay-started-at", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    batch_raw = _json_object(args.batch)
    if batch_raw.get("validation_mode") != "NON_CERTIFYING_REUSED_HOLDOUT":
        raise ValueError("lab requires the frozen reused V4 population")
    fresh = load_phase22_sealed_fresh_batch(batch_raw)
    provider = load_phase22_sealed_provider_numeric(
        _json_object(args.provider_numeric)
    )
    context_summary: dict[str, Any] | None = None
    if args.context_map is None:
        projections = project_phase22_execution_inputs(
            fresh=fresh,
            provider=provider,
            provider_numeric_freeze_sha256=args.provider_numeric_freeze_sha256,
        )
    else:
        allowed_signals = {
            item.signal_fingerprint for item in fresh.batch.opportunities
        }
        context_by_signal, context_summary = _research_context_by_signal(
            args.context_map,
            source_batch_sha256=fresh.declared_batch_sha256,
            allowed_signals=allowed_signals,
        )
        projections = tuple(
            project_phase22_fresh_capital_input(
                fresh=replace(
                    opportunity,
                    decision_context=context_by_signal.get(
                        opportunity.signal_fingerprint,
                        opportunity.decision_context,
                    ),
                ),
                spec=provider.spec_for(opportunity.qore_symbol),
                provider_numeric_freeze_sha256=(
                    args.provider_numeric_freeze_sha256
                ),
            )
            for opportunity in fresh.batch.opportunities
        )
    plan = build_phase22_chronological_replay_plan(
        fresh=fresh,
        projections=projections,
    )
    corpora = load_phase22_historical_regime_corpora(
        _source_roots(args.source_root)
    )
    regimes = build_phase22_historical_regime_evidence(
        plan=plan,
        provider=provider,
        provider_numeric_freeze_sha256=args.provider_numeric_freeze_sha256,
        corpora=corpora,
    )
    replay_started_at = datetime.fromisoformat(args.replay_started_at)

    control = execute_phase22_chronological_replay(
        plan=plan,
        regime_evidence=regimes,
        replay_started_at=replay_started_at,
    )
    treatment = execute_phase22_chronological_replay(
        plan=plan,
        regime_evidence=regimes,
        replay_started_at=replay_started_at,
        lab_allow_nonpositive_expectation=True,
        lab_cibo_free_tool_choice=True,
        lab_enable_t02_released_capacity=True,
    )
    research_authorizations = _compound_research_authorizations(plan)
    leverage_multipliers = tuple(Decimal(str(value)) for value in (1, 2, 3, 4))
    local_by_multiplier = {
        multiplier: run_compound_portfolio_lane(
            plan=plan,
            core_execution=treatment,
            lab_use_executed_core_surface=True,
            lab_require_rational_redeploy=True,
            lab_allow_noncertifying_research_redeploy=True,
            research_redeploy_authorizations=research_authorizations,
            lab_pool_scope=POOL_SCOPE_TRADER_LOCAL,
            lab_seed_multiplier=multiplier,
        )
        for multiplier in leverage_multipliers
    }
    portfolio_by_multiplier = {
        multiplier: run_compound_portfolio_lane(
            plan=plan,
            core_execution=treatment,
            lab_use_executed_core_surface=True,
            lab_require_rational_redeploy=True,
            lab_allow_noncertifying_research_redeploy=True,
            research_redeploy_authorizations=research_authorizations,
            lab_pool_scope=POOL_SCOPE_ACCOUNT,
            lab_seed_multiplier=multiplier,
        )
        for multiplier in leverage_multipliers
    }
    compound_local = local_by_multiplier[Decimal("1")]
    compound_portfolio = portfolio_by_multiplier[Decimal("1")]

    baseline_metrics = _run_minimal_seed_baseline(plan)
    control_metrics = _full_metrics(
        control,
        opportunity_count=len(fresh.batch.opportunities),
    )
    treatment_metrics = _full_metrics(
        treatment,
        opportunity_count=len(fresh.batch.opportunities),
    )
    audit = _tool_audit(plan=plan, execution=treatment)
    trader_rows_compound = _trader_rows(execution=treatment, compound=compound_local)
    trader_rows_portfolio = _trader_rows(
        execution=treatment,
        compound=compound_portfolio,
    )
    decision_trace = build_cibo_profitability_decision_trace(
        execution=treatment,
        compound_function_accountability=compound_portfolio.function_accountability,
    )
    coverage = _coverage(
        fresh=fresh,
        replay_started_at=replay_started_at,
        tool_audit=audit,
        compound=compound_portfolio,
        decision_trace=decision_trace,
    )
    participation_pass = all(
        row["participation_pass"] for row in trader_rows_portfolio
    )

    result = {
        "schema": "qore.cibo.t02-three-lane-capital-lab-arch2.v1",
        "status": "COMPLETE",
        "validation_mode": "NON_CERTIFYING_REUSED_HOLDOUT_DIAGNOSTIC",
        "treatment": (
            "ALL_TRADER_CIBO_FREE_TOOL_CHOICE_CMA_QORE_RISK_"
            "PLUS_FAIL_CLOSED_RATIONAL_COMPOUND_GATE"
        ),
        "allocator_role": (
            "LAB_P0_STATIC_TRADER_PRIOR_SIGN_GATE_DISABLED; "
            "REGIME_CAPITAL_MARGIN_CONCENTRATION_AND_QORE_RISK_REMAIN_ACTIVE"
        ),
        "all_candidates_reach_cma_qore_risk": False,
        "all_eligible_candidates_reach_cma_qore_risk": True,
        "replay_tool_eligibility_authority": False,
        "cibo_free_tool_choice": True,
        "compound_rational_redeploy_gate_preregistered": True,
        "causal_context_reconstruction": context_summary,
        "seven_of_seven_participation_pass": participation_pass,
        "baseline_minimal_seed": _canonical(baseline_metrics),
        "frozen_cibo_control": _canonical(control_metrics),
        "all_trader_cibo_core": _canonical(treatment_metrics),
        "all_trader_cibo_compound": compound_local.payload(
            core_executed_count=treatment.settled_count
        ),
        "all_trader_cibo_compound_portfolio": compound_portfolio.payload(
            core_executed_count=treatment.settled_count
        ),
        "compound_leverage_sweep": {
            format(multiplier, "f"): result.payload(
                core_executed_count=treatment.settled_count
            )
            for multiplier, result in local_by_multiplier.items()
        },
        "compound_portfolio_leverage_sweep": {
            format(multiplier, "f"): result.payload(
                core_executed_count=treatment.settled_count
            )
            for multiplier, result in portfolio_by_multiplier.items()
        },
        "portfolio_incremental_over_local_compound": {
            "ending_capital_delta_usd": format(
                compound_portfolio.ending_capital_usd
                - compound_local.ending_capital_usd,
                "f",
            ),
            "incremental_pnl_delta_usd": format(
                compound_portfolio.compound_incremental_pnl_usd
                - compound_local.compound_incremental_pnl_usd,
                "f",
            ),
            "additional_settlements": (
                compound_portfolio.compound_settled_count
                - compound_local.compound_settled_count
            ),
            "cross_trader_deployments": (
                compound_portfolio.cross_trader_compound_deployments
            ),
        },
        "traders_compound": trader_rows_compound,
        "traders_compound_portfolio": trader_rows_portfolio,
        "coverage": coverage,
        "decision_trace": decision_trace,
        "governance": {
            "trader_edge_changed": False,
            "outcome_aware_tuning": False,
            "reused_context_map_applied": context_summary is not None,
            "qore_risk_sovereign": True,
            "broker_mutation": False,
            "live": False,
            "real_capital": False,
            "production": False,
            "certification_claimed": False,
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "three-lane-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "all-trader-execution.json").write_text(
        json.dumps(_canonical(treatment), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "full-stack-coverage.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "decision-trace.json").write_text(
        json.dumps(decision_trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "seven_of_seven_participation_pass": participation_pass,
        "all_trader_core_ending_capital_usd": format(
            treatment_metrics.ending_capital_usd, "f"
        ),
        "all_trader_compound_ending_capital_usd": format(
            compound_local.ending_capital_usd, "f"
        ),
        "all_trader_compound_portfolio_ending_capital_usd": format(
            compound_portfolio.ending_capital_usd, "f"
        ),
        "portfolio_incremental_over_local_compound_usd": format(
            compound_portfolio.ending_capital_usd
            - compound_local.ending_capital_usd,
            "f",
        ),
        "compound_leverage_ending_capital_usd": {
            format(multiplier, "f"): format(result.ending_capital_usd, "f")
            for multiplier, result in local_by_multiplier.items()
        },
        "compound_portfolio_leverage_ending_capital_usd": {
            format(multiplier, "f"): format(result.ending_capital_usd, "f")
            for multiplier, result in portfolio_by_multiplier.items()
        },
        "full_stack_runtime_coverage_complete": (
            coverage["full_stack_runtime_coverage_complete"]
        ),
        "decision_trace_sha256": decision_trace["trace_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
