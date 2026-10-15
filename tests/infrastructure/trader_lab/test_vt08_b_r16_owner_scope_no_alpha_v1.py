"""Owner VT08 R16 exclusion: alpha contamination and alternate tracks FAIL."""
from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.trader_lab.vt08_b_r16_owner_scope_no_alpha_v1 import (
    AUTHORITY,
    EXPECTED,
    FAMILY,
    FROZEN_SCHEMA,
    STAGE,
    assert_single_vt08_current_manifest,
    audit_frozen_source_program_scope,
    no_excluded_alpha_lineage,
)

M = "EURJPY"


def manifest() -> dict[str, object]:
    return {
        **AUTHORITY,
        "sizing_used": False, "holdout_7y_accessed": False,
        "orders_enabled": False, "author_source_complete": False,
        "cognitive_admitted": False, "broker_fills": 0,
    }


def frozen() -> dict[str, object]:
    rows = []
    for i in range(EXPECTED[M]):
        rows.append({
            "market": M, "family": FAMILY, "stage": STAGE,
            "c2_opened_at_utc": f"2026-01-{i//24+1:02d}T{i%24:02d}:00:00+00:00",
            "decision_at_utc": f"2026-01-{i//24+1:02d}T{i%24:02d}:30:00+00:00",
            "A_rule_complete": False, "B_signoff": False,
            "cognitive_ready": False, "broker_fill": False,
            "pnl_read": False,
        })
    return {
        "schema": FROZEN_SCHEMA, "market": M,
        "stage_counts": {STAGE: len(rows)},
        "all_unique_proxy_cases_with_raw_receipts": len(rows),
        "examples_by_stage": {STAGE: rows},
        "source_complete_entries": 0, "real_cognitive_admissions": 0,
        "fills": 0, "sizing_applied": False,
        "sealed_holdout_accessed": False,
    }


def test_only_original_vt08_manifest_admitted() -> None:
    assert_single_vt08_current_manifest(manifest())


@pytest.mark.parametrize("forbidden", [
    "QORE-alpha", "qore_alpha", "QORE ALPHA",
    "VT08-QORE-ALPHA", "vt08_alpha",
    "alpha fork", "alpha model", "alpha strategy",
])
def test_any_alpha_or_derived_program_rejected(forbidden: str) -> None:
    data = manifest()
    data["signal_origin"] = forbidden
    with pytest.raises(ValueError, match="QORE-alpha"):
        assert_single_vt08_current_manifest(data)


def test_nested_alpha_feature_rejected() -> None:
    data = manifest()
    data["lineage"] = {"sources": [
        {"strategy": "VT08"}, {"strategy": "QORE_ALPHA"},
    ]}
    with pytest.raises(ValueError, match="QORE-alpha"):
        assert_single_vt08_current_manifest(data)


def test_bad_alpha_key_rejected() -> None:
    with pytest.raises(ValueError, match="QORE-alpha"):
        no_excluded_alpha_lineage({"qore-alpha-feature": 5})


@pytest.mark.parametrize(("field", "value"), [
    ("trader_id", "QORE"),
    ("methodology_program", "VT08_QUANT"),
    ("cognitive_program", "EXTERNAL_COG"),
    ("variant", "V2"),
    ("family", "OTHER_SOURCE_FAMILY"),
])
def test_alternate_software_identity_not_allowed(field: str, value: str) -> None:
    data = manifest()
    data[field] = value
    with pytest.raises(ValueError, match="scope identity/family mismatch"):
        assert_single_vt08_current_manifest(data)


@pytest.mark.parametrize("key", [
    "fallback_strategy", "external_strategy",
    "imported_model", "foreign_signal_origin",
    "alpha_features", "alternate_lineage", "parallel_track",
])
def test_external_strategy_dependencies_rejected(key: str) -> None:
    data = manifest()
    data[key] = ["VT08_NEW_FALLBACK"]
    with pytest.raises(ValueError, match="external/parallel"):
        assert_single_vt08_current_manifest(data)


@pytest.mark.parametrize(("field", "value"), [
    ("sizing_used", True), ("holdout_7y_accessed", True),
    ("orders_enabled", True), ("author_source_complete", True),
    ("cognitive_admitted", True), ("broker_fills", 1),
])
def test_source_only_does_not_authorize_gates_or_fills(
    field: str, value: object,
) -> None:
    data = manifest()
    data[field] = value
    with pytest.raises(ValueError, match="source-only"):
        assert_single_vt08_current_manifest(data)


def test_whole_538_original_shape_owner_scope() -> None:
    result = audit_frozen_source_program_scope(frozen(), expected_market=M)
    assert result["frozen_vt08_cases_verified"] == EXPECTED[M]
    assert result["alternate_programs_authorized"] == 0
    assert result["broker_fills"] == 0
    assert result["alpha_cognition_admitted"] is False


def test_full_frozen_alpha_contamination_rejected() -> None:
    report = frozen()
    report["examples_by_stage"][STAGE][-1]["signal_origin"] = "QORE_ALPHA"
    with pytest.raises(ValueError, match="QORE-alpha"):
        audit_frozen_source_program_scope(report, expected_market=M)


def test_full_frozen_unapproved_signal_rejected() -> None:
    report = frozen()
    report["examples_by_stage"][STAGE][1]["A_rule_complete"] = True
    with pytest.raises(ValueError, match="foreign/source-true"):
        audit_frozen_source_program_scope(report, expected_market=M)


def test_full_frozen_missing_case_rejected() -> None:
    report = frozen()
    report["examples_by_stage"][STAGE].pop()
    with pytest.raises(ValueError, match="census changed"):
        audit_frozen_source_program_scope(report, expected_market=M)


def test_full_frozen_duplicate_rejected() -> None:
    report = frozen()
    records = report["examples_by_stage"][STAGE]
    records[1] = deepcopy(records[0])
    with pytest.raises(ValueError, match="duplicate candidate"):
        audit_frozen_source_program_scope(report, expected_market=M)
