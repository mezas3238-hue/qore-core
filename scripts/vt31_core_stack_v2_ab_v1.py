"""VT31 certified economics vs QORE CORE STACK V2 executed-decision A/B.

Stage 1 deliberately covers only decisions that became certified VT31 trades.
It proves that adding Shared Core as a causal shadow sidecar preserves every
certified trade row and its economics while measuring Core+adapter overhead.

This stage does NOT claim WAIT/ABSTAIN coverage. A later decision-universe A/B
must instrument the full VT31 source/reasoning stream, including non-trades.
"""
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from time import perf_counter_ns
from typing import cast

import vt31_nas100_capacity_selective_target_ladder_v1 as frontier
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_candidate_5y_validation_v1 as fivey
import vt31_nas100_structural_target_candidate_v1 as candidate

from qore.infrastructure.core_stack_v2 import (
    DecisionObservation,
    MarketEvent,
    build_snapshot,
    freeze_facts,
    summarize_decision_ab,
)
from qore.infrastructure.traders.vt31_core_stack_v2_adapter import VT31CoreAdapter

SCHEMA = "qore.core_stack_v2.vt31.executed_decision_ab.v1"
IDENTITY = "VT31_CURRENT_VS_QORE_CORE_STACK_V2_EXECUTED_DECISION_AB_V1"
START_DATE = date(2017, 7, 1)
END_EXCLUSIVE_DATE = date(2022, 7, 1)
EXPECTED_BASELINE_ARTIFACT_ID = 10607439608

# Every value copied into Core is explicitly causal at authorization time.
CAUSAL_ROW_FIELDS = (
    "side",
    "tier",
    "entry_family",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
    "authorization_reason",
)

# These may exist in retained rows for economic replay but may never enter Core.
FORBIDDEN_CORE_FIELDS = (
    "r_multiple",
    "capital_weighted_net_r",
    "exit_at",
    "exit_reason",
    "mfe_r",
    "mae_r",
    "loss_path_class",
    "future_journey_label",
    "terminal_pnl",
)


def _canonical_digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_certified_rows(
    *,
    r8_path: Path,
    r6_path: Path,
    r5_path: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    (
        series,
        account,
        evidence_fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = fivey._stitch((r8_path, r6_path, r5_path))

    def stitched_loader(
        _path: Path,
    ) -> tuple[tuple[object, ...], str, str, datetime, str, str]:
        return (
            series,
            account,
            evidence_fingerprint,
            checked_at,
            software_sha,
            provider,
        )

    original_residual_loader = residual.load_market_evidence
    original_frontier_loader = frontier.load_market_evidence
    residual.load_market_evidence = stitched_loader
    frontier.load_market_evidence = stitched_loader
    try:
        evaluation = candidate.evaluate(
            Path("STITCHED_IMMUTABLE_5Y_EVIDENCE"),
            partition="core_stack_v2_executed_decision_ab",
            include_rows=True,
        )
    finally:
        residual.load_market_evidence = original_residual_loader
        frontier.load_market_evidence = original_frontier_loader

    rows = [
        row
        for row in cast(list[dict[str, object]], evaluation.pop("trade_rows"))
        if START_DATE
        <= date.fromisoformat(cast(str, row["local_date"]))
        < END_EXCLUSIVE_DATE
    ]
    return rows, {
        "account_fingerprint": account,
        "evidence_fingerprint": evidence_fingerprint,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "provider_symbol_name": provider,
        "source_records": records,
        "candidate_contract_fingerprint": evaluation["contract_fingerprint"],
    }


def _core_facts(row: dict[str, object]) -> dict[str, str]:
    selected = {
        field: str(row.get(field, "UNKNOWN"))
        for field in CAUSAL_ROW_FIELDS
    }
    if any(field in selected for field in FORBIDDEN_CORE_FIELDS):
        raise AssertionError("forbidden post-outcome field entered Core facts")

    volatility = selected["reference_volatility_state"].upper()
    return {
        "market_state": "VT31_CERTIFIED_EXECUTED_DECISION",
        "session_state": "NY_AM_SILVER_BULLET",
        "liquidity_state": selected["last_structure_event_family"],
        "structure_state": selected["authorization_reason"],
        "volatility_state": volatility,
        "expansion_state": (
            "EXPANSION" if volatility == "EXPANDED" else "NOT_EXPANDED"
        ),
        "compression_state": (
            "COMPRESSION" if volatility == "COMPRESSED" else "NOT_COMPRESSED"
        ),
        "directional_state": selected["side"].upper(),
        "reversal_state": "SPECIALIST_AUTHORIZED",
        "continuation_state": "SPECIALIST_UNRESOLVED",
        **{f"vt31:{key}": value for key, value in selected.items()},
    }


def evaluate(
    *,
    baseline_path: Path,
    r8_path: Path,
    r6_path: Path,
    r5_path: Path,
) -> dict[str, object]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline["candidate_id"] != candidate.CANDIDATE_ID:
        raise AssertionError("baseline candidate identity drift")
    if baseline["selected_variant"] != candidate.SELECTED_VARIANT:
        raise AssertionError("baseline selected variant drift")
    if baseline["contract_fingerprint"] != candidate.contract_fingerprint():
        raise AssertionError("baseline candidate contract fingerprint drift")

    rows, evidence = _load_certified_rows(
        r8_path=r8_path,
        r6_path=r6_path,
        r5_path=r5_path,
    )
    if evidence["candidate_contract_fingerprint"] != baseline["contract_fingerprint"]:
        raise AssertionError("replayed candidate contract fingerprint drift")

    before_digest = _canonical_digest(rows)
    current_metrics = residual._metrics(rows)
    baseline_metrics = cast(dict[str, object], baseline["result"])["metrics"]
    economic_metrics_exact = current_metrics == baseline_metrics

    adapter = VT31CoreAdapter()
    observations: list[DecisionObservation] = []
    context_fingerprints: list[str] = []
    snapshot_fingerprints: list[str] = []
    authority_violations = 0

    for sequence, row in enumerate(rows, start=1):
        signal_at = datetime.fromisoformat(cast(str, row["signal_at"]))
        event = MarketEvent(
            event_id=f"VT31_EXECUTED:{sequence}:{row['signal_at']}",
            market="NAS100",
            event_type="VT31_EXECUTED_DECISION",
            source_at=signal_at,
            observed_at=signal_at,
            sequence=sequence,
            complete=True,
            timeframe_seconds=None,
            facts=freeze_facts(_core_facts(row)),
        )

        started = perf_counter_ns()
        snapshot = build_snapshot(
            events=(event,),
            generated_at=signal_at,
        )
        context = adapter.adapt(snapshot)
        latency_us = max(0, (perf_counter_ns() - started) // 1_000)

        if (
            snapshot.order_authority
            or snapshot.risk_authority
            or snapshot.strategy_mutation_authority
            or context.order_authority
            or context.risk_authority
            or context.methodology_mutation_allowed
        ):
            authority_violations += 1

        decision_fingerprint = _canonical_digest(
            {
                field: row.get(field)
                for field in CAUSAL_ROW_FIELDS
            }
        )
        observations.append(
            DecisionObservation(
                trader_id="VT31_NAS100",
                observation_id=f"{sequence}:{row['signal_at']}",
                baseline_action="EXECUTE",
                v2_action=(
                    "EXECUTE" if context.core_context_valid else "ABSTAIN"
                ),
                baseline_fingerprint=decision_fingerprint,
                v2_fingerprint=decision_fingerprint,
                core_context_valid=context.core_context_valid,
                end_to_end_latency_us=latency_us,
            )
        )
        context_fingerprints.append(context.fingerprint())
        snapshot_fingerprints.append(snapshot.fingerprint())

    after_digest = _canonical_digest(rows)
    ab_summary = summarize_decision_ab(tuple(observations))
    parity = {
        "trade_rows_unchanged": before_digest == after_digest,
        "trade_count_exact": len(rows)
        == int(cast(dict[str, object], baseline["result"])["trade_count"]),
        "economic_metrics_exact": economic_metrics_exact,
        "decision_deltas": ab_summary.decision_deltas,
        "invalid_core_contexts": ab_summary.invalid_core_contexts,
        "authority_violations": authority_violations,
        "latency_p50_us": ab_summary.latency_p50_us,
        "latency_p95_us": ab_summary.latency_p95_us,
        "latency_p99_us": ab_summary.latency_p99_us,
        "latency_p99_le_2s": ab_summary.latency_p99_us <= 2_000_000,
    }
    passes_stage1 = (
        parity["trade_rows_unchanged"]
        and parity["trade_count_exact"]
        and parity["economic_metrics_exact"]
        and parity["decision_deltas"] == 0
        and parity["invalid_core_contexts"] == 0
        and parity["authority_violations"] == 0
        and parity["latency_p99_le_2s"]
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "ab_stage": "EXECUTED_DECISION_PRESERVATION",
        "baseline_artifact_id": EXPECTED_BASELINE_ARTIFACT_ID,
        "candidate_id": candidate.CANDIDATE_ID,
        "selected_variant": candidate.SELECTED_VARIANT,
        "contract_fingerprint": candidate.contract_fingerprint(),
        "window": {
            "start": START_DATE.isoformat(),
            "end_exclusive": END_EXCLUSIVE_DATE.isoformat(),
            "evidence_status": "CONSUMED_EXTENDED_VALIDATION",
            "fresh": False,
        },
        "evidence": evidence,
        "baseline_economics": baseline["result"],
        "v2_economics": {
            "trade_count": len(rows),
            "metrics": current_metrics,
            "identical_to_baseline_by_unchanged_trade_rows": (
                economic_metrics_exact and before_digest == after_digest
            ),
        },
        "executed_decision_parity": parity,
        "snapshot_fingerprint_digest": _canonical_digest(snapshot_fingerprints),
        "context_fingerprint_digest": _canonical_digest(context_fingerprints),
        "passes_stage1": passes_stage1,
        "coverage": {
            "executed_trade_decisions": len(rows),
            "wait_decisions": "NOT_MEASURED_IN_STAGE1",
            "abstain_decisions": "NOT_MEASURED_IN_STAGE1",
            "invalidated_decisions": "NOT_MEASURED_IN_STAGE1",
            "full_decision_universe_ab_complete": False,
        },
        "governance": {
            "vt31_methodology_changed": False,
            "trade_rows_modified": False,
            "core_order_authority": False,
            "core_risk_authority": False,
            "adapter_order_authority": False,
            "adapter_risk_authority": False,
            "future_outcome_fields_used_by_core": False,
            "parameter_scan": False,
            "retuning": False,
            "opens_new_holdout": False,
            "vt08_forex_touched": False,
            "capitalizer_touched": False,
            "live_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--r8", required=True, type=Path)
    parser.add_argument("--r6", required=True, type=Path)
    parser.add_argument("--r5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = evaluate(
        baseline_path=args.baseline,
        r8_path=args.r8,
        r6_path=args.r6,
        r5_path=args.r5,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ab_stage": payload["ab_stage"],
                "candidate_id": payload["candidate_id"],
                "executed_decision_parity": payload["executed_decision_parity"],
                "v2_economics": payload["v2_economics"],
                "coverage": payload["coverage"],
                "passes_stage1": payload["passes_stage1"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
