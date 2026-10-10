"""Lineage of an actual type-checked CandidateEvent over closed M15, synthetic fixtures."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab import vt08_5m_a_b_narrow_source_lineage_v1 as lab
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    source_h4_from_m15,
)

NY = ZoneInfo("America/New_York")


def bars_and_candidate() -> tuple[dict[datetime, Vt08B01Bar], SimpleNamespace]:
    t = datetime(2026, 1, 5, 17, tzinfo=NY).astimezone(UTC)
    by_open: dict[datetime, Vt08B01Bar] = {}
    for i in range(2 * 96 + 32):
        s = t + timedelta(minutes=15 * i)
        p = (
            Decimal("100")
            if i < 96
            else Decimal("101")
            if i < 192
            else Decimal("101.5")
        )
        by_open[s] = Vt08B01Bar(
            opened_at=s,
            closed_at=s + timedelta(minutes=15),
            open=p,
            high=p + Decimal("0.25"),
            low=p - Decimal("0.25"),
            close=p,
        )
    anchor = datetime(2026, 1, 8, 1, tzinfo=NY).astimezone(UTC)
    c1 = source_h4_from_m15(
        by_open, opened_at_local=datetime(2026, 1, 7, 17, tzinfo=NY)
    )
    c2 = source_h4_from_m15(
        by_open, opened_at_local=datetime(2026, 1, 7, 21, tzinfo=NY)
    )
    assert c1 is not None and c2 is not None
    candidate = SimpleNamespace(
        symbol="EURJPY",
        decision_at=anchor,
        reference_h4=c1,
        candle2=c2,
        side=DemoTradingSetupSide.LONG,
        protected_swing=SimpleNamespace(
            confirmed_at=anchor - timedelta(minutes=30),
        ),
    )
    return by_open, candidate


class FakeEvent:
    def source_event_id(self) -> str:
        return "vt08-5m-source:" + "c" * 64

    def envelope(self) -> dict[str, object]:
        return {
            "source_event_id": self.source_event_id(),
            "event_id": "vt08-5m:" + "d" * 64,
            "event_fingerprint": "d" * 64,
            "market": "EURJPY",
            "bias_feature_cutoff": "UNATTESTED_IN_LEGACY_B01_CANDIDATE",
        }


def test_attach_actual_completed_day_and_h4_provenance_without_signing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    by_open, candidate = bars_and_candidate()
    monkeypatch.setattr(
        lab,
        "from_narrow_b01_candidate",
        lambda x, *, evidence_sha256: FakeEvent(),
    )
    result = lab.attest_narrow_candidate(
        candidate=candidate, bars_by_open=by_open,
    )
    expected = datetime(2026, 1, 7, 17, tzinfo=NY).astimezone(UTC)
    assert result["bias_feature_cutoff"] == expected.isoformat()
    assert result["bias_asof_evidence"]["bias_side"] == "long"
    assert result["bias_asof_evidence"]["source_day_current"]["m15_count"] == 96
    assert len(result["h4_source_m15_provenance"]["c2_m15_sha256"]) == 64
    assert "cognitive_feature_cutoffs" not in result
    assert result["joint_a_b_contract_signed"] is False
    assert result["cognitive_feature_provenance_complete"] is False
    assert result["trades_executed"] == 0


def test_c2_ohlc_source_mutation_invalidates_derived_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    by_open, candidate = bars_and_candidate()
    monkeypatch.setattr(
        lab,
        "from_narrow_b01_candidate",
        lambda x, *, evidence_sha256: FakeEvent(),
    )
    t = candidate.candle2.opened_at
    row = by_open[t]
    by_open[t] = replace(row, high=row.high + Decimal("20"))
    with pytest.raises(ValueError, match="not authenticated"):
        lab.attest_narrow_candidate(
            candidate=candidate, bars_by_open=by_open,
        )


def test_cisd_from_future_bar_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    by_open, candidate = bars_and_candidate()
    monkeypatch.setattr(
        lab,
        "from_narrow_b01_candidate",
        lambda x, *, evidence_sha256: FakeEvent(),
    )
    candidate.protected_swing.confirmed_at = candidate.decision_at + timedelta(
        minutes=15
    )
    with pytest.raises(ValueError, match="future"):
        lab.attest_narrow_candidate(candidate=candidate, bars_by_open=by_open)


def test_missing_15m_source_fail_closed() -> None:
    by_open, candidate = bars_and_candidate()
    by_open.pop(candidate.candle2.opened_at)
    with pytest.raises(ValueError, match="constituent M15 missing"):
        lab.attest_narrow_candidate(candidate=candidate, bars_by_open=by_open)
