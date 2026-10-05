#!/usr/bin/env python3
"""Build the provider-neutral reasoning-request ledger for the single-account run.

This is a preflight, not an economic replay. It reconstructs each opportunity,
executes the sovereign CF01-CF19 consultation, and materializes the exact
CiboReasoningRequest that the existing adaptive reasoning runtime will consume.

No provider/model call is made here. No outcome is supplied to cognition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_adaptive_reasoning_runtime import (
    cibo_reasoning_request_digest,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)
from qore.infrastructure.cibo_sovereign_reasoning_request import (
    build_sovereign_reasoning_request,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            "reasoning-request ledger timestamp must be string"
        )
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            "reasoning-request ledger timestamp must be timezone-aware"
        )
    return result


def _opportunity(row: dict[str, Any]) -> TraderOpportunityEnvelope:
    payload = row["trader_opportunity"]
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "reasoning-request ledger opportunity payload missing"
        )
    context = tuple(
        (str(item[0]), str(item[1]))
        for item in payload.get("decision_context", ())
    )
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage(str(row["trader_id"])),
        signal_fingerprint=str(row["signal_fingerprint"]),
        qore_symbol=str(row["qore_symbol"]),
        provider_symbol=str(
            payload.get("provider_symbol") or row["qore_symbol"]
        ),
        side=str(payload["side"]),
        entry_type=str(payload.get("entry_type", "market")),
        intended_entry=_d(payload["intended_entry"]),
        stop_loss=_d(payload["stop_loss"]),
        take_profit=_d(payload["take_profit"]),
        stop_loss_per_volume=_d(payload["stop_loss_per_volume"]),
        margin_per_volume=_d(payload["margin_per_volume"]),
        volume_step=_d(payload["volume_step"]),
        minimum_volume=_d(payload["minimum_volume"]),
        maximum_volume=_d(payload["maximum_volume"]),
        minimum_execution_steps=int(
            payload.get("minimum_execution_steps", 1)
        ),
        decision_context=context,
    )


def _regime(row: dict[str, Any]) -> CiboCapitalRegimeState:
    ce2i = row.get("ce2i_predecision_evidence")
    if not isinstance(ce2i, dict):
        raise CiboCapitalManagementError(
            "reasoning-request ledger CE2I evidence missing"
        )
    receipts = ce2i.get("runtime_receipts")
    if not isinstance(receipts, list):
        raise CiboCapitalManagementError(
            "reasoning-request ledger CE2I runtime receipts missing"
        )
    candidates = [
        item
        for item in receipts
        if isinstance(item, dict)
        and item.get("engine_name") == "select_ce2i_tools_for_regime"
    ]
    if len(candidates) != 1:
        raise CiboCapitalManagementError(
            "reasoning-request ledger requires one regime receipt"
        )
    payload = candidates[0].get("input_payload")
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "reasoning-request ledger regime input missing"
        )
    return CiboCapitalRegimeState(
        liquidity=LiquidityState(str(payload["liquidity"])),
        volatility=VolatilityState(str(payload["volatility"])),
        correlation=CorrelationState(str(payload["correlation"])),
        provider_condition=ProviderCondition(
            str(payload["provider_condition"])
        ),
        risk_utilization=_d(payload["risk_utilization"]),
        margin_utilization=_d(payload["margin_utilization"]),
        drawdown_utilization=_d(payload["drawdown_utilization"]),
        opportunity_count=1,
        position_path_adverse=bool(
            payload.get("position_path_adverse", False)
        ),
        evidence_stale=bool(payload.get("evidence_stale", False)),
    )


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_ledger(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != (
        "qore.cibo.single-account-7trader-maximum-capability.v1"
    ):
        raise CiboCapitalManagementError(
            "reasoning-request ledger requires canonical single-account manifest"
        )
    if manifest.get("account_count") != 1:
        raise CiboCapitalManagementError(
            "reasoning-request ledger requires one account"
        )
    if manifest.get("account_reset_count") != 0:
        raise CiboCapitalManagementError(
            "reasoning-request ledger forbids account reset"
        )
    if manifest.get("economic_era_reset_count") != 0:
        raise CiboCapitalManagementError(
            "reasoning-request ledger forbids era reset"
        )

    opportunities = manifest.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise CiboCapitalManagementError(
            "reasoning-request ledger population is empty"
        )

    rows: list[dict[str, Any]] = []
    trader_counts: Counter[str] = Counter()
    max_prompt_chars = 0
    min_prompt_chars: int | None = None
    total_prompt_chars = 0

    for row in opportunities:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "reasoning-request ledger row must be object"
            )
        if row.get("outcome_available_to_predecision") is not False:
            raise CiboCapitalManagementError(
                "reasoning-request ledger detected outcome availability"
            )

        opportunity = _opportunity(row)
        decision_at = _dt(row["market_decision_at"])
        regime = _regime(row)
        consultation = consult_cibo_economic_faculties(
            decision_at=decision_at,
            opportunities=(opportunity,),
            regime_state=regime,
        )
        request = build_sovereign_reasoning_request(
            consultation=consultation,
            opportunity=opportunity,
        )
        prompt_lower = request.prompt.lower()
        for forbidden in (
            "settlement_outcome_research_only",
            "gross_structural_outcome_r",
            "realized_net_pnl",
            "future_outcome",
        ):
            if forbidden in prompt_lower:
                raise CiboCapitalManagementError(
                    "reasoning-request ledger outcome leakage detected"
                )
        if len(consultation.faculty_receipts) != 19:
            raise CiboCapitalManagementError(
                "reasoning-request ledger faculty surface drift"
            )
        called = sum(
            1
            for item in consultation.faculty_receipts
            if item.output_payload["native_engine_called"]
        )
        full_semantic = sum(
            1
            for item in consultation.faculty_receipts
            if item.output_payload["native_engine_called"]
            and item.output_payload["native_engine_output"].get(
                "semantic_transport"
            )
            == "FULL_CANONICAL_READ_ONLY"
        )
        if full_semantic != called:
            raise CiboCapitalManagementError(
                "reasoning-request ledger semantic transport incomplete"
            )

        prompt_chars = len(request.prompt)
        max_prompt_chars = max(max_prompt_chars, prompt_chars)
        min_prompt_chars = (
            prompt_chars
            if min_prompt_chars is None
            else min(min_prompt_chars, prompt_chars)
        )
        total_prompt_chars += prompt_chars
        trader_counts[opportunity.trader_id.value] += 1

        rows.append(
            {
                "decision_epoch_id": row["decision_epoch_id"],
                "market_decision_at": decision_at.isoformat(),
                "signal_fingerprint": opportunity.signal_fingerprint,
                "trader_id": opportunity.trader_id.value,
                "qore_symbol": opportunity.qore_symbol,
                "consultation_id": consultation.consultation_id,
                "reasoning_request_id": str(request.request_id),
                "reasoning_request_digest": cibo_reasoning_request_digest(
                    request
                ),
                "reasoning_subject_code": request.subject_code,
                "prompt_chars": prompt_chars,
                "faculty_count": len(consultation.faculty_receipts),
                "native_called_count": called,
                "full_semantic_native_count": full_semantic,
                "outcome_used": consultation.outcome_used,
                "broker_mutation": consultation.broker_mutation,
            }
        )

    ledger = {
        "schema": "qore.cibo.single-account-reasoning-request-ledger.v1",
        "source_manifest_sha256": manifest["manifest_sha256"],
        "decision_count": len(rows),
        "trader_counts": dict(sorted(trader_counts.items())),
        "minimum_prompt_chars": min_prompt_chars or 0,
        "maximum_prompt_chars": max_prompt_chars,
        "average_prompt_chars": (
            total_prompt_chars // len(rows) if rows else 0
        ),
        "all_decisions_cf01_cf19_consulted": True,
        "all_applicable_native_semantics_full": True,
        "outcome_used_for_predecision": False,
        "broker_mutation": False,
        "rows": rows,
    }
    ledger["ledger_sha256"] = _sha(ledger)
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    ledger = build_ledger(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ledger_sha256": ledger["ledger_sha256"],
                "decision_count": ledger["decision_count"],
                "trader_counts": ledger["trader_counts"],
                "minimum_prompt_chars": ledger["minimum_prompt_chars"],
                "maximum_prompt_chars": ledger["maximum_prompt_chars"],
                "average_prompt_chars": ledger["average_prompt_chars"],
                "outcome_used_for_predecision": ledger[
                    "outcome_used_for_predecision"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
