from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r62_external_gate_readiness as r62,
)


def test_r62_is_bound_to_exact_frozen_candidate() -> None:
    report = r62.build_report()
    assert report["candidate"]["candidate_id"] == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert report["candidate"]["rule_fingerprint"] == (
        "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
    )
    assert report["candidate"]["candidate_modified"] is False


def test_r62_prepares_all_three_external_gate_requests() -> None:
    report = r62.build_report()
    requests = report["external_gate_requests"]
    assert set(requests) == {
        "risk_review",
        "cibo_review",
        "independent_validation",
    }
    assert requests["risk_review"]["authority"] == "RISK"
    assert requests["cibo_review"]["authority"] == "CIBO"
    assert (
        requests["independent_validation"]["authority"]
        == "INDEPENDENT_VALIDATION"
    )
    for request in requests.values():
        assert request["self_issued_proof"] is False
        assert len(request["request_fingerprint"]) == 64


def test_r62_fails_closed_before_external_proofs() -> None:
    report = r62.build_report()
    assert report["quantitative_certification_ready"] is True
    assert report["external_governed_gates_satisfied"] is False
    assert report["demo_eligible"] is False
    assert report["trader_certified"] is False
    assert report["governance"]["external_proofs_fabricated"] is False
    assert report["governance"]["live_authorized"] is False
