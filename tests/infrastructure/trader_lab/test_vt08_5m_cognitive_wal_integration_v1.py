"""Synthetic-only gate/WAL integration: durable fail-closed lineage across restart."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from test_vt08_cognitive_5m_consumed_gate_v1 import T0, _position, _snapshot

from qore.infrastructure.trader_lab.vt08_b_durable_cognitive_research_ledger_v1 import (
    Vt08DurableResearchLedger,
)
from qore.infrastructure.trader_lab.vt08_cognitive_5m_consumed_gate_v1 import (
    Vt08FiveMarketCognitiveGate,
    Vt08ResearchFillEvidence,
    Vt08ResearchTerminalEvidence,
)

SOURCE = "synthetic-restart-verified-cycle"


def _make_gate(journal: Vt08DurableResearchLedger) -> Vt08FiveMarketCognitiveGate:
    return Vt08FiveMarketCognitiveGate(
        fixture_mode=True, durable_ledger=journal
    )


def _fill() -> Vt08ResearchFillEvidence:
    return Vt08ResearchFillEvidence(
        source_event_id=SOURCE,
        market="EURJPY",
        side="long",
        source_cycle_id="synthetic-h4-cycle-09",
        fill_id="synthetic-fill-one",
        filled_at=T0 + timedelta(minutes=3),
        entry_price=Decimal("100"),
        evidence_sha256="a" * 64,
    )


def _terminal() -> Vt08ResearchTerminalEvidence:
    return Vt08ResearchTerminalEvidence(
        source_event_id=SOURCE,
        market="EURJPY",
        fill_id="synthetic-fill-one",
        fill_evidence_sha256="a" * 64,
        closed_at=T0 + timedelta(minutes=9),
        exit_price=Decimal("101"),
        terminal_reason="TARGET",
        evidence_sha256="b" * 64,
    )


def test_journaled_gate_end_to_end_and_post_restart_tombstone(tmp_path: Path) -> None:
    path = tmp_path / "cognitive.sqlite3"
    with Vt08DurableResearchLedger(path) as journal:
        gate = _make_gate(journal)
        first = gate.evaluate(_snapshot(source=SOURCE, cisd_state="PENDING"))
        assert first.action.value == "WAIT"
        executed = gate.evaluate(
            _snapshot(source=SOURCE, when=T0 + timedelta(minutes=3))
        )
        assert executed.action.value == "EXECUTE"
        gate.record_fill(_fill())
        t = T0 + timedelta(minutes=6)
        pos = gate.evaluate_position(
            _snapshot(
                source=SOURCE, when=t, entry_state="FILLED",
                position_state="OPEN", journey_stage="IN_TRADE",
            ),
            _position(t),
        )
        assert pos.research_only
        gate.record_terminal(_terminal())
        assert [row.kind for row in journal.events()] == [
            "WAIT", "EXECUTE", "FILL", "POSITION", "TERMINAL",
        ]
        assert journal.verify_integrity()[0] == 5
    with Vt08DurableResearchLedger(path) as recovered:
        gate = _make_gate(recovered)
        with pytest.raises(ValueError, match="cannot rearm after restart"):
            gate.evaluate(
                _snapshot(source=SOURCE, when=T0 + timedelta(minutes=12))
            )
        assert gate.decisions == ()
        assert recovered.verify_integrity()[0] == 5


def test_wal_commit_failure_does_not_mutate_decision_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Vt08DurableResearchLedger(tmp_path / "g.sqlite3") as db:
        gate = _make_gate(db)

        def fault(**_: object) -> None:
            raise OSError("injected disk commit failure")

        monkeypatch.setattr(db, "append", fault)
        with pytest.raises(OSError, match="disk commit failure"):
            gate.evaluate(_snapshot(source=SOURCE))
        assert gate.decisions == ()
        assert db.events() == ()


def test_wal_rejected_for_default_unverified_real_source_mode(
    tmp_path: Path,
) -> None:
    with Vt08DurableResearchLedger(tmp_path / "g.sqlite3") as db:
        with pytest.raises(PermissionError, match="synthetic WAL"):
            Vt08FiveMarketCognitiveGate(durable_ledger=db)
