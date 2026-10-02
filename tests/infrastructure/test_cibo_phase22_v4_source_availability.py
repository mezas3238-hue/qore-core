from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_phase22_v4_governance import (
    PHASE22_V4_CANDIDATE,
    V4_CANDIDATE_ID,
    phase22_v4_governance_payload,
)
from qore.infrastructure.cibo_phase22_v4_source_availability import (
    ALLOWED_REQUEST_TYPES,
    assess_probe,
    probe_windows,
)


def test_v4_candidate_is_mechanical_adjacent_and_pre_outcome() -> None:
    candidate = PHASE22_V4_CANDIDATE
    assert candidate.candidate_id == V4_CANDIDATE_ID
    assert candidate.start_at == datetime(2014, 10, 19, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2015, 4, 19, tzinfo=UTC)
    payload = phase22_v4_governance_payload()
    assert payload["selection_outcomes_inspected"] is False
    assert payload["v3_lane_artifact_contents_used_for_selection"] is False
    assert payload["policy_retuning_authorized"] is False
    assert payload["fresh_execution_authorized"] is False
    assert payload["second_v3_execution_authorized"] is False


def test_v4_probe_surface_allows_only_read_requests() -> None:
    assert ALLOWED_REQUEST_TYPES == {
        "ProtoOAGetTrendbarsReq",
        "ProtoOASymbolsListReq",
    }


def test_v4_probe_windows_and_availability_are_causal() -> None:
    candidate = PHASE22_V4_CANDIDATE
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


def test_v4_source_module_has_no_mutation_requests() -> None:
    path = Path(
        "src/qore/infrastructure/cibo_phase22_v4_source_availability.py"
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
