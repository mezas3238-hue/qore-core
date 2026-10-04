from copy import deepcopy
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_a3_b4_b4_intake import (
    SharedA3B4IntakeError,
    build_b4_intake_batch,
)

NOW = datetime(2026, 10, 4, 19, 35, tzinfo=UTC)


def _payloads():
    b06_rows = []
    b07_rows = []
    frontier_rows = []
    sid = 1
    groups = (
        ("CURRENT_REFERENCE_VERIFIED", 85),
        ("VERSIONED_CONTRACT_VERIFIED", 5),
        ("LEGACY_LINEAGE_ONLY", 2),
        ("PROVIDER_BINDING_UNKNOWN", 12),
        ("PROVIDER_ATTESTED_ONLY", 73),
    )
    temporal = (
        ("DISTRIBUTED_OTC_CALENDAR_UNRESOLVED", 60),
        ("R8_HISTORICAL_SESSION_PARTIAL", 1),
        ("CURRENT_INDEX_CALENDAR_UNRESOLVED", 10),
        ("LEGACY_HISTORICAL_VERSION_REQUIRED", 2),
        ("IDENTITY_BLOCKED", 12),
        ("IDENTITY_AND_MARKET_STRUCTURE_BLOCKED", 73),
        ("VERSIONED_SESSION_CALENDAR_REQUIRED", 5),
        ("REFERENCE_TEMPORAL_SEMANTICS_REQUIRED", 14),
    )
    temporal_values = [
        value for value, count in temporal for _ in range(count)
    ]
    assert len(temporal_values) == 177

    for disposition, count in groups:
        for _ in range(count):
            symbol = f"S{sid}"
            b06_rows.append(
                {
                    "provider": "CTRADER_DEMO",
                    "provider_symbol_id": sid,
                    "provider_symbol": symbol,
                    "identity_disposition": disposition,
                }
            )
            b07_rows.append(
                {
                    "provider": "CTRADER_DEMO",
                    "provider_symbol_id": sid,
                    "provider_symbol": symbol,
                    "temporal_disposition": temporal_values[sid - 1],
                    "relational_comparability_authorized": False,
                }
            )
            frontier = {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": sid,
                "provider_symbol": symbol,
            }
            if disposition == "CURRENT_REFERENCE_VERIFIED":
                frontier["observation_identity"] = f"QORE:REFERENCE:{sid}"
            elif disposition == "VERSIONED_CONTRACT_VERIFIED":
                frontier["observation_identity"] = (
                    f"QORE:FUTURES_CONTRACT:GC:2027-{sid:02d}:COMEX"
                )
            frontier_rows.append(frontier)
            sid += 1

    b06 = {
        "identity": "SHARED_B4_GLOBAL_IDENTITY_DISPOSITION_001",
        "sensor_count": 177,
        "records": b06_rows,
        "registry_fingerprint_sha256": "a" * 64,
        "b06_epistemic_closure_complete": True,
        "calendar_binding_authorized": False,
        "relational_claims_authorized": False,
        "productive_authority": False,
    }
    b07 = {
        "identity": "SHARED_B4_TEMPORAL_DISPOSITION_REGISTRY_001",
        "sensor_count": 177,
        "records": b07_rows,
        "registry_fingerprint_sha256": "b" * 64,
        "b07_epistemic_closure_complete": True,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "comparability_eligible_count": 0,
        "relational_comparability_authorized": False,
        "productive_authority": False,
    }
    frontier = {
        "identity": "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001",
        "sensor_count": 177,
        "records": frontier_rows,
        "frontier_v3_fingerprint_sha256": "c" * 64,
    }
    return b06, b07, frontier


def test_builds_exact_honest_177_row_intake():
    b06, b07, frontier = _payloads()
    batch = build_b4_intake_batch(
        b06_registry=b06,
        b07_registry=b07,
        identity_frontier_v3=frontier,
        fact_timestamp=NOW,
        decision_timestamp=NOW,
    )
    assert len(batch.facts) == 177
    assert batch.resolved_identity_count == 90
    assert batch.unknown_identity_count == 87
    assert batch.comparable_count == 0
    assert batch.relation_eligible_count == 0
    assert all(not fact.a3_consumable_as_certainty for fact in batch.facts)
    assert all(not fact.relation_claim_allowed for fact in batch.facts)
    assert len(batch.fingerprint()) == 64


def test_verified_b06_identity_requires_explicit_upstream_key():
    b06, b07, frontier = _payloads()
    rows = frontier["records"]
    assert isinstance(rows, list)
    rows[0].pop("observation_identity")
    with pytest.raises(
        SharedA3B4IntakeError,
        match="lacks one explicit upstream identity",
    ):
        build_b4_intake_batch(
            b06_registry=b06,
            b07_registry=b07,
            identity_frontier_v3=frontier,
            fact_timestamp=NOW,
            decision_timestamp=NOW,
        )


def test_population_drift_fails_closed():
    b06, b07, frontier = _payloads()
    damaged = deepcopy(b07)
    rows = damaged["records"]
    assert isinstance(rows, list)
    rows.pop()
    with pytest.raises(SharedA3B4IntakeError):
        build_b4_intake_batch(
            b06_registry=b06,
            b07_registry=damaged,
            identity_frontier_v3=frontier,
            fact_timestamp=NOW,
            decision_timestamp=NOW,
        )


def test_authority_widening_fails_closed():
    b06, b07, frontier = _payloads()
    b07["comparability_eligible_count"] = 1
    with pytest.raises(
        SharedA3B4IntakeError,
        match="unexpectedly authorizes comparability",
    ):
        build_b4_intake_batch(
            b06_registry=b06,
            b07_registry=b07,
            identity_frontier_v3=frontier,
            fact_timestamp=NOW,
            decision_timestamp=NOW,
        )
