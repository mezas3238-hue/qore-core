"""Assemble heterogeneous Trader Lab outputs into one CEILING_DISCOVERY verdict.

The assembler deliberately treats the Maximum Capability Frontier as diagnostic
only.  Native MAX coverage and the single-account sovereign economic run are the
authoritative evidence required to close CEILING_DISCOVERY.
"""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any, Mapping

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ceiling_discovery import (
    CiboCeilingDiscoveryEvidence,
    CiboCeilingLimitKind,
)


_REQUIRED_ABLATIONS = (
    "sizing",
    "adaptive_leverage",
    "cibo_compound",
    "compound_portfolio",
    "cognition",
)


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CiboCapitalManagementError(
            f"ceiling assembly {name} must be mapping"
        )
    return value


def _decimal(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"ceiling assembly {name} must be Decimal-compatible"
        ) from error
    if not result.is_finite() or result < 0:
        raise CiboCapitalManagementError(
            f"ceiling assembly {name} must be finite non-negative"
        )
    return result


def _int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CiboCapitalManagementError(
            f"ceiling assembly {name} must be non-negative int"
        )
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise CiboCapitalManagementError(
            f"ceiling assembly {name} must be bool"
        )
    return value


def assemble_ceiling_discovery(
    *,
    native_preflight: Mapping[str, Any],
    sovereign_run: Mapping[str, Any],
    diagnostic_frontier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one canonical ceiling verdict from lab receipts."""

    preflight = _mapping(native_preflight, "native_preflight")
    run = _mapping(sovereign_run, "sovereign_run")

    if preflight.get("schema") != (
        "qore.cibo.native-max-intelligence-preflight.v1"
    ):
        raise CiboCapitalManagementError(
            "ceiling assembly native preflight schema invalid"
        )
    if run.get("schema") != (
        "qore.cibo.single-account-sovereign-ceiling-run.v1"
    ):
        raise CiboCapitalManagementError(
            "ceiling assembly sovereign run schema invalid"
        )

    if diagnostic_frontier is not None:
        frontier = _mapping(diagnostic_frontier, "diagnostic_frontier")
        if frontier.get("frontier_role") != "DIAGNOSTIC_FRONTIER_ONLY":
            raise CiboCapitalManagementError(
                "ceiling assembly frontier must be diagnostic-only"
            )
        if frontier.get("ceiling_discovery_closure_eligible") is not False:
            raise CiboCapitalManagementError(
                "diagnostic frontier cannot be closure-eligible"
            )

    preflight_count = _int(
        preflight.get("decision_count"),
        "preflight decision_count",
    )
    pass_count = _int(
        preflight.get("native_max_pass_count"),
        "native_max_pass_count",
    )
    blocked_count = _int(
        preflight.get("native_max_blocked_count"),
        "native_max_blocked_count",
    )
    if pass_count + blocked_count != preflight_count:
        raise CiboCapitalManagementError(
            "ceiling assembly Native MAX count identity drift"
        )
    if preflight.get("maximum_intelligence_ready") is not True:
        raise CiboCapitalManagementError(
            "ceiling assembly requires complete Native MAX preflight"
        )
    if preflight.get("external_ai_call_count") != 0:
        raise CiboCapitalManagementError(
            "ceiling assembly forbids external AI in preflight"
        )

    run_count = _int(run.get("decision_count"), "run decision_count")
    if run_count != preflight_count:
        raise CiboCapitalManagementError(
            "ceiling assembly preflight/run decision population drift"
        )
    if (
        run.get("source_manifest_sha256")
        != preflight.get("source_manifest_sha256")
    ):
        raise CiboCapitalManagementError(
            "ceiling assembly source manifest lineage drift"
        )

    ablations = _mapping(run.get("ablations"), "ablations")
    executed: dict[str, bool] = {}
    for name in _REQUIRED_ABLATIONS:
        row = _mapping(ablations.get(name), f"ablation {name}")
        executed[name] = _bool(
            row.get("executed"),
            f"ablation {name} executed",
        )
        if not executed[name]:
            raise CiboCapitalManagementError(
                f"ceiling assembly mandatory ablation missing: {name}"
            )

    limiting_raw = run.get("limiting_factor")
    try:
        limiting = CiboCeilingLimitKind(str(limiting_raw))
    except ValueError as error:
        raise CiboCapitalManagementError(
            "ceiling assembly limiting factor invalid"
        ) from error

    evidence = CiboCeilingDiscoveryEvidence(
        decision_count=run_count,
        native_max_pass_count=pass_count,
        sovereign_runtime_evaluation_count=_int(
            run.get("sovereign_runtime_evaluation_count"),
            "sovereign_runtime_evaluation_count",
        ),
        full_semantic_decision_count=_int(
            run.get("full_semantic_decision_count"),
            "full_semantic_decision_count",
        ),
        external_ai_call_count=_int(
            run.get("external_ai_call_count"),
            "external_ai_call_count",
        ),
        account_reset_count=_int(
            run.get("account_reset_count"),
            "account_reset_count",
        ),
        economic_era_reset_count=_int(
            run.get("economic_era_reset_count"),
            "economic_era_reset_count",
        ),
        initial_capital_usd=_decimal(
            run.get("initial_capital_usd"),
            "initial_capital_usd",
        ),
        ending_capital_usd=_decimal(
            run.get("ending_capital_usd"),
            "ending_capital_usd",
        ),
        peak_capital_usd=_decimal(
            run.get("peak_capital_usd"),
            "peak_capital_usd",
        ),
        maximum_drawdown_usd=_decimal(
            run.get("maximum_drawdown_usd"),
            "maximum_drawdown_usd",
        ),
        native_sovereign_runtime_used=_bool(
            run.get("native_sovereign_runtime_used"),
            "native_sovereign_runtime_used",
        ),
        qore_risk_sovereign=_bool(
            run.get("qore_risk_sovereign"),
            "qore_risk_sovereign",
        ),
        outcome_used_for_predecision=_bool(
            run.get("outcome_used_for_predecision"),
            "outcome_used_for_predecision",
        ),
        target_capital_used_for_tuning=_bool(
            run.get("target_capital_used_for_tuning"),
            "target_capital_used_for_tuning",
        ),
        sizing_ablation_present=executed["sizing"],
        adaptive_leverage_ablation_present=executed["adaptive_leverage"],
        cibo_compound_ablation_present=executed["cibo_compound"],
        compound_portfolio_ablation_present=executed["compound_portfolio"],
        cognition_ablation_present=executed["cognition"],
        population_exhausted=_bool(
            run.get("population_exhausted"),
            "population_exhausted",
        ),
        growth_capacity_remaining_at_population_end=_bool(
            run.get("growth_capacity_remaining_at_population_end"),
            "growth_capacity_remaining_at_population_end",
        ),
        intrinsic_ceiling_claimed=_bool(
            run.get("intrinsic_ceiling_claimed"),
            "intrinsic_ceiling_claimed",
        ),
        observed_lower_bound_only=_bool(
            run.get("observed_lower_bound_only"),
            "observed_lower_bound_only",
        ),
        limiting_factor=limiting,
    )

    classification = (
        "INTRINSIC_CEILING"
        if evidence.ceiling_discovery_ready_to_close
        else "OBSERVED_LOWER_BOUND"
        if evidence.observed_lower_bound_only
        else "CEILING_DISCOVERY_OPEN"
    )
    return {
        "schema": "qore.cibo.ceiling-discovery-assembly.v1",
        "classification": classification,
        "ceiling_discovery_ready_to_close": (
            evidence.ceiling_discovery_ready_to_close
        ),
        "capital_multiple": format(evidence.capital_multiple, "f"),
        "maximum_drawdown_fraction_of_peak": format(
            evidence.maximum_drawdown_fraction_of_peak,
            "f",
        ),
        "evidence": {
            key: (
                value.value
                if isinstance(value, CiboCeilingLimitKind)
                else format(value, "f")
                if isinstance(value, Decimal)
                else value
            )
            for key, value in asdict(evidence).items()
        },
        "sources": {
            "source_manifest_sha256": run.get("source_manifest_sha256"),
            "native_preflight_schema": preflight.get("schema"),
            "sovereign_run_schema": run.get("schema"),
            "diagnostic_frontier_fingerprint": (
                None
                if diagnostic_frontier is None
                else diagnostic_frontier.get("fingerprint")
            ),
        },
        "governance": {
            "diagnostic_frontier_authoritative": False,
            "native_sovereign_run_authoritative": True,
            "external_ai": False,
            "outcome_aware_tuning": False,
            "certification_claimed": False,
        },
    }
