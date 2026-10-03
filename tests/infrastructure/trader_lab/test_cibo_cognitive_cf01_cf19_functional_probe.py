from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from qore.infrastructure.cibo_capability_exam_cognitive_coverage import (
    EXPECTED_FACULTIES,
    EXPECTED_TOOLS,
    build_cibo_capability_cognitive_coverage,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 2, 55, tzinfo=UTC)


def _candidate_batch_sha(candidate: TraderLabCandidateBinding) -> str:
    payload = (
        "qore:trader-lab:cibo-cognitive:"
        + candidate.fingerprint.value
    ).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def test_trader_lab_cibo_cognitive_cf01_cf19_executes_full_chain(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=921)
    expected_sha = _candidate_batch_sha(candidate)

    receipt = build_cibo_capability_cognitive_coverage(
        source_batch_sha256=expected_sha,
        observed_at=NOW,
    )

    assert receipt.source_batch_sha256 == expected_sha
    assert receipt.complete is True
    assert receipt.cognitive_used is True
    assert receipt.all_functional_faculties_consulted is True
    assert receipt.all_ce2i_tools_registered is True
    assert receipt.mission_faculties == tuple(
        item.value for item in EXPECTED_FACULTIES
    )
    assert receipt.coordinated_faculties == tuple(
        item.value for item in EXPECTED_FACULTIES
    )
    assert len(receipt.coordinated_faculties) == 19
    assert receipt.ce2i_tool_codes == EXPECTED_TOOLS
    assert receipt.reasoning_route_tier
    assert receipt.reasoning_mode
    assert receipt.reasoning_route_reason
    assert receipt.mission_code
    assert receipt.coordination_disposition
    assert receipt.executive_directive
    assert receipt.trader_sizing_authority == "NONE"
    assert receipt.cibo_sizing_authority == "CIBO_CMA"
    assert receipt.qore_risk_sovereign is True
    assert receipt.broker_mutation_authorized is False
    assert receipt.live_authorized is False
    assert receipt.real_capital_authorized is False
    assert receipt.production_authorized is False
    assert receipt.merge_authorized is False


def test_trader_lab_cognitive_receipt_is_candidate_bound(
    candidate_factory,
) -> None:
    left = candidate_factory(candidate_suffix=922, version="v1")
    right = candidate_factory(candidate_suffix=923, version="v1")

    left_receipt = build_cibo_capability_cognitive_coverage(
        source_batch_sha256=_candidate_batch_sha(left),
        observed_at=NOW,
    )
    right_receipt = build_cibo_capability_cognitive_coverage(
        source_batch_sha256=_candidate_batch_sha(right),
        observed_at=NOW,
    )

    assert left.fingerprint != right.fingerprint
    assert left_receipt.source_batch_sha256 != right_receipt.source_batch_sha256
