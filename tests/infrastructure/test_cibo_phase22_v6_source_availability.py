from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_phase22_v6_governance import (
    PHASE22_V6_CANDIDATE,
    V6_CANDIDATE_ID,
    phase22_v6_governance_payload,
)
from qore.infrastructure.cibo_phase22_v6_source_availability import (
    ALLOWED_REQUEST_TYPES,
    assess_probe,
    probe_windows,
)


def test_v6_candidate_is_mechanical_adjacent_and_pre_outcome() -> None:
    candidate = PHASE22_V6_CANDIDATE
    assert candidate.candidate_id == V6_CANDIDATE_ID
    assert candidate.start_at == datetime(2013, 10, 19, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2014, 4, 19, tzinfo=UTC)
    payload = phase22_v6_governance_payload()
    assert payload["selection_outcomes_inspected"] is False
    assert payload["v5_fresh_execution_occurred"] is False
    assert payload["v5_outcomes_exist"] is False
    assert payload["fresh_execution_authorized"] is False


def test_v6_selection_is_bound_to_v5_source_unavailability() -> None:
    receipt = json.loads(
        Path(
            "docs/research/CIBO-PHASE22-V5-SOURCE-UNAVAILABLE-RECEIPT.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["source_available"] is False
    assert receipt["status"] == "SOURCE_UNAVAILABLE"
    assert receipt["trader_logic_executed"] is False
    assert receipt["outcomes_inspected"] is False
    assert receipt["fresh_execution_authorized"] is False
    assert {
        (item["symbol"], item["timeframe"])
        for item in receipt["unavailable_sources"]
    } == {("NAS100", "M5"), ("NAS100", "M1")}


def test_v6_probe_surface_allows_only_read_requests() -> None:
    assert ALLOWED_REQUEST_TYPES == {
        "ProtoOAGetTrendbarsReq",
        "ProtoOASymbolsListReq",
    }


def test_v6_probe_windows_and_availability_are_causal() -> None:
    candidate = PHASE22_V6_CANDIDATE
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


def test_v6_source_module_has_no_mutation_requests() -> None:
    path = Path(
        "src/qore/infrastructure/cibo_phase22_v6_source_availability.py"
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
