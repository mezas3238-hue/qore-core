"""Adversarial SQLite WAL tests. No market or broker authority is asserted."""
from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_b_durable_cognitive_research_ledger_v1 import (
    Vt08DurableResearchLedger,
)

T = datetime(2026, 1, 5, 6, tzinfo=UTC)
E = "synthetic:eurjpy:cycle-01"
IDENTITY_SHA = "a" * 64
H = "b" * 64


def _add(
    db: Vt08DurableResearchLedger, kind: str, when: datetime = T,
    *, source: str = E, market: str = "EURJPY", evidence: str = H,
    fill_id: str | None = None, identity: str = IDENTITY_SHA,
):
    return db.append(
        source_event_id=source, market=market, kind=kind,
        as_of=when, identity_sha256=identity,
        evidence_sha256=evidence, fill_id=fill_id,
    )


def test_reopen_wait_execute_fill_position_terminal_preserves_chain(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ledger.sqlite3"
    with Vt08DurableResearchLedger(db_path) as db:
        wait = _add(db, "WAIT")
        assert wait.inserted and wait.seq == 1
        assert _add(db, "WAIT").seq == 1
        assert _add(db, "WAIT").inserted is False
        assert _add(db, "EXECUTE", T + timedelta(minutes=3)).seq == 2
        count, sha = db.verify_integrity()
        assert count == 2 and sha != "0" * 64
    with Vt08DurableResearchLedger(db_path) as restored:
        fill = _add(
            restored, "FILL", T + timedelta(minutes=3), fill_id="fill-001",
        )
        assert fill.seq == 3
        _add(restored, "POSITION", T + timedelta(minutes=6))
        end = _add(
            restored, "TERMINAL", T + timedelta(minutes=9), fill_id="fill-001",
        )
        assert end.seq == 5
        assert restored.verify_integrity()[0] == 5
        assert len(restored.events()) == 5
    with Vt08DurableResearchLedger(db_path) as again:
        assert _add(
            again, "TERMINAL", T + timedelta(minutes=9), fill_id="fill-001",
        ).inserted is False
        with pytest.raises(ValueError, match="terminal/killed"):
            _add(again, "POSITION", T + timedelta(minutes=12))
        assert again.verify_integrity()[0] == 5


def test_abstain_killed_tombstone_survives_restart(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite"
    with Vt08DurableResearchLedger(path) as db:
        _add(db, "WAIT")
        _add(db, "ABSTAIN", T + timedelta(minutes=3))
    with Vt08DurableResearchLedger(path) as db:
        with pytest.raises(ValueError, match="terminal/killed"):
            _add(db, "EXECUTE", T + timedelta(minutes=6))
        assert db.verify_integrity()[0] == 2


def test_no_fill_without_execute_or_reuse_of_fill_id(tmp_path: Path) -> None:
    with Vt08DurableResearchLedger(tmp_path / "ledger.sqlite") as db:
        _add(db, "WAIT")
        with pytest.raises(ValueError, match="unique EXECUTE"):
            _add(db, "FILL", fill_id="one")
        _add(db, "EXECUTE", T + timedelta(minutes=3))
        _add(db, "FILL", T + timedelta(minutes=3), fill_id="one")
        _add(db, "EXECUTE", T + timedelta(minutes=6),
             source="synthetic:second", market="USDCHF")
        with pytest.raises(ValueError, match="fill_id reused"):
            _add(db, "FILL", T + timedelta(minutes=6),
                 source="synthetic:second", market="USDCHF", fill_id="one")
        assert db.verify_integrity()[0] == 4


def test_no_duplicate_contradiction_or_identity_drift(tmp_path: Path) -> None:
    with Vt08DurableResearchLedger(tmp_path / "ledger.sqlite") as db:
        _add(db, "WAIT")
        with pytest.raises(ValueError, match="conflicting evidence"):
            _add(db, "WAIT", evidence="c" * 64)
        with pytest.raises(ValueError, match="identity drift"):
            _add(db, "EXECUTE", T + timedelta(minutes=3), identity="c" * 64)
        with pytest.raises(ValueError, match="identity drift"):
            _add(db, "EXECUTE", T + timedelta(minutes=3), market="USDCAD")
        assert db.verify_integrity()[0] == 1


def test_out_of_order_cross_market_rejected_without_state_change(
    tmp_path: Path,
) -> None:
    with Vt08DurableResearchLedger(tmp_path / "ledger.sqlite") as db:
        _add(db, "EXECUTE", T + timedelta(minutes=3))
        with pytest.raises(ValueError, match="global source time regression"):
            _add(db, "WAIT", T, source="other", market="NZDUSD")
        assert db.verify_integrity()[0] == 1


def test_duplicate_decision_time_after_wait_rejected(tmp_path: Path) -> None:
    with Vt08DurableResearchLedger(tmp_path / "ledger.sqlite") as db:
        _add(db, "WAIT")
        with pytest.raises(ValueError, match="decision timestamp must advance"):
            _add(db, "EXECUTE")
        assert db.verify_integrity()[0] == 1


def test_terminal_wrong_fill_id_or_fill_without_evidence_rejected(
    tmp_path: Path,
) -> None:
    with Vt08DurableResearchLedger(tmp_path / "ledger.sqlite") as db:
        _add(db, "EXECUTE")
        with pytest.raises(ValueError, match="requires fill"):
            _add(db, "POSITION", T + timedelta(minutes=2))
        _add(db, "FILL", T + timedelta(minutes=2), fill_id="fill-a")
        with pytest.raises(ValueError, match="lineage drift"):
            _add(db, "TERMINAL", T + timedelta(minutes=3), fill_id="fill-b")
        assert db.verify_integrity()[0] == 2


def test_concurrent_connections_dedupe_and_no_double_fill(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite"
    with Vt08DurableResearchLedger(path) as initial:
        _add(initial, "EXECUTE")
    def write_once(_: int) -> bool:
        with Vt08DurableResearchLedger(path) as db:
            return _add(
                db, "FILL", T + timedelta(minutes=3), fill_id="same-fill",
            ).inserted
    with ThreadPoolExecutor(max_workers=6) as executor:
        outcomes = list(executor.map(write_once, range(12)))
    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 11
    with Vt08DurableResearchLedger(path) as db:
        assert db.verify_integrity()[0] == 2


def test_mutated_row_detected_after_crash_reopen(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite"
    with Vt08DurableResearchLedger(path) as db:
        _add(db, "WAIT")
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE vt08_wal_v1 SET market='CADJPY' WHERE seq=1")
    with pytest.raises(ValueError, match="tampered"):
        Vt08DurableResearchLedger(path)


def test_only_research_non_operational_events(tmp_path: Path) -> None:
    with Vt08DurableResearchLedger(tmp_path / "ledger.sqlite") as db:
        with pytest.raises(ValueError, match="unknown event kind"):
            _add(db, "BROKER_ORDER")
        with pytest.raises(ValueError, match="invalid SHA256"):
            _add(db, "EXECUTE", identity="bad")
        event = _add(db, "WAIT")
        assert event.research_only and not event.broker_authorized
