"""Read-only per-opportunity decision trace for the CIBO profitability lab.

The trace is deliberately descriptive. It never chooses a Trader, changes a
policy, sizes capital, calls Risk, mutates provider state, or reads future
outcomes to alter a decision. Missing runtime links are recorded as ABSENT or
NOT_INTEGRATED instead of being inferred from capability-registration receipts.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_v4_chronological_execution import (
    Phase22HistoricalExecutionReport,
)

_CF_CODES = tuple(f"CF{index:02d}" for index in range(1, 20))
_T_CODES = tuple(f"T{index:02d}" for index in range(1, 21))
_GENC_CODES = tuple(f"GEN-C{index}" for index in range(1, 15))


def build_cibo_profitability_decision_trace(
    *,
    execution: Phase22HistoricalExecutionReport,
    compound_function_accountability: Iterable[dict[str, object]] = (),
) -> dict[str, object]:
    """Reconstruct the observed economic path without changing it."""

    if not isinstance(execution, Phase22HistoricalExecutionReport):
        raise CiboCapitalManagementError(
            "profitability decision trace requires Phase22HistoricalExecutionReport"
        )

    books = execution.books
    policies = {
        item.evidence_sha256: item for item in books.holdout_policy.decisions
    }
    risks = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in books.executed_risk.executed_risk
    }
    settlements = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in books.cma_settlement.settlements
    }
    releases = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in books.t20_release.release_chain
    }
    genc = _genc_accountability(compound_function_accountability)

    rows: list[dict[str, object]] = []
    for decision in sorted(
        books.holdout_evidence.decisions,
        key=lambda item: (item.decision_at, item.decision_epoch_id),
    ):
        policy = policies.get(decision.evidence_sha256)
        if policy is None:
            raise CiboCapitalManagementError(
                "profitability trace missing policy for decision evidence"
            )
        decision_payload = _json_object(
            decision.canonical_payload_json,
            "decision",
        )
        policy_payload = _json_object(
            policy.canonical_record_json,
            "policy",
        )
        candidate_rows = decision_payload.get("candidates")
        if not isinstance(candidate_rows, list):
            raise CiboCapitalManagementError(
                "profitability trace decision candidates missing"
            )
        full_surface = _object(
            policy_payload.get("full_surface"),
            "full_surface",
        )
        regime = _object(full_surface.get("regime"), "regime")
        enabled_tools = _string_tuple(
            regime.get("enabled_tools"),
            "enabled_tools",
        )
        advanced_by_signal = _advanced_by_signal(full_surface)
        portfolio_decisions = _list_of_objects(
            full_surface.get("portfolio_decisions", []),
            "portfolio_decisions",
        )
        allocation_rows = _allocation_rows(policy_payload)
        consultation = _object(
            policy_payload.get("economic_consultation"),
            "economic_consultation",
        )
        consulted_faculties = _string_tuple(
            consultation.get("consulted_faculties"),
            "consulted_faculties",
        )
        if len(consulted_faculties) != 19:
            raise CiboCapitalManagementError(
                "profitability trace requires exact runtime CF01-CF19 consultation"
            )
        economic_application = _object(
            policy_payload.get("advanced_economic_application"),
            "advanced_economic_application",
        )
        effective_candidates = {
            _required_string(item.get("signal_fingerprint"), "signal_fingerprint"): item
            for item in _list_of_objects(
                economic_application.get("candidates", []),
                "advanced economic candidates",
            )
        }
        candidate_effects = _list_of_objects(
            economic_application.get("candidate_effects", []),
            "advanced candidate effects",
        )
        portfolio_effects = _list_of_objects(
            economic_application.get("portfolio_effects", []),
            "advanced portfolio effects",
        )

        for raw_candidate in candidate_rows:
            candidate_row = _object(raw_candidate, "candidate row")
            opportunity = _object(
                candidate_row.get("opportunity"),
                "opportunity",
            )
            candidate = _object(candidate_row.get("candidate"), "candidate")
            signal = _required_string(
                opportunity.get("signal_fingerprint"),
                "signal_fingerprint",
            )
            trader_id = _required_string(
                opportunity.get("trader_id"),
                "trader_id",
            )
            qore_symbol = _required_string(
                opportunity.get("qore_symbol"),
                "qore_symbol",
            )
            key = (decision.evidence_sha256, signal)
            risk = risks.get(key)
            settlement = settlements.get(key)
            release = releases.get(key)
            allocation = allocation_rows.get(signal)
            effective_candidate = effective_candidates.get(signal)
            if effective_candidate is None:
                raise CiboCapitalManagementError(
                    "profitability trace missing effective economic candidate"
                )
            signal_effects = [
                item
                for item in candidate_effects
                if item.get("signal_fingerprint") == signal
            ]
            selected = signal in policy.selected_signal_fingerprints

            if selected != (risk is not None):
                raise CiboCapitalManagementError(
                    "profitability trace CIBO selection/Risk lineage drift"
                )
            if settlement is not None and risk is None:
                raise CiboCapitalManagementError(
                    "profitability trace settlement without Risk lineage"
                )
            if release is not None and settlement is None:
                raise CiboCapitalManagementError(
                    "profitability trace release without settlement lineage"
                )

            rows.append(
                {
                    "decision_epoch_id": decision.decision_epoch_id,
                    "market_decision_at": decision.decision_at.isoformat(),
                    "decision_evidence_sha256": decision.evidence_sha256,
                    "signal_fingerprint": signal,
                    "trader_id": trader_id,
                    "qore_symbol": qore_symbol,
                    "trader_opportunity": opportunity,
                    "market_predecision_state": {
                        "provider_observation": candidate_row.get(
                            "provider_observation"
                        ),
                        "provider_model_sha256": candidate_row.get(
                            "provider_model_sha256"
                        ),
                        "provider_time_semantics": candidate_row.get(
                            "provider_time_semantics"
                        ),
                        "hard_risk_headroom_usd": decision_payload.get(
                            "hard_risk_headroom_usd"
                        ),
                        "margin_headroom_usd": decision_payload.get(
                            "margin_headroom_usd"
                        ),
                        "regime": regime,
                    },
                    "cognitive_orchestration": {
                        "cf01_cf19_registered_in_separate_capability_exam": list(
                            _CF_CODES
                        ),
                        "runtime_economic_consultation": "PRESENT",
                        "runtime_consulted_faculties": list(consulted_faculties),
                        "consultation_id": consultation.get("consultation_id"),
                        "coordination_disposition": consultation.get(
                            "coordination_disposition"
                        ),
                        "coordination_request_code": consultation.get(
                            "coordination_request_code"
                        ),
                        "causal_predecision": consultation.get("causal_predecision"),
                        "outcome_used": consultation.get("outcome_used"),
                        "executive_brain_invoked": False,
                        "mission_director_invoked": False,
                        "functional_coordinator_invoked": True,
                        "reason": (
                            "CF01-CF19 functional consultation is now a required "
                            "predecision prerequisite before CE2I evaluation; the "
                            "legacy executive brain remains quarantined"
                        ),
                    },
                    "expectation": candidate.get("expectation"),
                    "ce2i": {
                        "registered_tools": list(_T_CODES),
                        "enabled_tools": list(enabled_tools),
                        "opportunity_advanced_decisions": advanced_by_signal.get(
                            signal, []
                        ),
                        "portfolio_advanced_decisions": portfolio_decisions,
                        "evidence_transport": (
                            "CAUSAL_TIME_GUARDED_ADVANCED_EVIDENCE"
                            if signal_effects or portfolio_effects
                            else "EMPTY_OR_NONAUTHORIZED_ADVANCED_EVIDENCE"
                        ),
                        "candidate_economic_effects": signal_effects,
                        "portfolio_economic_effects": portfolio_effects,
                        "effective_hard_risk_headroom_usd": (
                            economic_application.get(
                                "effective_hard_risk_headroom_usd"
                            )
                        ),
                        "effective_margin_headroom_usd": (
                            economic_application.get(
                                "effective_margin_headroom_usd"
                            )
                        ),
                    },
                    "capital_science": {
                        "scope": "LANE_LEVEL_STATUS_NOT_PER_OPPORTUNITY",
                        "capabilities": genc,
                    },
                    "allocation": {
                        "selected_by_cibo_policy": selected,
                        "allocator_disposition": policy.allocator_disposition,
                        "allocation_row": allocation,
                    },
                    "cma": {
                        "sizing_authority": "CIBO_CMA",
                        "candidate_stop_risk_usd": effective_candidate.get(
                            "stop_risk_usd"
                        ),
                        "candidate_margin_usd": effective_candidate.get(
                            "margin_usd"
                        ),
                        "pre_ce2i_stop_risk_usd": candidate.get("stop_risk_usd"),
                        "pre_ce2i_margin_usd": candidate.get("margin_usd"),
                        "risk_request_emitted": risk is not None,
                        "requested_stop_risk_usd": (
                            None
                            if risk is None
                            else format(risk.requested_stop_risk_usd, "f")
                        ),
                    },
                    "qore_risk": (
                        {
                            "status": "NOT_REACHED",
                            "sovereign": True,
                        }
                        if risk is None
                        else {
                            "status": risk.risk_decision.value,
                            "sovereign": True,
                            "evidence_id": risk.evidence_id,
                            "authorized_stop_risk_usd": format(
                                risk.authorized_stop_risk_usd, "f"
                            ),
                            "authorized_margin_usd": format(
                                risk.authorized_margin_usd, "f"
                            ),
                            "risk_model_sha256": risk.risk_model_sha256,
                        }
                    ),
                    "provider_economics_and_execution": {
                        "provider_evidence_id": candidate_row.get(
                            "provider_evidence_id"
                        ),
                        "executed": settlement is not None,
                        "provider_execution_adjustment_usd": (
                            None
                            if settlement is None
                            else format(
                                settlement.provider_execution_adjustment_usd,
                                "f",
                            )
                        ),
                        "decision_provider_cost_proxy_usd": (
                            None
                            if settlement is None
                            else format(
                                settlement.decision_provider_cost_proxy_usd,
                                "f",
                            )
                        ),
                    },
                    "settlement": (
                        None
                        if settlement is None
                        else {
                            "evidence_id": settlement.evidence_id,
                            "observed_at": settlement.observed_at.isoformat(),
                            "gross_structural_outcome_r": format(
                                settlement.gross_structural_outcome_r, "f"
                            ),
                            "realized_net_pnl_usd": format(
                                settlement.realized_net_pnl_usd, "f"
                            ),
                            "capital_deployed_at": (
                                settlement.capital_deployed_at.isoformat()
                            ),
                            "capital_released_at": (
                                settlement.capital_released_at.isoformat()
                            ),
                            "capital_minutes": format(
                                settlement.capital_minutes, "f"
                            ),
                        }
                    ),
                    "capital_release": (
                        None
                        if release is None
                        else {
                            "tool_code": "T20",
                            "evidence_id": release.evidence_id,
                            "released_at": release.released_at.isoformat(),
                            "released_stop_risk_usd": format(
                                release.released_stop_risk_usd, "f"
                            ),
                            "released_margin_usd": format(
                                release.released_margin_usd, "f"
                            ),
                        }
                    ),
                    "post_outcome_learning": {
                        "status": "NOT_INTEGRATED_IN_CURRENT_ECONOMIC_REPLAY",
                        "same_trade_decision_mutated": False,
                    },
                }
            )

    expected_opportunities = sum(
        len(item.signal_fingerprints)
        for item in books.holdout_evidence.decisions
    )
    if len(rows) != expected_opportunities:
        raise CiboCapitalManagementError(
            "profitability trace opportunity coverage drift"
        )

    payload: dict[str, object] = {
        "schema": "qore.cibo.profitability-lab.decision-trace.v1",
        "status": "OBSERVATIONAL",
        "opportunity_count": len(rows),
        "governance": {
            "policy_mutated": False,
            "trader_logic_mutated": False,
            "cma_authority_mutated": False,
            "qore_risk_authority_mutated": False,
            "outcome_aware_tuning_used": False,
            "broker_mutation": False,
            "live": False,
            "real_capital": False,
            "production": False,
            "merge_authority": False,
        },
        "opportunities": rows,
    }
    payload["trace_sha256"] = _fingerprint(payload)
    return payload


def _genc_accountability(
    rows: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    by_code: dict[str, dict[str, object]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise CiboCapitalManagementError(
                "profitability trace GEN-C accountability row invalid"
            )
        function_code = raw.get("function_code")
        if not isinstance(function_code, str) or not function_code:
            raise CiboCapitalManagementError(
                "profitability trace GEN-C function code missing"
            )
        code = function_code.split("_", 1)[0]
        if code not in _GENC_CODES:
            continue
        by_code[code] = {
            "capability": code,
            "status": raw.get("status"),
            "reason": raw.get("reason"),
            "executed_count": raw.get("executed_count", 0),
        }
    return [
        by_code.get(
            code,
            {
                "capability": code,
                "status": "NOT_INTEGRATED",
                "reason": (
                    "capability absent from current Compound economic lane"
                ),
                "executed_count": 0,
            },
        )
        for code in _GENC_CODES
    ]


def _advanced_by_signal(
    full_surface: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    out: dict[str, list[dict[str, object]]] = {}
    for raw in _list_of_objects(
        full_surface.get("opportunity_assessments", []),
        "opportunity_assessments",
    ):
        signal = _required_string(
            raw.get("signal_fingerprint"),
            "advanced assessment signal",
        )
        out[signal] = _list_of_objects(
            raw.get("decisions", []),
            "advanced decisions",
        )
    return out


def _allocation_rows(
    policy_payload: dict[str, object],
) -> dict[str, dict[str, object]]:
    allocator = _object(
        policy_payload.get("allocator_decision"),
        "allocator_decision",
    )
    allocation = allocator.get("allocation")
    if allocation is None:
        return {}
    allocation_obj = _object(allocation, "allocation")
    out: dict[str, dict[str, object]] = {}
    for row in _list_of_objects(allocation_obj.get("rows", []), "allocation rows"):
        signal = _required_string(
            row.get("signal_fingerprint"),
            "allocation signal",
        )
        out[signal] = row
    return out


def _json_object(value: str, label: str) -> dict[str, object]:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            f"profitability trace {label} JSON must be str"
        )
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            f"profitability trace {label} JSON invalid"
        ) from error
    return _object(parsed, label)


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(
            f"profitability trace {label} must be object"
        )
    return value


def _list_of_objects(
    value: object,
    label: str,
) -> list[dict[str, object]]:
    if not isinstance(value, list) or any(
        not isinstance(item, dict) for item in value
    ):
        raise CiboCapitalManagementError(
            f"profitability trace {label} must be object list"
        )
    return value


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) for item in value
    ):
        raise CiboCapitalManagementError(
            f"profitability trace {label} must be string list"
        )
    return tuple(value)


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CiboCapitalManagementError(
            f"profitability trace {label} missing"
        )
    return value


def _fingerprint(value: dict[str, object]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
