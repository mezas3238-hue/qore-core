"""Fail-closed scientific EIA result -> QORE Research / Trader Lab handoff.

This is a READ-ONLY source-evidence receipt for a completed *association test*.
It cannot construct TraderLabStageEvidenceRecord, qualify a candidate, synthesize
ResearchReturnObservation, mint external governed authority, or promote to DEMO.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo.research_director import CiboResearchStage
from qore.infrastructure.trader_lab.lifecycle import MANDATORY_STAGES, TraderLabState
from qore.infrastructure.trader_lab.stage_evidence import TraderLabStage

PREREG_COMMIT = "00065e6df7450cac707f983858ca39eed7b30c47"
RESULT_RUN_COMMIT = "25b8d2fc18c02992ff1115bbb117cc42438de891"
SOURCE_RUN_ID = 38448311219
SOURCE_ARTIFACT_ID = 11839586948
SOURCE_ARTIFACT_ZIP_SHA256 = (
    "48cc8c7e8b3816fb7adf23658303bd90c3ed9e270c6e0e015fbd82a9904bf9eb"
)
SOURCE_SHA = {
    "WTI_F1": "a55a70d2438ebdc600a77f9d3f9c46be1e2f480ac5ffec3bb753c61cf21db0c9",
    "WTI_F2": "31d8a01ae5bd3cb8753925743802c9e77f11bd54ce1b5e0fd4d91d91940ecea7",
    "NG_F1": "1e71a774943c00cdba337c8be1c9888ea1d56b175c446527cc0d94f7dc2b03f1",
    "NG_F2": "abf42f8f7c6acc9581d283688d7571336a0ee4850c7ae43e433e37720f655aee",
}
WINDOW_YEARS = {"dev": (2012, 2018), "diag": (2019, 2021)}
ALPHA = 0.025
MIN_DELTA = 0.10
MIN_STATE_MONTHS = 8
REQUIRED_ROOTS = ("WTI", "NG")


class ResearchHandoffError(ValueError):
    """Contradiction, missing provenance, outcome tampering or attempted promotion."""


def _closed_keys(actual: Any, expected: set[str], where: str) -> dict[str, Any]:
    if not isinstance(actual, dict) or set(actual) != expected:
        raise ResearchHandoffError(f"SCHEMA_{where}")
    return actual


def _int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ResearchHandoffError(f"NONNEGATIVE_INT_{label}")
    return value


def _float(value: Any, label: str) -> float:
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ResearchHandoffError(f"FINITE_FLOAT_{label}")
    return float(value)


def _one_sided_fisher(
    up_back: int, down_back: int, up_cont: int, down_cont: int
) -> float:
    """Independent exact Fisher right tail with fixed row/column margins."""
    row1 = up_back + down_back
    total_up = up_back + up_cont
    total_down = down_back + down_cont
    total = row1 + up_cont + down_cont
    denom = math.comb(total, row1)
    return sum(
        math.comb(total_up, s)
        * math.comb(total_down, row1 - s)
        / denom
        for s in range(up_back, min(row1, total_up) + 1)
        if 0 <= row1 - s <= total_down
    )


def _verify_window(window: Any, name: str) -> dict[str, Any]:
    obj = _closed_keys(
        window,
        {
            "window", "n_months", "n_backwardation_months", "n_contango_months",
            "up_backwardation", "down_backwardation", "up_contango", "down_contango",
            "delta_probability_up", "one_sided_fisher_p", "min_months_per_state",
            "minimum_positive_delta", "family_alpha_per_root", "decision",
        },
        "WINDOW",
    )
    first, last = WINDOW_YEARS[name]
    if obj["window"] != f"{first}-{last}":
        raise ResearchHandoffError("WINDOW_RELABELED")
    for key, expected in (
        ("min_months_per_state", MIN_STATE_MONTHS),
        ("minimum_positive_delta", MIN_DELTA),
        ("family_alpha_per_root", ALPHA),
    ):
        if obj[key] != expected:
            raise ResearchHandoffError(f"PREREG_THRESHOLD_MUTATED_{key}")
    back = _int(obj["n_backwardation_months"], "back")
    cont = _int(obj["n_contango_months"], "cont")
    total = _int(obj["n_months"], "total")
    if total != back + cont or total > (last - first + 1) * 12:
        raise ResearchHandoffError("INVALID_MONTH_COUNTS")
    u_b = _int(obj["up_backwardation"], "up_back")
    d_b = _int(obj["down_backwardation"], "down_back")
    u_c = _int(obj["up_contango"], "up_cont")
    d_c = _int(obj["down_contango"], "down_cont")
    if back != u_b + d_b or cont != u_c + d_c:
        raise ResearchHandoffError("INVALID_CONTINGENCY_COUNTS")
    if back < MIN_STATE_MONTHS or cont < MIN_STATE_MONTHS:
        if obj["decision"] != "INCONCLUSIVE_TOO_FEW_MONTHS":
            raise ResearchHandoffError("FALSE_POWER_PROMOTION")
        if obj["delta_probability_up"] is not None or obj["one_sided_fisher_p"] is not None:
            raise ResearchHandoffError("UNSUPPORTED_TEST_IN_LOW_POWER_WINDOW")
        return obj
    actual_delta = u_b / back - u_c / cont
    actual_p = _one_sided_fisher(u_b, d_b, u_c, d_c)
    if abs(_float(obj["delta_probability_up"], "delta") - actual_delta) > 1e-9:
        raise ResearchHandoffError("TAMPERED_DELTA")
    if abs(_float(obj["one_sided_fisher_p"], "p") - actual_p) > 1e-9:
        raise ResearchHandoffError("TAMPERED_FISHER_P")
    decision_expected = (
        "NO_POSITIVE_DIRECTION"
        if actual_delta <= 0
        else "PRELIMINARY_PREREG_WINDOW_PASS"
        if actual_delta >= MIN_DELTA and actual_p <= ALPHA
        else "NO_SUPPORT_UNDER_PREREG"
    )
    if obj["decision"] != decision_expected:
        raise ResearchHandoffError("TAMPERED_WINDOW_DECISION")
    return obj


def _verify_root(root_report: Any, expected_root: str) -> dict[str, Any]:
    obj = _closed_keys(
        root_report,
        {"root", "months_audit", "dev", "diag", "decision", "is_tradable_edge_certified"},
        "ROOT",
    )
    if obj["root"] != expected_root or obj["is_tradable_edge_certified"] is not False:
        raise ResearchHandoffError("WRONG_ROOT_OR_FALSE_EDGE_CERT")
    audit = _closed_keys(
        obj["months_audit"],
        {"eligible_months", "not_enough_same_month_observations",
         "spread_ties", "outcome_ties", "valid_one_per_month"},
        "MONTH_AUDIT",
    )
    vals = {name: _int(value, name) for name, value in audit.items()}
    if (
        vals["eligible_months"] != 120
        or vals["eligible_months"] != sum(
            vals[key] for key in (
                "not_enough_same_month_observations",
                "spread_ties", "outcome_ties", "valid_one_per_month",
            )
        )
    ):
        raise ResearchHandoffError("MONTH_AUDIT_INCONSISTENT")
    dev = _verify_window(obj["dev"], "dev")
    diag = _verify_window(obj["diag"], "diag")
    if vals["valid_one_per_month"] != dev["n_months"] + diag["n_months"]:
        raise ResearchHandoffError("MONTH_AND_WINDOW_DISAGREE")
    choices = (dev["decision"], diag["decision"])
    if all(x == "PRELIMINARY_PREREG_WINDOW_PASS" for x in choices):
        expected = "CANDIDATE_DESERVES_HOLDOUT_PROPOSAL"
    elif "INCONCLUSIVE_TOO_FEW_MONTHS" in choices:
        expected = "INCONCLUSIVE_TOO_FEW_MONTHS"
    elif "NO_POSITIVE_DIRECTION" in choices:
        expected = "NO_POSITIVE_DIRECTION"
    else:
        expected = "NO_SUPPORT_UNDER_PREREG"
    if obj["decision"] != expected:
        raise ResearchHandoffError("TAMPERED_ROOT_DECISION")
    return obj


@dataclass(frozen=True, slots=True)
class ScientificHandoffReceipt:
    """Scientific closure only: no ResearchRun, candidate, stage proof or trading."""

    schema: str
    experiment: str
    prereg_commit: str
    source_run_commit: str
    source_run_id: int
    source_artifact_id: int
    scientific_receipt_sha256: str
    result_by_root: tuple[tuple[str, str], ...]
    qore_research_classification: str
    cibo_research_contract_stage: str
    trader_lab_state: str
    trader_lab_first_mandatory_stage: str
    trader_lab_stage_evidence_produced: bool
    has_economic_returns_or_fills: bool
    fresh_holdout_consumed: bool
    demo_eligible: bool
    execution_authority: bool

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def build_handoff_receipt(raw: dict[str, Any]) -> ScientificHandoffReceipt:
    """Validate an exact experimental-result artifact before recording SCIENCE."""
    report = _closed_keys(
        raw,
        {
            "identity", "preregistered_hypothesis_count", "source_SHA256", "scope",
            "dev", "diag", "holdout_2022_2024",
            "forward_reference_price_change_not_executable_roll_net",
            "market_data_budget_USD", "trading_orders", "trader_certified",
            "full_source_ready_for_6_roots", "results", "fx_holdout_touched",
        },
        "ENVELOPE",
    )
    fixed = {
        "identity": "QORE_FUTURES_A_EIA_FRONT_RANK_PROSPECTIVE_V1",
        "preregistered_hypothesis_count": 2,
        "scope": "monthly_first_common_day_signal_2_day_embargo_to_5_day_reference_change",
        "dev": "2012-2018",
        "diag": "2019-2021",
        "holdout_2022_2024": "SEALED_NO_VALUES_LOADED",
        "forward_reference_price_change_not_executable_roll_net": True,
        "market_data_budget_USD": 0,
        "trading_orders": 0,
        "trader_certified": 0,
        "full_source_ready_for_6_roots": False,
        "fx_holdout_touched": False,
    }
    for name, target in fixed.items():
        if type(report[name]) is not type(target) or report[name] != target:
            raise ResearchHandoffError(f"CONTRADICTS_FROZEN_PROTOCOL_{name}")
    if report["source_SHA256"] != SOURCE_SHA:
        raise ResearchHandoffError("UNVERIFIED_SOURCE_DATA_HASH")
    results = report["results"]
    if not isinstance(results, list) or len(results) != len(REQUIRED_ROOTS):
        raise ResearchHandoffError("NOT_TWO_PREDECLARED_ROOTS")
    roots = {
        r["root"]: r for r in results
        if isinstance(r, dict) and isinstance(r.get("root"), str)
    }
    if set(roots) != set(REQUIRED_ROOTS) or len(roots) != len(results):
        raise ResearchHandoffError("ROOT_SWAP_OR_DUPLICATION")
    checked = [_verify_root(roots[name], name) for name in REQUIRED_ROOTS]
    if any(r["decision"] == "CANDIDATE_DESERVES_HOLDOUT_PROPOSAL" for r in checked):
        science = "PARTIAL_CANDIDATE_HOLDOUT_NOT_AUTHORIZED"
    else:
        science = "NO_SUPPORT_UNDER_PREREG"
    if MANDATORY_STAGES[0] is not TraderLabStage.RESEARCH:
        raise ResearchHandoffError("TRADER_LAB_CONTRACT_DRIFT")
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return ScientificHandoffReceipt(
        schema="qore.research-scientific-handoff.eia-f1f2.v1",
        experiment="EIA_WTI_NG_BACKWARDATION_REFERENCE_UP_V1",
        prereg_commit=PREREG_COMMIT,
        source_run_commit=RESULT_RUN_COMMIT,
        source_run_id=SOURCE_RUN_ID,
        source_artifact_id=SOURCE_ARTIFACT_ID,
        scientific_receipt_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        result_by_root=tuple((r["root"], r["decision"]) for r in checked),
        qore_research_classification=science,
        cibo_research_contract_stage=CiboResearchStage.EXPERIMENT.value,
        trader_lab_state=TraderLabState.DRAFT.value,
        trader_lab_first_mandatory_stage=TraderLabStage.RESEARCH.value,
        trader_lab_stage_evidence_produced=False,
        has_economic_returns_or_fills=False,
        fresh_holdout_consumed=False,
        demo_eligible=False,
        execution_authority=False,
    )
