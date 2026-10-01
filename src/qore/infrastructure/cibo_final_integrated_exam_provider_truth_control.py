"""Source-bound E4 Provider Truth control for the Final Integrated CIBO Exam.

E4 accepts either the original forward-execution calibration or the separately
governed Phase22 bounded DEMO calibration. The latter proves current provider
execution/slippage behavior only; it is never relabelled as historical
2015-2016 execution.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    Phase22QualificationReceipt,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
    bind_final_exam_control_artifact,
)

_FORWARD_CALIBRATION_ID = "CIBO_CTRADER_DEMO_FORWARD_EXECUTION_CALIBRATION_V1"
_DEMO_CALIBRATION_SCHEMA = "qore.cibo.phase22.demo-provider-calibration.v1"
_EVIDENCE_KIND = "FINAL_INTEGRATED_EXAM_CONTROL"
_SCHEMA = "qore.cibo.final-provider-truth-control.v2"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_DEMO_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
_MINIMUM_DEMO_DISTINCT_ORDERS = 8


def _decimal(value: object, name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"E4 Provider Truth invalid decimal: {name}"
        ) from error
    if not parsed.is_finite():
        raise CiboCapitalManagementError(
            f"E4 Provider Truth non-finite decimal: {name}"
        )
    return parsed


def _canonical_calibration_fingerprint(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("calibration_sha256", None)
    raw = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _validate_forward_execution_calibration(
    calibration: dict[str, Any],
) -> dict[str, Any]:
    if calibration.get("calibration_id") != _FORWARD_CALIBRATION_ID:
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration identity drift"
        )
    if (
        calibration.get("provider_key") != "ctrader-demo"
        or calibration.get("environment") != "demo"
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth provider/environment drift"
        )
    calibration_sha = calibration.get("calibration_sha256")
    if (
        not isinstance(calibration_sha, str)
        or _SHA256_RE.fullmatch(calibration_sha) is None
        or calibration_sha != _canonical_calibration_fingerprint(calibration)
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration fingerprint drift"
        )
    manifest_sha = calibration.get("manifest_sha256")
    if (
        not isinstance(manifest_sha, str)
        or _SHA256_RE.fullmatch(manifest_sha) is None
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth manifest digest invalid"
        )

    candidate_rows = calibration.get("manifest_candidate_rows")
    complete_rows = calibration.get("manifest_complete_lineage_rows")
    total_observations = calibration.get("total_observations")
    if any(
        type(value) is not int or value <= 0
        for value in (candidate_rows, complete_rows, total_observations)
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth provider population invalid"
        )
    assert isinstance(candidate_rows, int)
    assert isinstance(complete_rows, int)
    assert isinstance(total_observations, int)
    if candidate_rows < 200:
        raise CiboCapitalManagementError(
            "E4 Provider Truth candidate population below frozen minimum"
        )
    coverage = Decimal(complete_rows) / Decimal(candidate_rows)
    if coverage < Decimal("0.95"):
        raise CiboCapitalManagementError(
            "E4 Provider Truth provider population coverage below 95%"
        )
    observations = calibration.get("observations")
    summaries = calibration.get("symbol_summaries")
    if (
        not isinstance(observations, list)
        or len(observations) != total_observations
        or not isinstance(summaries, list)
        or not summaries
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth observation/summary population drift"
        )
    required_true = (
        "manifest_scientifically_ready",
        "all_complete_rows_reconciled",
        "required_symbol_coverage_met",
        "minimum_symbol_observations_met",
        "empirical_slippage_calibrated",
        "execution_model_ready",
    )
    for field in required_true:
        if calibration.get(field) is not True:
            raise CiboCapitalManagementError(
                f"E4 Provider Truth required provider gate failed: {field}"
            )
    required_false = (
        "historical_2017_exact_claimed",
        "holdout_outcomes_used",
        "target_aware",
        "productive_authority",
    )
    for field in required_false:
        if calibration.get(field) is not False:
            raise CiboCapitalManagementError(
                f"E4 Provider Truth governance contamination: {field}"
            )
    if calibration.get("blockers") not in ([], ()):
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration retains blockers"
        )
    return {
        "provider_calibration_mode": "FORWARD_EXECUTION_CALIBRATION_V1",
        "provider_calibration_sha256": calibration_sha,
        "forward_manifest_sha256": manifest_sha,
        "candidate_rows": candidate_rows,
        "complete_lineage_rows": complete_rows,
        "total_observations": total_observations,
        "population_coverage": format(coverage, "f"),
        "symbol_summary_count": len(summaries),
        "historical_execution_claimed": False,
    }


def _validate_bounded_demo_calibration(
    calibration: dict[str, Any],
    *,
    actual_file_sha: str,
) -> dict[str, Any]:
    if calibration.get("schema") != _DEMO_CALIBRATION_SCHEMA:
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO calibration schema drift"
        )
    expected_identity = {
        "status": "READY",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "endpoint_host": "demo.ctraderapi.com",
    }
    for field, value in expected_identity.items():
        if calibration.get(field) != value:
            raise CiboCapitalManagementError(
                f"E4 Provider Truth DEMO calibration field drift: {field}"
            )

    required_symbols = calibration.get("required_symbols")
    if required_symbols != list(_REQUIRED_DEMO_SYMBOLS):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO required-symbol surface drift"
        )
    if (
        calibration.get("minimum_distinct_entry_orders_per_symbol")
        != _MINIMUM_DEMO_DISTINCT_ORDERS
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO minimum-order contract drift"
        )

    counts = calibration.get("after_valid_distinct_orders")
    if not isinstance(counts, dict) or set(counts) != set(_REQUIRED_DEMO_SYMBOLS):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO distinct-order coverage drift"
        )
    for symbol in _REQUIRED_DEMO_SYMBOLS:
        value = counts.get(symbol)
        if type(value) is not int or value < _MINIMUM_DEMO_DISTINCT_ORDERS:
            raise CiboCapitalManagementError(
                "E4 Provider Truth DEMO minimum distinct orders not met"
            )

    observations = calibration.get("observations")
    observation_count = calibration.get("observation_count")
    if (
        not isinstance(observations, list)
        or type(observation_count) is not int
        or observation_count != len(observations)
        or observation_count < (
            len(_REQUIRED_DEMO_SYMBOLS) * _MINIMUM_DEMO_DISTINCT_ORDERS
        )
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO observation population incomplete"
        )
    orders_by_symbol: dict[str, set[str]] = {
        symbol: set() for symbol in _REQUIRED_DEMO_SYMBOLS
    }
    for raw in observations:
        if not isinstance(raw, dict):
            raise CiboCapitalManagementError(
                "E4 Provider Truth DEMO observation must be object"
            )
        symbol = raw.get("qore_symbol")
        order_ref = raw.get("order_ref")
        if (
            symbol not in orders_by_symbol
            or not isinstance(order_ref, str)
            or _SHA256_RE.fullmatch(order_ref) is None
        ):
            raise CiboCapitalManagementError(
                "E4 Provider Truth DEMO observation identity drift"
            )
        orders_by_symbol[str(symbol)].add(order_ref)
    if any(
        len(orders_by_symbol[symbol]) < _MINIMUM_DEMO_DISTINCT_ORDERS
        for symbol in _REQUIRED_DEMO_SYMBOLS
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO observed distinct-order minimum not met"
        )

    created = calibration.get("created_round_trips")
    created_count = calibration.get("created_round_trip_count")
    if (
        not isinstance(created, list)
        or type(created_count) is not int
        or created_count != len(created)
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO created-cohort accounting drift"
        )
    if any(
        not isinstance(item, dict) or item.get("position_closed") is not True
        for item in created
    ):
        raise CiboCapitalManagementError(
            "E4 Provider Truth DEMO created position not proven closed"
        )

    required_true = (
        "empirical_slippage_calibrated",
        "execution_model_ready",
        "minimum_volume_only",
        "created_positions_closed",
    )
    for field in required_true:
        if calibration.get(field) is not True:
            raise CiboCapitalManagementError(
                f"E4 Provider Truth DEMO required provider gate failed: {field}"
            )
    required_false = (
        "historical_provider_economics_claimed",
        "historical_holdout_execution_claimed",
        "holdout_outcomes_used",
        "fundednext_touched",
        "vps_touched",
        "live_authorized",
        "real_capital_authorized",
        "productive_authority",
    )
    for field in required_false:
        if calibration.get(field) is not False:
            raise CiboCapitalManagementError(
                f"E4 Provider Truth DEMO governance contamination: {field}"
            )

    return {
        "provider_calibration_mode": "BOUNDED_DEMO_EXECUTION_CALIBRATION_V1",
        "provider_calibration_sha256": actual_file_sha,
        "forward_manifest_sha256": None,
        "candidate_rows": None,
        "complete_lineage_rows": None,
        "total_observations": observation_count,
        "population_coverage": "DEMO_CALIBRATION_ONLY",
        "symbol_summary_count": len(_REQUIRED_DEMO_SYMBOLS),
        "minimum_distinct_orders_per_symbol": _MINIMUM_DEMO_DISTINCT_ORDERS,
        "historical_execution_claimed": False,
    }


def build_e4_provider_truth_control(
    *,
    integrated_git_sha: str,
    phase22_receipt: Phase22QualificationReceipt,
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    provider_calibration_artifact_json: str,
    observed_at: datetime,
) -> CiboFinalExamControlReceipt:
    """Require real provider calibration before E4 can PASS."""

    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "E4 Provider Truth requires canonical Phase22 receipt"
        )
    if not isinstance(intake, ArchitectAPhase22V2ScientificIntakeReport):
        raise CiboCapitalManagementError(
            "E4 Provider Truth requires canonical Phase22 intake"
        )
    if intake.qualification_status != "PASS":
        raise CiboCapitalManagementError(
            "E4 Provider Truth requires Phase22 PASS intake"
        )
    if not intake.ready_for_scientific_reentry or intake.blockers:
        raise CiboCapitalManagementError(
            "E4 Provider Truth requires admissible Phase22 intake"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "E4 Provider Truth observed_at must be timezone-aware"
        )
    if observed_at <= phase22_receipt.qualified_at:
        raise CiboCapitalManagementError(
            "E4 Provider Truth must be post-Phase22 qualification"
        )

    refs = dict(intake.receipt_refs)
    expected_file_sha = refs.get("provider_economics_sha256")
    if expected_file_sha is None:
        raise CiboCapitalManagementError(
            "E4 Provider Truth missing provider economics receipt"
        )
    actual_file_sha = "sha256:" + hashlib.sha256(
        provider_calibration_artifact_json.encode("utf-8")
    ).hexdigest()
    if actual_file_sha != expected_file_sha:
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration artifact digest drift"
        )

    try:
        calibration = json.loads(provider_calibration_artifact_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration artifact invalid JSON"
        ) from error
    if not isinstance(calibration, dict):
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration artifact must be object"
        )
    expected_json = json.dumps(
        calibration,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if expected_json != provider_calibration_artifact_json:
        raise CiboCapitalManagementError(
            "E4 Provider Truth calibration artifact must be canonical JSON"
        )

    if calibration.get("schema") == _DEMO_CALIBRATION_SCHEMA:
        provider = _validate_bounded_demo_calibration(
            calibration,
            actual_file_sha=actual_file_sha,
        )
    else:
        provider = _validate_forward_execution_calibration(calibration)

    payload = {
        "schema": _SCHEMA,
        "evidence_binding_id": "E4_PROVIDER_TRUTH",
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": "CIBO_ARCH_A_E4_PROVIDER_TRUTH_V2",
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": phase22_receipt.candidate_parameter_sha256,
        "phase22_qualification_artifact_sha256": (
            phase22_receipt.qualification_artifact_sha256
        ),
        "certification_stage": "POST_PHASE22",
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
        "phase22_handoff_manifest_sha256": intake.manifest_sha256,
        "provider_calibration_file_sha256": actual_file_sha,
        **provider,
        "execution_model_ready": True,
        "empirical_slippage_calibrated": True,
        "provider_bound_execution_required": True,
        "synthetic_provider_economics_allowed": False,
        "historical_holdout_execution_claimed": False,
    }
    artifact_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return bind_final_exam_control_artifact(
        receipt_id="E4_PROVIDER_TRUTH",
        evidence_kind=_EVIDENCE_KIND,
        source_artifact_json=artifact_json,
    )
