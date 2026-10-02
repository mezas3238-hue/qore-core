from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_phase22_v5_governance import (
    PHASE22_V5_CANDIDATE,
    V5_CANDIDATE_ID,
    phase22_v5_governance_payload,
)
from qore.infrastructure.cibo_phase22_v5_source_availability import (
    ALLOWED_REQUEST_TYPES,
    assess_probe,
    probe_windows,
)


def test_v5_candidate_is_mechanical_adjacent_and_pre_outcome() -> None:
    candidate = PHASE22_V5_CANDIDATE
    assert candidate.candidate_id == V5_CANDIDATE_ID
    assert candidate.start_at == datetime(2014, 4, 19, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2014, 10, 19, tzinfo=UTC)
    payload = phase22_v5_governance_payload()
    assert payload["selection_outcomes_inspected"] is False
    assert payload["v4_lane_artifact_contents_used_for_selection"] is False
    assert payload["policy_retuning_authorized"] is False
    assert payload["fresh_execution_authorized"] is False
    assert payload["second_v4_execution_authorized"] is False


def test_v5_predecessor_is_terminal_consumed_invalid() -> None:
    forensic = json.loads(
        Path(
            "docs/research/"
            "CIBO-PHASE22-V4-CLAIMED-FAILURE-FORENSIC-RECEIPT.json"
        ).read_text(encoding="utf-8")
    )
    consumption = json.loads(
        Path("docs/research/CIBO-PHASE22-V4-CONSUMPTION-RECEIPT.json").read_text(
            encoding="utf-8"
        )
    )
    assert forensic["terminal_assessment"]["candidate_status"] == (
        "INVALID_CONSUMED"
    )
    assert forensic["terminal_assessment"]["candidate_terminal"] is True
    assert forensic["scientific_integrity"]["v4_reexecution_forbidden"] is True
    assert consumption["claim_committed"] is True
    assert consumption["outcomes_emitted"] is True


def test_v5_probe_surface_allows_only_read_requests() -> None:
    assert ALLOWED_REQUEST_TYPES == {
        "ProtoOAGetTrendbarsReq",
        "ProtoOASymbolsListReq",
    }


def test_v5_probe_windows_and_availability_are_causal() -> None:
    candidate = PHASE22_V5_CANDIDATE
    first, last = probe_windows(
        candidate.start_at,
        candidate.end_exclusive_at,
        "M5",
    )
    result = assess_probe(
        symbol="EURUSD",
        provider_symbol="EURUSD",
        timeframe="M5",
        first_window=first,
        last_window=last,
        first_timestamps=(first[0],),
        last_timestamps=(last[0],),
    )
    assert result.available is True


def test_v5_source_module_has_no_mutation_requests() -> None:
    path = Path(
        "src/qore/infrastructure/cibo_phase22_v5_source_availability.py"
    )
    source = path.read_text(encoding="utf-8")
    for token in (
        "ProtoOANewOrderReq",
        "ProtoOAClosePositionReq",
        "ProtoOACancelOrderReq",
        "ProtoOAAmendOrderReq",
        "ProtoOAAmendPositionSLTPReq",
    ):
        assert token not in source
