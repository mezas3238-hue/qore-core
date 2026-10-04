"""Build explicit CIBO function input/output/consumer/actuation telemetry.

Research-only diagnostic. It does not alter CIBO decisions, Trader logic, Risk,
execution, broker state, or certification state.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation

from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from pathlib import Path
from typing import Any

CF_CODES = tuple(f"CF{i:02d}" for i in range(1, 20))
T_CODES = tuple(f"T{i:02d}" for i in range(1, 21))
GENC_CODES = tuple(f"GEN-C{i}" for i in range(1, 15))
ADVANCED = {"T02", "T03", "T04", "T08", "T10", "T16", "T17"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _coverage_by_code(coverage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = coverage.get("rows")
    if not isinstance(rows, list):
        raise ValueError("coverage rows missing")
    return {
        str(row["capability"]): row
        for row in rows
        if isinstance(row, dict) and row.get("capability")
    }


def _dec(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _direct_ce2i_trace_evidence(
    row: dict[str, Any],
    *,
    next_decision_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Prove selected CE2I paths from canonical runtime trace fields."""

    result: dict[str, dict[str, Any]] = {}
    allocation = row.get("allocation")
    selected = (
        isinstance(allocation, dict)
        and allocation.get("selected_by_cibo_policy") is True
    )
    opportunity = row.get("trader_opportunity")
    cma = row.get("cma")
    qore = row.get("qore_risk")
    release = row.get("capital_release")
    settlement = row.get("settlement")

    if selected and isinstance(opportunity, dict) and isinstance(cma, dict):
        minimum = _dec(opportunity.get("minimum_volume"))
        step = _dec(opportunity.get("volume_step"))
        stop_per_volume = _dec(opportunity.get("stop_loss_per_volume"))
        margin_per_volume = _dec(opportunity.get("margin_per_volume"))
        execution_steps = opportunity.get("minimum_execution_steps")
        pre_risk = _dec(cma.get("pre_ce2i_stop_risk_usd"))
        pre_margin = _dec(cma.get("pre_ce2i_margin_usd"))
        if (
            minimum is not None
            and step is not None
            and step > 0
            and stop_per_volume is not None
            and margin_per_volume is not None
            and pre_risk is not None
            and pre_margin is not None
            and isinstance(execution_steps, int)
            and not isinstance(execution_steps, bool)
            and execution_steps >= 1
            and cma.get("sizing_authority") == "CIBO_CMA"
            and cma.get("risk_request_emitted") is True
        ):
            lifecycle_floor = minimum * Decimal(execution_steps)
            raw = max(minimum, lifecycle_floor)
            aligned_steps = (raw / step).to_integral_value(
                rounding=ROUND_CEILING
            )
            volume = aligned_steps * step
            expected_risk = volume * stop_per_volume
            expected_margin = volume * margin_per_volume
            if pre_risk == expected_risk and pre_margin == expected_margin:
                result["T01"] = {
                    "input_payload": {
                        "minimum_volume": str(minimum),
                        "minimum_execution_steps": execution_steps,
                        "volume_step": str(step),
                        "stop_loss_per_volume": str(stop_per_volume),
                        "margin_per_volume": str(margin_per_volume),
                    },
                    "output_payload": {
                        "minimal_seed_volume": str(volume),
                        "stop_risk_usd": str(pre_risk),
                        "margin_usd": str(pre_margin),
                    },
                    "downstream_consumer": "cma-risk-request",
                    "consumer_action": "minimal-seed-consumed",
                    "decision_changed": True,
                    "economic_effect_observable": pre_risk > 0,
                }

    if (
        selected
        and isinstance(cma, dict)
        and cma.get("risk_request_emitted") is True
        and isinstance(qore, dict)
        and qore.get("status") in {"ALLOW", "REDUCE"}
        and isinstance(qore.get("evidence_id"), str)
        and qore.get("evidence_id")
    ):
        requested = _dec(cma.get("requested_stop_risk_usd"))
        authorized_risk = _dec(qore.get("authorized_stop_risk_usd"))
        authorized_margin = _dec(qore.get("authorized_margin_usd"))
        if (
            requested is not None
            and authorized_risk is not None
            and authorized_margin is not None
        ):
            result["T19"] = {
                "input_payload": {
                    "requested_stop_risk_usd": str(requested),
                    "signal_fingerprint": row.get("signal_fingerprint"),
                },
                "output_payload": {
                    "risk_evidence_id": qore.get("evidence_id"),
                    "risk_disposition": qore.get("status"),
                    "reserved_stop_risk_usd": str(authorized_risk),
                    "reserved_margin_usd": str(authorized_margin),
                },
                "downstream_consumer": "qore-risk-reservation",
                "consumer_action": "capacity-reservation-consumed",
                "decision_changed": True,
                "economic_effect_observable": (
                    authorized_risk > 0 or authorized_margin > 0
                ),
            }

    if isinstance(release, dict) and isinstance(settlement, dict):
        released_risk = _dec(release.get("released_stop_risk_usd"))
        released_margin = _dec(release.get("released_margin_usd"))
        if (
            release.get("tool_code") == "T20"
            and isinstance(release.get("evidence_id"), str)
            and release.get("evidence_id")
            and released_risk is not None
            and released_margin is not None
        ):
            result["T20"] = {
                "input_payload": {
                    "settlement_evidence_id": settlement.get("evidence_id"),
                    "capital_released_at": settlement.get(
                        "capital_released_at"
                    ),
                },
                "output_payload": {
                    "release_evidence_id": release.get("evidence_id"),
                    "released_stop_risk_usd": str(released_risk),
                    "released_margin_usd": str(released_margin),
                },
                "downstream_consumer": "capital-headroom-reconciliation",
                "consumer_action": "released-capacity-restored",
                "decision_changed": True,
                "economic_effect_observable": (
                    released_risk > 0 or released_margin > 0
                ),
            }
            released_at = settlement.get("capital_released_at")
            if (
                isinstance(released_at, str)
                and next_decision_at is not None
                and datetime.fromisoformat(next_decision_at)
                > datetime.fromisoformat(released_at)
            ):
                result["T05"] = {
                    "input_payload": {
                        "release_evidence_id": release.get("evidence_id"),
                        "released_at": released_at,
                        "released_stop_risk_usd": str(released_risk),
                        "released_margin_usd": str(released_margin),
                    },
                    "output_payload": {
                        "next_decision_at": next_decision_at,
                        "risk_headroom_recycled": released_risk > 0,
                        "margin_headroom_recycled": released_margin > 0,
                    },
                    "downstream_consumer": "next-epoch-capital-headroom",
                    "consumer_action": "released-capacity-recycled",
                    "decision_changed": (
                        released_risk > 0 or released_margin > 0
                    ),
                    "economic_effect_observable": (
                        released_risk > 0 or released_margin > 0
                    ),
                }

    if (
        selected
        and isinstance(opportunity, dict)
        and isinstance(qore, dict)
        and qore.get("status") in {"ALLOW", "REDUCE"}
    ):
        authorized_risk = _dec(qore.get("authorized_stop_risk_usd"))
        authorized_margin = _dec(qore.get("authorized_margin_usd"))
        stop_per_volume = _dec(opportunity.get("stop_loss_per_volume"))
        margin_per_volume = _dec(opportunity.get("margin_per_volume"))
        minimum_volume = _dec(opportunity.get("minimum_volume"))
        volume_step = _dec(opportunity.get("volume_step"))
        if (
            authorized_risk is not None
            and authorized_margin is not None
            and stop_per_volume is not None
            and stop_per_volume > 0
            and margin_per_volume is not None
            and margin_per_volume > 0
            and minimum_volume is not None
            and minimum_volume > 0
            and volume_step is not None
            and volume_step > 0
        ):
            current_volume = authorized_risk / stop_per_volume
            if current_volume >= minimum_volume:
                t14_input = CiboDeRiskingInput(
                    current_volume=current_volume,
                    minimum_retained_volume=minimum_volume,
                    volume_step=volume_step,
                    stop_risk_per_volume_usd=stop_per_volume,
                    margin_per_volume_usd=margin_per_volume,
                    maximum_retained_stop_risk_usd=authorized_risk,
                    maximum_retained_margin_usd=authorized_margin,
                    methodology_position_valid=True,
                )
                t14 = plan_dynamic_derisking(t14_input)
                result["T14"] = {
                    "input_payload": {
                        "current_volume": str(current_volume),
                        "minimum_retained_volume": str(minimum_volume),
                        "volume_step": str(volume_step),
                        "stop_risk_per_volume_usd": str(stop_per_volume),
                        "margin_per_volume_usd": str(margin_per_volume),
                        "maximum_retained_stop_risk_usd": str(
                            authorized_risk
                        ),
                        "maximum_retained_margin_usd": str(
                            authorized_margin
                        ),
                        "methodology_position_valid": True,
                    },
                    "output_payload": {
                        "action": t14.action.value,
                        "retained_volume": str(t14.retained_volume),
                        "reduction_volume": str(t14.reduction_volume),
                        "released_stop_risk_usd": str(
                            t14.released_stop_risk_usd
                        ),
                        "released_margin_usd": str(t14.released_margin_usd),
                        "reason": t14.reason,
                    },
                    "downstream_consumer": "cibo-position-risk-envelope",
                    "consumer_action": "dynamic-derisking-evaluated",
                    "decision_changed": t14.reduction_volume > 0,
                    "economic_effect_observable": (
                        t14.released_stop_risk_usd > 0
                        or t14.released_margin_usd > 0
                    ),
                    "diagnostic_only": True,
                }

    return result


def _cognitive_rows(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for code in CF_CODES:
        calls = 0
        expected_rows = 0
        shared_outputs: Counter[str] = Counter()
        function_outputs: Counter[str] = Counter()
        native_statuses: Counter[str] = Counter()
        native_engines: Counter[str] = Counter()
        complete_io = True
        consumer_bound = True
        advisory_boundary = True
        context_effect = True
        native_runtime_valid = True
        for row in opportunities:
            cog = row.get("cognitive_orchestration")
            if not isinstance(cog, dict):
                continue
            if code in cog.get("cf01_cf19_registered_in_separate_capability_exam", []):
                expected_rows += 1
            shared_outputs[
                "|".join(
                    str(cog.get(name))
                    for name in (
                        "mission_disposition",
                        "coordination_disposition",
                        "coordination_request_code",
                    )
                )
            ] += 1
            receipts = cog.get("faculty_receipts", [])
            if not isinstance(receipts, list):
                complete_io = False
                consumer_bound = False
                advisory_boundary = False
                context_effect = False
                native_runtime_valid = False
                continue
            matching = [
                item
                for item in receipts
                if isinstance(item, dict) and item.get("function_code") == code
            ]
            if len(matching) != 1:
                complete_io = False
                consumer_bound = False
                advisory_boundary = False
                context_effect = False
                native_runtime_valid = False
                continue
            receipt = matching[0]
            calls += 1
            input_payload = receipt.get("input_payload")
            output_payload = receipt.get("output_payload")
            output_code = (
                output_payload.get("contribution_code")
                if isinstance(output_payload, dict)
                else None
            )
            function_outputs[str(output_code)] += 1
            complete_io = complete_io and (
                isinstance(input_payload, dict)
                and bool(input_payload)
                and isinstance(output_payload, dict)
                and bool(output_payload)
                and isinstance(receipt.get("input_sha256"), str)
                and str(receipt["input_sha256"]).startswith("sha256:")
                and isinstance(receipt.get("output_sha256"), str)
                and str(receipt["output_sha256"]).startswith("sha256:")
            )
            consumer_bound = consumer_bound and (
                receipt.get("downstream_consumer") == "cibo-functional-coordinator"
                and receipt.get("consumer_action") == "contribution-coordinated"
            )
            advisory_boundary = advisory_boundary and (
                receipt.get("advisory_only") is True
                and receipt.get("economic_authority") is False
                and receipt.get("sizing_authority") is False
                and receipt.get("risk_authority") is False
                and receipt.get("execution_authority") is False
                and receipt.get("outcome_used") is False
            )
            context_effect = context_effect and (
                receipt.get("decision_context_effect") == "evidence-request-context"
            )
            if not isinstance(output_payload, dict):
                native_runtime_valid = False
                continue
            native_called = output_payload.get("native_engine_called")
            native_name = output_payload.get("native_engine_name")
            native_status = output_payload.get("native_engine_status")
            native_output = output_payload.get("native_engine_output")
            native_reason = output_payload.get("native_engine_reason")
            native_statuses[str(native_status)] += 1
            native_engines[str(native_name)] += 1
            valid_status = native_status in {
                "SUCCESS",
                "FAIL_CLOSED",
                "DEPENDENCY_BLOCKED",
                "JUSTIFIED_NOT_APPLICABLE",
            }
            native_runtime_valid = native_runtime_valid and (
                type(native_called) is bool
                and isinstance(native_name, str)
                and bool(native_name)
                and valid_status
                and isinstance(native_output, dict)
                and (
                    native_reason is None
                    or (isinstance(native_reason, str) and bool(native_reason))
                )
                and (
                    (native_status == "JUSTIFIED_NOT_APPLICABLE" and native_called is False)
                    or (
                        native_status != "JUSTIFIED_NOT_APPLICABLE"
                        and native_called is True
                    )
                )
            )

        observed = (
            expected_rows > 0
            and calls == expected_rows
            and complete_io
            and consumer_bound
            and advisory_boundary
            and context_effect
        )
        native_observed = (
            observed
            and native_runtime_valid
            and sum(native_statuses.values()) == calls
        )
        if not observed:
            diagnosis = "OBSERVABILITY_GAP"
        elif not native_observed:
            diagnosis = "NATIVE_ENGINE_TELEMETRY_GAP"
        elif native_statuses == Counter({"SUCCESS": calls}):
            diagnosis = "NATIVE_ENGINE_SUCCESS_CONSUMED_NO_ECONOMIC_ACTUATION"
        elif native_statuses == Counter({"FAIL_CLOSED": calls}):
            diagnosis = "NATIVE_ENGINE_FAIL_CLOSED"
        elif native_statuses == Counter({"DEPENDENCY_BLOCKED": calls}):
            diagnosis = "NATIVE_ENGINE_DEPENDENCY_BLOCKED"
        elif native_statuses == Counter({"JUSTIFIED_NOT_APPLICABLE": calls}):
            diagnosis = "JUSTIFIED_NOT_APPLICABLE_PREDECISION"
        else:
            diagnosis = "MIXED_NATIVE_ENGINE_RUNTIME_STATUS"

        result.append(
            {
                "function_code": code,
                "stage": "COGNITIVE",
                "call_count": calls,
                "expected_trace_rows": expected_rows,
                "per_function_input_observable": observed,
                "per_function_output_observable": observed,
                "downstream_consumer_observable": observed,
                "advisory_consumption_observable": observed,
                "native_runtime_observable": native_observed,
                "native_engine_status_distribution": dict(native_statuses),
                "native_engine_distribution": dict(native_engines),
                "decision_change_observable": False,
                "economic_effect_observable": False,
                "authority_boundary_preserved": advisory_boundary,
                "shared_coordinator_output_distribution": dict(shared_outputs),
                "function_output_distribution": dict(function_outputs),
                "status": diagnosis,
                "diagnosis": diagnosis,
            }
        )
    return result


def _ce2i_rows(
    opportunities: list[dict[str, Any]],
    coverage: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions: dict[str, list[dict[str, Any]]] = {code: [] for code in T_CODES}
    effects: Counter[str] = Counter()
    runtime_receipts: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]] = {
        code: {} for code in T_CODES
    }
    direct_trace_evidence: dict[str, list[dict[str, Any]]] = {
        code: [] for code in T_CODES
    }
    ordered_rows = sorted(
        opportunities,
        key=lambda item: (
            str(item.get("market_decision_at")),
            str(item.get("decision_epoch_id")),
            str(item.get("signal_fingerprint")),
        ),
    )
    next_decision_by_epoch: dict[str, str | None] = {}
    epoch_times: list[tuple[str, str]] = []
    for item in ordered_rows:
        epoch = str(item.get("decision_epoch_id"))
        at = str(item.get("market_decision_at"))
        if not epoch_times or epoch_times[-1][0] != epoch:
            epoch_times.append((epoch, at))
    for index, (epoch, _at) in enumerate(epoch_times):
        next_decision_by_epoch[epoch] = (
            epoch_times[index + 1][1]
            if index + 1 < len(epoch_times)
            else None
        )

    for row in opportunities:
        epoch = str(row.get("decision_epoch_id"))
        for code, evidence in _direct_ce2i_trace_evidence(
            row,
            next_decision_at=next_decision_by_epoch.get(epoch),
        ).items():
            direct_trace_evidence[code].append(evidence)
        ce2i = row.get("ce2i")
        if not isinstance(ce2i, dict):
            continue
        for decision in (
            list(ce2i.get("opportunity_advanced_decisions", []))
            + list(ce2i.get("portfolio_advanced_decisions", []))
        ):
            if isinstance(decision, dict) and decision.get("tool_code") in decisions:
                decisions[str(decision["tool_code"])].append(decision)
        for effect in (
            list(ce2i.get("candidate_economic_effects", []))
            + list(ce2i.get("portfolio_economic_effects", []))
        ):
            if isinstance(effect, dict) and effect.get("tool_code"):
                effects[str(effect["tool_code"])] += 1
        for receipt in ce2i.get("runtime_receipts", []):
            if not isinstance(receipt, dict):
                continue
            code = str(receipt.get("tool_code"))
            if code not in runtime_receipts:
                continue
            key = (
                str(receipt.get("scope_id")),
                str(receipt.get("input_sha256")),
                str(receipt.get("output_sha256")),
                str(receipt.get("engine_name")),
            )
            runtime_receipts[code][key] = receipt

    result = []
    for code in T_CODES:
        cov = coverage.get(code, {})
        rows = decisions[code]
        dispositions = Counter(str(row.get("disposition")) for row in rows)
        reasons = Counter(str(row.get("reason")) for row in rows)
        per_call_output = bool(rows) if code in ADVANCED else False
        effect_count = effects[code]
        receipts = list(runtime_receipts[code].values())
        direct_rows = direct_trace_evidence[code]
        receipt_io_complete = bool(receipts) and all(
            isinstance(item.get("input_payload"), dict)
            and bool(item["input_payload"])
            and isinstance(item.get("output_payload"), dict)
            and bool(item["output_payload"])
            and isinstance(item.get("input_sha256"), str)
            and str(item["input_sha256"]).startswith("sha256:")
            and isinstance(item.get("output_sha256"), str)
            and str(item["output_sha256"]).startswith("sha256:")
            and bool(item.get("downstream_consumer"))
            and bool(item.get("consumer_action"))
            and item.get("native_engine_called") is True
            and item.get("allocation_authority") is False
            and item.get("risk_authority") is False
            and item.get("execution_authority") is False
            and item.get("productive_authority") is False
            and item.get("broker_mutation") is False
            for item in receipts
        )
        direct_io_complete = bool(direct_rows) and all(
            isinstance(item.get("input_payload"), dict)
            and bool(item["input_payload"])
            and isinstance(item.get("output_payload"), dict)
            and bool(item["output_payload"])
            and bool(item.get("downstream_consumer"))
            and bool(item.get("consumer_action"))
            for item in direct_rows
        )
        runtime_io_complete = receipt_io_complete or direct_io_complete
        runtime_changed = sum(
            item.get("decision_changed") is True
            or item.get("economic_effect_observable") is True
            for item in receipts
        ) + sum(
            item.get("decision_changed") is True
            or item.get("economic_effect_observable") is True
            for item in direct_rows
        )
        status = str(cov.get("status", "UNKNOWN"))
        coverage_reason = str(cov.get("reason", ""))
        if runtime_io_complete and runtime_changed > 0:
            diagnosis = "INPUT_OUTPUT_CONSUMER_ACTUATION_OBSERVED"
        elif runtime_io_complete and (
            status == "JUSTIFIED_NOT_APPLICABLE"
            or (
                rows
                and dispositions.get("ABSTAIN", 0) == len(rows)
            )
        ):
            diagnosis = "JUSTIFIED_NOT_APPLICABLE"
        elif runtime_io_complete:
            diagnosis = "INPUT_OUTPUT_CONSUMER_OBSERVED_NO_CHANGE"
        elif status == "JUSTIFIED_NOT_APPLICABLE":
            diagnosis = "JUSTIFIED_NOT_APPLICABLE"
        elif code in ADVANCED and rows:
            if dispositions.get("FAIL_CLOSED", 0) == len(rows):
                diagnosis = "ALL_CALLS_FAIL_CLOSED"
            elif dispositions.get("ABSTAIN", 0) == len(rows):
                diagnosis = "JUSTIFIED_NOT_APPLICABLE"
            elif effect_count > 0:
                diagnosis = "OUTPUT_AND_ECONOMIC_EFFECT_OBSERVED"
            else:
                diagnosis = "OUTPUT_OBSERVED_NO_ECONOMIC_EFFECT"
        elif status == "APPLIED":
            diagnosis = "AGGREGATE_ONLY_PER_CALL_IO_MISSING"
        else:
            diagnosis = "FAIL_CLOSED_OR_UNAVAILABLE"
        result.append(
            {
                "function_code": code,
                "stage": "CE2I",
                "coverage_status": status,
                "coverage_reason": coverage_reason,
                "enabled_epochs": cov.get("enabled_epochs"),
                "applied_count": cov.get("applied_count"),
                "per_call_input_observable": runtime_io_complete,
                "per_call_output_observable": per_call_output or runtime_io_complete,
                "downstream_consumer_observable": (
                    effect_count > 0 or runtime_io_complete
                ),
                "decision_change_observable": (
                    effect_count > 0 or runtime_changed > 0
                ),
                "economic_effect_observable": (
                    effect_count > 0
                    or any(
                        item.get("economic_effect_observable") is True
                        for item in receipts
                    )
                    or any(
                        item.get("economic_effect_observable") is True
                        for item in direct_rows
                    )
                ),
                "advanced_call_count": len(rows),
                "runtime_receipt_count": len(receipts),
                "direct_trace_evidence_count": len(direct_rows),
                "runtime_actuation_count": runtime_changed,
                "economic_effect_count": effect_count,
                "dispositions": dict(dispositions),
                "reason_distribution": dict(reasons),
                "diagnosis": diagnosis,
            }
        )
    return result


def _genc_rows(capital: dict[str, Any]) -> list[dict[str, Any]]:
    calls = capital.get("calls")
    if not isinstance(calls, list):
        raise ValueError("Capital Science calls missing")
    result = []
    for code in GENC_CODES:
        rows = [row for row in calls if row.get("function_code") == code]
        dispositions = Counter(str(row.get("disposition")) for row in rows)
        all_io = bool(rows) and all(
            isinstance(row.get("input_payload"), dict)
            and bool(row["input_payload"])
            and isinstance(row.get("output_payload"), dict)
            and bool(row["output_payload"])
            for row in rows
        )
        consumer_count = sum(
            bool(row.get("downstream_consumer")) and bool(row.get("consumer_action"))
            for row in rows
        )
        changed = sum(bool(row.get("decision_changed")) for row in rows)
        native = sum(bool(row.get("native_engine_called")) for row in rows)
        economic_delta = sum(
            str(row.get(name, "0")) not in {"0", "0.0", "None"}
            for row in rows
            for name in (
                "risk_delta_usd",
                "margin_delta_usd",
                "incremental_pnl_attribution_usd",
            )
        )
        stages = Counter(str(row.get("stage")) for row in rows)
        consumer_actions = Counter(
            str(row.get("consumer_action")) for row in rows
        )
        healthy_no_change = (
            bool(rows)
            and changed == 0
            and economic_delta == 0
            and (
                set(dispositions).issubset(
                    {"ELIGIBLE_NO_CHANGE", "JUSTIFIED_NOT_APPLICABLE"}
                )
                or (
                    code == "GEN-C9"
                    and set(stages) == {"POST_SEGMENT"}
                    and set(consumer_actions)
                    == {"EVALUATE_COMPLETED_CAPITAL_PATH"}
                )
                or (
                    code == "GEN-C10"
                    and set(stages) == {"PREDECISION"}
                    and set(consumer_actions)
                    == {"PUBLISH_CAUSAL_CAPITAL_TWIN"}
                )
                or (
                    code == "GEN-C12"
                    and set(stages) == {"PREDECISION"}
                    and set(consumer_actions)
                    == {"CRISIS_ENVELOPE_ALLOWS_CAPITAL"}
                )
                or (
                    code == "GEN-C13"
                    and set(stages) == {"POST_OUTCOME"}
                    and set(consumer_actions)
                    == {"INGEST_SETTLED_CAPITAL_EPISODE"}
                )
                or (
                    code == "GEN-C14"
                    and set(stages) == {"RESEARCH_GOVERNANCE"}
                    and set(consumer_actions)
                    == {"SEAL_NON_CERTIFYING_RESEARCH_LINEAGE"}
                )
                or (
                    code == "GEN-C2"
                    and set(stages) == {"PREDECISION"}
                    and set(consumer_actions)
                    == {"USE_DEPLOYABLE_PROFIT_ONLY"}
                )
            )
        )
        if not rows:
            diagnosis = "NO_PER_CALL_RUNTIME_RECEIPTS"
        elif not all_io:
            diagnosis = "INPUT_OUTPUT_INCOMPLETE"
        elif consumer_count != len(rows):
            diagnosis = "CONSUMER_BINDING_INCOMPLETE"
        elif (
            dispositions.get("JUSTIFIED_NOT_APPLICABLE", 0) == len(rows)
        ):
            diagnosis = "JUSTIFIED_NOT_APPLICABLE"
        elif changed > 0 or economic_delta > 0:
            diagnosis = "INPUT_OUTPUT_CONSUMER_ACTUATION_OBSERVED"
        elif healthy_no_change:
            diagnosis = "INPUT_OUTPUT_CONSUMER_OBSERVED_NO_CHANGE"
        elif dispositions.get("APPLIED", 0) > 0:
            diagnosis = "APPLIED_WITHOUT_OBSERVABLE_ACTUATION"
        elif dispositions.get("FAIL_CLOSED", 0) == len(rows):
            diagnosis = "ALL_CALLS_FAIL_CLOSED"
        else:
            diagnosis = "INPUT_OUTPUT_CONSUMER_OBSERVED_NO_CHANGE"
        result.append(
            {
                "function_code": code,
                "stage": "CAPITAL_SCIENCE",
                "call_count": len(rows),
                "input_output_complete": all_io,
                "consumer_bound_count": consumer_count,
                "decision_changed_count": changed,
                "native_engine_called_count": native,
                "economic_delta_field_count": economic_delta,
                "dispositions": dict(dispositions),
                "stage_distribution": dict(stages),
                "consumer_action_distribution": dict(consumer_actions),
                "diagnosis": diagnosis,
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--capital-science-io", type=Path, required=True)
    parser.add_argument("--group-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = _load(args.decision_trace)
    coverage_raw = _load(args.coverage)
    capital = _load(args.capital_science_io)
    group = _load(args.group_result)
    opportunities = trace.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise ValueError("decision trace opportunities missing")
    coverage = _coverage_by_code(coverage_raw)

    rows = (
        _cognitive_rows(opportunities)
        + _ce2i_rows(opportunities, coverage)
        + _genc_rows(capital)
    )
    runtime_ok = {
        "OUTPUT_AND_ECONOMIC_EFFECT_OBSERVED",
        "INPUT_OUTPUT_CONSUMER_ACTUATION_OBSERVED",
        "INPUT_OUTPUT_CONSUMER_OBSERVED_ADVISORY",
        "INPUT_OUTPUT_CONSUMER_OBSERVED_NO_CHANGE",
        "NATIVE_ENGINE_SUCCESS_CONSUMED_NO_ECONOMIC_ACTUATION",
        "JUSTIFIED_NOT_APPLICABLE_PREDECISION",
        "JUSTIFIED_NOT_APPLICABLE",
    }
    actuation_ok = {
        "OUTPUT_AND_ECONOMIC_EFFECT_OBSERVED",
        "INPUT_OUTPUT_CONSUMER_ACTUATION_OBSERVED",
        "JUSTIFIED_NOT_APPLICABLE_PREDECISION",
        "JUSTIFIED_NOT_APPLICABLE",
    }
    runtime_blockers = [
        {
            "function_code": row["function_code"],
            "stage": row["stage"],
            "diagnosis": row["diagnosis"],
        }
        for row in rows
        if row["diagnosis"] not in runtime_ok
    ]
    actuation_gaps = [
        {
            "function_code": row["function_code"],
            "stage": row["stage"],
            "diagnosis": row["diagnosis"],
        }
        for row in rows
        if row["diagnosis"] not in actuation_ok
        and row["diagnosis"] not in {
            "NATIVE_ENGINE_FAIL_CLOSED",
            "NATIVE_ENGINE_DEPENDENCY_BLOCKED",
            "ALL_CALLS_FAIL_CLOSED",
            "FAIL_CLOSED_OR_UNAVAILABLE",
            "NO_PER_CALL_RUNTIME_RECEIPTS",
            "INPUT_OUTPUT_INCOMPLETE",
            "CONSUMER_BINDING_INCOMPLETE",
            "NATIVE_ENGINE_TELEMETRY_GAP",
            "OBSERVABILITY_GAP",
            "AGGREGATE_ONLY_PER_CALL_IO_MISSING",
        }
    ]
    blockers = runtime_blockers + actuation_gaps
    payload = {
        "schema": "qore.cibo.function-io-actuation.v1",
        "group_id": group.get("group_id"),
        "function_count": len(rows),
        "functions": rows,
        "runtime_functionality_complete": not runtime_blockers,
        "runtime_blocker_count": len(runtime_blockers),
        "runtime_blockers": runtime_blockers,
        "economic_actuation_coverage_complete": (
            not runtime_blockers and not actuation_gaps
        ),
        "actuation_gap_count": len(actuation_gaps),
        "actuation_gaps": actuation_gaps,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "governance": {
            "diagnostic_only": True,
            "outcome_aware_tuning": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
        },
    }
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": payload["group_id"],
                "economic_actuation_coverage_complete": payload[
                    "economic_actuation_coverage_complete"
                ],
                "blocker_count": payload["blocker_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
