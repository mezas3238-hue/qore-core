"""Contracts for the CIBO Trader Lab three-by-one-year adaptive research harness.

Research-only. These holdouts are intentionally reusable/burned by adaptive
search and therefore cannot support Fresh OOS or certification claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

GROUP_WINDOWS = (
    ("GROUP_1", "2019-06-30T00:00:00+00:00", "2020-06-30T00:00:00+00:00"),
    ("GROUP_2", "2020-06-30T00:00:00+00:00", "2021-06-30T00:00:00+00:00"),
    ("GROUP_3", "2021-06-30T00:00:00+00:00", "2022-06-30T00:00:00+00:00"),
)
REQUIRED_TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
REQUIRED_TIMEFRAMES = ("H4", "H1", "M15", "M5", "M1")
REQUIRED_CROSS_HOLDOUT_PASS_COUNT = 3
REQUIRED_COGNITIVE_FACULTIES = tuple(f"CF{i:02d}" for i in range(1, 20))
REQUIRED_CE2I_TOOLS = tuple(f"T{i:02d}" for i in range(1, 21))
REQUIRED_CAPITAL_SCIENCE = tuple(f"GEN-C{i}" for i in range(1, 15))


class ThreeHoldoutResearchError(ValueError):
    pass


def _decimal(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise ThreeHoldoutResearchError(f"{name} must be decimal") from error
    if not result.is_finite():
        raise ThreeHoldoutResearchError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class HoldoutWindow:
    group_id: str
    start_at: datetime
    end_exclusive_at: datetime

    def __post_init__(self) -> None:
        if self.group_id not in {row[0] for row in GROUP_WINDOWS}:
            raise ThreeHoldoutResearchError("unknown holdout group")
        if (
            self.start_at.tzinfo is None
            or self.start_at.utcoffset() is None
            or self.end_exclusive_at.tzinfo is None
            or self.end_exclusive_at.utcoffset() is None
            or self.end_exclusive_at <= self.start_at
        ):
            raise ThreeHoldoutResearchError("invalid holdout chronology")
        if self.start_at.astimezone(UTC).replace(year=self.start_at.year + 1) != (
            self.end_exclusive_at.astimezone(UTC)
        ):
            raise ThreeHoldoutResearchError("holdout must be exactly one calendar year")


@dataclass(frozen=True, slots=True)
class CandidateGateResult:
    configuration_fingerprint: str
    passed: bool
    failed_gates: tuple[str, ...]


def expected_windows() -> tuple[HoldoutWindow, ...]:
    return tuple(
        HoldoutWindow(
            group_id=group_id,
            start_at=datetime.fromisoformat(start),
            end_exclusive_at=datetime.fromisoformat(end),
        )
        for group_id, start, end in GROUP_WINDOWS
    )


def evaluate_candidate(candidate: dict[str, Any]) -> CandidateGateResult:
    fingerprint = candidate.get("configuration_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ThreeHoldoutResearchError("configuration fingerprint required")
    if candidate.get("configuration_scope") != "CIBO_ONLY":
        raise ThreeHoldoutResearchError(
            "candidate configuration fingerprint must be CIBO-only"
        )
    if candidate.get("trader_parameters_changed") is not False:
        raise ThreeHoldoutResearchError(
            "Trader parameters must remain frozen during CIBO research"
        )
    if candidate.get("trader_profitability_used_for_gate") is not True:
        raise ThreeHoldoutResearchError(
            "all-seven Trader profitability must gate CIBO candidates"
        )

    m = candidate.get("measurements")
    if not isinstance(m, dict):
        raise ThreeHoldoutResearchError("candidate measurements required")

    failed: list[str] = []
    if m.get("all_7_traders_participate") is not True:
        failed.append("ALL_7_TRADERS")
    per_trader = m.get("per_trader_under_cibo")
    if not isinstance(per_trader, dict):
        raise ThreeHoldoutResearchError(
            "per-Trader CIBO economic measurements are required"
        )
    if (
        len(per_trader) != len(REQUIRED_TRADERS)
        or set(per_trader) != set(REQUIRED_TRADERS)
    ):
        failed.append("ALL_7_TRADERS_EXACT_SURFACE")
    else:
        for trader_id in REQUIRED_TRADERS:
            row = per_trader[trader_id]
            if not isinstance(row, dict):
                raise ThreeHoldoutResearchError(
                    f"{trader_id}: CIBO measurement row missing"
                )
            if int(row.get("settled_count", 0)) <= 0:
                failed.append(f"{trader_id}:NO_SETTLEMENT")
            if _decimal(
                row.get("final_pnl_usd", "0"),
                f"{trader_id} final pnl",
            ) <= 0:
                failed.append(f"{trader_id}:PNL")
            if _decimal(
                row.get("profit_factor", "0"),
                f"{trader_id} profit factor",
            ) <= 1:
                failed.append(f"{trader_id}:PF")
            if _decimal(
                row.get("expectancy_usd", "0"),
                f"{trader_id} expectancy",
            ) <= 0:
                failed.append(f"{trader_id}:EXPECTANCY")
    if tuple(m.get("timeframes", ())) != REQUIRED_TIMEFRAMES:
        failed.append("TIMEFRAME_SURFACE")

    core = m.get("core")
    compound = m.get("compound")
    portfolio = m.get("compound_portfolio")
    mc = m.get("monte_carlo")
    stress = m.get("stress")
    if not all(isinstance(x, dict) for x in (core, compound, portfolio, mc, stress)):
        raise ThreeHoldoutResearchError("economic measurement blocks missing")

    if _decimal(core["net_pnl_usd"], "core net pnl") <= 0:
        failed.append("CORE_PNL")
    if _decimal(core["profit_factor"], "core profit factor") <= 1:
        failed.append("CORE_PF")
    if _decimal(core["expectancy_usd"], "core expectancy") <= 0:
        failed.append("CORE_EXPECTANCY")
    if _decimal(compound["incremental_pnl_usd"], "compound incremental pnl") <= 0:
        failed.append("COMPOUND_PNL")
    if _decimal(
        portfolio["incremental_pnl_usd"],
        "compound portfolio incremental pnl",
    ) <= 0:
        failed.append("PORTFOLIO_PNL")
    if _decimal(
        portfolio["value_add_vs_compound_usd"],
        "portfolio value add",
    ) <= 0:
        failed.append("PORTFOLIO_VALUE_ADD")
    if _decimal(m["final_ending_capital_usd"], "ending capital") <= 60:
        failed.append("ENDING_CAPITAL")
    if m.get("chronological_folds_all_positive") is not True:
        failed.append("CHRONOLOGICAL_FOLDS")
    if _decimal(mc["median_pnl_usd"], "MC median") <= 0:
        failed.append("MC_MEDIAN")
    if _decimal(mc["p05_pnl_usd"], "MC p05") <= 0:
        failed.append("MC_P05")
    if _decimal(stress["provider_cost_x2_pnl_usd"], "provider cost x2") <= 0:
        failed.append("PROVIDER_COST_X2")
    if _decimal(stress["remove_best_3_pnl_usd"], "remove best 3") <= 0:
        failed.append("REMOVE_BEST_3")
    if int(m.get("protected_capital_breaches", -1)) != 0:
        failed.append("PROTECTED_CAPITAL")
    if m.get("all_required_cibo_functions_accounted_for") is not True:
        failed.append("CIBO_FUNCTION_ACCOUNTABILITY")
    function_behavior = m.get("cibo_function_behavior")
    if not isinstance(function_behavior, dict):
        raise ThreeHoldoutResearchError("CIBO function behavior report missing")
    if tuple(function_behavior.get("cognitive_faculties", ())) != (
        REQUIRED_COGNITIVE_FACULTIES
    ):
        failed.append("CF01_CF19_ACCOUNTABILITY")
    if tuple(function_behavior.get("ce2i_tools", ())) != REQUIRED_CE2I_TOOLS:
        failed.append("T01_T20_ACCOUNTABILITY")
    if tuple(function_behavior.get("capital_science", ())) != (
        REQUIRED_CAPITAL_SCIENCE
    ):
        failed.append("GENC01_GENC14_ACCOUNTABILITY")
    if function_behavior.get("per_function_observability_complete") is not True:
        failed.append("PER_FUNCTION_OBSERVABILITY")
    if m.get("trader_profitability_used_for_gate") is not True:
        failed.append("ALL_7_TRADER_PROFITABILITY_GATE_REQUIRED")
    if m.get("qore_risk_sovereign") is not True:
        failed.append("QORE_RISK_SOVEREIGN")

    return CandidateGateResult(
        configuration_fingerprint=fingerprint,
        passed=not failed,
        failed_gates=tuple(failed),
    )


def evaluate_three_groups(
    group_payloads: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    windows = expected_windows()
    if len(group_payloads) != len(windows):
        raise ThreeHoldoutResearchError("exact three group payloads required")

    passed_by_group: dict[str, set[str]] = {}
    diagnostics: dict[str, list[dict[str, Any]]] = {}
    for expected, payload in zip(windows, group_payloads, strict=True):
        if payload.get("schema") != "qore.cibo.trader-lab.1y-group-result.v1":
            raise ThreeHoldoutResearchError("unexpected group-result schema")
        if payload.get("group_id") != expected.group_id:
            raise ThreeHoldoutResearchError("group order/identity drift")
        if payload.get("start_at") != expected.start_at.isoformat():
            raise ThreeHoldoutResearchError("group start drift")
        if payload.get("end_exclusive_at") != expected.end_exclusive_at.isoformat():
            raise ThreeHoldoutResearchError("group end drift")
        if tuple(payload.get("traders", ())) != REQUIRED_TRADERS:
            raise ThreeHoldoutResearchError("seven-Trader cohort drift")
        if payload.get("adaptive_research_only") is not True:
            raise ThreeHoldoutResearchError("group must be adaptive research-only")
        if payload.get("execution_topology") != "SINGLE_INTEGRATED_7_TRADER_PORTFOLIO":
            raise ThreeHoldoutResearchError("group must be one integrated 7-Trader portfolio")
        if payload.get("shared_cibo_state") is not True:
            raise ThreeHoldoutResearchError("group must use one shared CIBO state")
        if payload.get("shared_qore_risk_state") is not True:
            raise ThreeHoldoutResearchError("group must use one shared QORE Risk state")
        if str(payload.get("shared_initial_capital_usd")) != "60":
            raise ThreeHoldoutResearchError("group shared initial capital must be USD60")
        if payload.get("per_trader_results_source_only") is not True:
            raise ThreeHoldoutResearchError("per-Trader results must remain SOURCE_ONLY")

        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            raise ThreeHoldoutResearchError("candidate list missing")
        group_passed: set[str] = set()
        group_diag: list[dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ThreeHoldoutResearchError("candidate must be object")
            result = evaluate_candidate(candidate)
            if result.passed:
                group_passed.add(result.configuration_fingerprint)
            group_diag.append(
                {
                    "configuration_fingerprint": result.configuration_fingerprint,
                    "passed": result.passed,
                    "failed_gates": list(result.failed_gates),
                }
            )
        passed_by_group[expected.group_id] = group_passed
        diagnostics[expected.group_id] = group_diag

    common = set.intersection(*passed_by_group.values()) if passed_by_group else set()
    sorted_common = sorted(common)
    stop = len(sorted_common) >= REQUIRED_CROSS_HOLDOUT_PASS_COUNT
    return {
        "schema": "qore.cibo.trader-lab.3x1y-sensor.v1",
        "status": (
            "STOP_THREE_CROSS_HOLDOUT_FULL_PASS"
            if stop
            else "CONTINUE_SEARCH"
        ),
        "required_pass_count": REQUIRED_CROSS_HOLDOUT_PASS_COUNT,
        "cross_holdout_full_pass_count": len(sorted_common),
        "cross_holdout_full_pass_fingerprints": sorted_common,
        "per_group_full_pass_counts": {
            key: len(value) for key, value in passed_by_group.items()
        },
        "diagnostics": diagnostics,
        "research_only": True,
        "adaptive_outcome_aware_search": True,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
        "live_authorized": False,
        "production_authorized": False,
        "real_capital_authorized": False,
        "broker_mutation": False,
    }
