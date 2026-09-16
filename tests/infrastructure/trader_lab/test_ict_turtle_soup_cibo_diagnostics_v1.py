from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_cibo_diagnostics_v1 import (
    _functional_evidence,
    diagnose_holdout,
)


def _trade() -> dict[str, object]:
    return {
        "symbol": "EURUSD",
        "side": "long",
        "daily_c2_opened_at": "2017-01-02T22:00:00+00:00",
        "h4_c2_opened_at": "2017-01-03T09:00:00+00:00",
        "entry_at": "2017-01-03T13:00:00+00:00",
        "exit_at": "2017-01-03T17:00:00+00:00",
        "exit_reason": "target",
        "gross_r": "1.25",
        "primary_net_r": "1.20",
    }


def _event_row(timeframe: str, opened: str, *, hit_minutes: str) -> dict[str, str]:
    return {
        "symbol": "EURUSD",
        "timeframe": timeframe,
        "reference_type": "prior-candle",
        "side": "long",
        "source_opened_at": opened,
        "raid_at": opened,
        "same_source_reclaim": "True",
        "cisd_confirmed": "False",
        "fvg_after_raid": "True",
        "exact_equal_count": "1",
        "opposite_reference_hit_24h": "True",
        "opposite_reference_hit_minutes": hit_minutes,
    }


def _write_fixture(tmp_path: Path, *, missing_h4: bool = False) -> tuple[Path, Path]:
    trades = tmp_path / "trades.json"
    events = tmp_path / "events.csv"
    trades.write_text(json.dumps([_trade()]))
    rows = [_event_row("D1", "2017-01-02T22:00:00+00:00", hit_minutes="120")]
    if not missing_h4:
        rows.append(_event_row("H4", "2017-01-03T09:00:00+00:00", hit_minutes="30"))
    with events.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return trades, events


def test_exact_linkage_and_pre_entry_state(tmp_path: Path) -> None:
    trades, events = _write_fixture(tmp_path)
    diagnostics = diagnose_holdout(trades, events)
    assert len(diagnostics) == 1
    item = diagnostics[0]
    assert item.d1_full_c1_traverse_pre_entry is True
    assert item.h4_full_c1_traverse_pre_entry is True
    assert item.market_phase == "two-level-full-range-repricing"
    assert item.d1_reclaim_observed is True
    assert item.h4_reclaim_observed is True
    assert item.authority == CiboFunctionalAuthority.OBSERVATION.value


def test_missing_exact_h4_match_fails_closed(tmp_path: Path) -> None:
    trades, events = _write_fixture(tmp_path, missing_h4=True)
    with pytest.raises(ValueError, match="missing exact prior-candle events"):
        diagnose_holdout(trades, events)


def test_late_opposite_hit_is_not_pre_entry(tmp_path: Path) -> None:
    trades, events = _write_fixture(tmp_path)
    rows = list(csv.DictReader(events.open()))
    rows[0]["opposite_reference_hit_minutes"] = "1000"
    with events.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    item = diagnose_holdout(trades, events)[0]
    assert item.d1_full_c1_traverse_pre_entry is False
    assert "e1-clue.d1-incomplete-full-range-repricing" in item.diagnostic_cause_codes


def test_cibo_evidence_is_dependency_bounded() -> None:
    evidence = _functional_evidence(datetime(2017, 1, 3, 17, tzinfo=UTC))
    assert evidence.status is CiboEvidenceStatus.EVIDENCE_DEPENDENT
    assert tuple(ref.value for ref in evidence.evidence_refs) == (
        "lab:ict-ts-behavior-v1:run-35125861002",
        "lab:ict-ts-r5-holdout:run-35118222306",
    )
    assert "no-authority-root" in evidence.reasons
