"""Cross-branch integration against Architect A's actual frozen GitHub module.

CI checks out A at an exact SHA. This test dynamically reads A's source file,
does not copy or mutate it, and verifies B refuses to invent missing evidence.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_5m_a_to_b_candidate_readiness_v1 import (
    Vt08CandidateBoundaryError,
    inspect_architect_a_candidate,
)


def _real_a_golden() -> object:
    location = os.environ.get("VT08_ARCHITECT_A_FROZEN_MODULE")
    if not location:
        pytest.skip("cross-branch source fixture only available in frozen CI checkout")
    path = Path(location)
    assert path.is_file(), "GitHub A contract checkout failed"
    spec = importlib.util.spec_from_file_location("vt08_a_frozen_source_module", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    ny = ZoneInfo("America/New_York")
    anchor = datetime(2026, 1, 5, 1, tzinfo=ny)
    return module.Vt08CandidateEventV1(
        market="EURJPY",
        source_family="positional-entry",
        ltf_profile="M15_STANDARD",
        side="long",
        scenario="C2_COMPLETED",
        h4_anchor_at=anchor,
        decision_at=anchor,
        evidence_as_of=anchor,
        candle2_closed_at=anchor,
        opposing_series_opened_at=anchor - timedelta(hours=2),
        cisd_confirmed_at=anchor - timedelta(minutes=15),
        ps_confirmed_at=anchor - timedelta(minutes=15),
        entry_price=Decimal("160.00"),
        stop_price=Decimal("159.50"),
        target_price=Decimal("161.00"),
        pending_expiry_at=anchor + timedelta(hours=4),
        source_methodology_sha256="a" * 64,
        evidence_sha256="b" * 64,
    )


def test_actual_a_methodology_contract_is_parsed_but_not_mislabelled_ready() -> None:
    actual = _real_a_golden()
    # The exact source method belongs to Architect A's implementation.
    envelope = actual.envelope()
    result = inspect_architect_a_candidate(envelope)
    assert result.market == "EURJPY"
    assert result.source_event_id == actual.source_event_id()
    assert result.snapshot_event_id == envelope["event_id"]
    assert result.cognitive_ready is False
    assert "A_B:DAILY_BIAS_SOURCE_TIME_UNATTESTED" in result.blockers
    assert "A_B:COGNITIVE_FEATURE_PROVENANCE_INCOMPLETE" in result.blockers
    assert "A_B:CONTRACT_NOT_JOINTLY_FROZEN" in result.blockers


def test_a_source_event_identity_survives_snapshot_evidence_changes() -> None:
    actual = _real_a_golden()
    alternative = replace(actual, evidence_sha256="c" * 64)
    assert actual.source_event_id() == alternative.source_event_id()
    assert actual.fingerprint() != alternative.fingerprint()
    assert inspect_architect_a_candidate(actual.envelope()).source_event_id == (
        inspect_architect_a_candidate(alternative.envelope()).source_event_id
    )


def test_b_rejects_a_envelope_if_a_source_confirmation_goes_into_future() -> None:
    actual = _real_a_golden()
    contents = actual.envelope()
    feature_times = dict(contents["feature_close_cutoffs"])
    feature_times["cisd"] = (
        actual.decision_at + timedelta(minutes=1)
    ).isoformat()
    contents["feature_close_cutoffs"] = feature_times
    with pytest.raises(Vt08CandidateBoundaryError, match="future source confirmation"):
        inspect_architect_a_candidate(contents)
