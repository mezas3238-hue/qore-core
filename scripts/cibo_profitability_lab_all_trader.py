"""CIBO Profitability Lab P0: all-Trader participation + runtime coverage.

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
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    build_cibo_capability_cognitive_coverage,
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
from qore.infrastructure.cibo_reused_holdout_capability_exam import (
    _full_metrics,
    _run_minimal_seed_baseline,
    _tool_audit,
)
from qore.infrastructure.cibo_reused_holdout_compound_portfolio_lane import (
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
) -> dict[str, Any]:
    cognitive = build_cibo_capability_cognitive_coverage(
        source_batch_sha256=fresh.declared_batch_sha256,
        observed_at=replay_started_at,
    )
    cf_rows = [
        {
            "capability": f"CF{i:02d}",
            "stage": "COGNITIVE",
            "status": "APPLIED",
            "reason": "capability-exam cognitive coordinator consultation receipt",
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
        and all(row["status"] != "NOT_INTEGRATED" for row in t_rows)
        and all(row["status"] != "NOT_INTEGRATED" for row in genc_rows)
    )
    return {
        "schema": "qore.cibo.profitability-lab.full-stack-coverage.p0.v1",
        "cf01_cf19_complete": cognitive.all_functional_faculties_consulted,
        "t01_t20_registered": cognitive.all_ce2i_tools_registered,
        "full_stack_runtime_coverage_complete": full_complete,
        "rows": cf_rows + t_rows + genc_rows,
        "broker_mutation": False,
        "live": False,
        "real_capital": False,
        "production": False,
        "certification_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--provider-numeric", type=Path, required=True)
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
    projections = project_phase22_execution_inputs(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=args.provider_numeric_freeze_sha256,
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
    )
    compound = run_compound_portfolio_lane(
        plan=plan,
        core_execution=treatment,
        lab_use_executed_core_surface=True,
    )

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
    trader_rows = _trader_rows(execution=treatment, compound=compound)
    coverage = _coverage(
        fresh=fresh,
        replay_started_at=replay_started_at,
        tool_audit=audit,
        compound=compound,
    )
    participation_pass = all(row["participation_pass"] for row in trader_rows)

    result = {
        "schema": "qore.cibo.profitability-lab.all-trader-p0.v1",
        "status": "COMPLETE",
        "validation_mode": "NON_CERTIFYING_REUSED_HOLDOUT_DIAGNOSTIC",
        "treatment": "ALL_TRADER_CMA_QORE_RISK_PLUS_CURRENT_COMPOUND",
        "allocator_role": (
            "LAB_P0_STATIC_TRADER_PRIOR_SIGN_GATE_DISABLED; "
            "REGIME_CAPITAL_MARGIN_CONCENTRATION_AND_QORE_RISK_REMAIN_ACTIVE"
        ),
        "all_candidates_reach_cma_qore_risk": False,
        "all_eligible_candidates_reach_cma_qore_risk": True,
        "seven_of_seven_participation_pass": participation_pass,
        "baseline_minimal_seed": _canonical(baseline_metrics),
        "frozen_cibo_control": _canonical(control_metrics),
        "all_trader_cibo_core": _canonical(treatment_metrics),
        "all_trader_cibo_compound_portfolio": compound.payload(
            core_executed_count=treatment.settled_count
        ),
        "traders": trader_rows,
        "coverage": coverage,
        "governance": {
            "trader_edge_changed": False,
            "outcome_aware_tuning": False,
            "qore_risk_sovereign": True,
            "broker_mutation": False,
            "live": False,
            "real_capital": False,
            "production": False,
            "certification_claimed": False,
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "lab-result.json").write_text(
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
    print(json.dumps({
        "seven_of_seven_participation_pass": participation_pass,
        "all_trader_core_ending_capital_usd": format(
            treatment_metrics.ending_capital_usd, "f"
        ),
        "all_trader_compound_ending_capital_usd": format(
            compound.ending_capital_usd, "f"
        ),
        "full_stack_runtime_coverage_complete": (
            coverage["full_stack_runtime_coverage_complete"]
        ),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
