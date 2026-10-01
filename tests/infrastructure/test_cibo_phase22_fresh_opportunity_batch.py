from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
    build_phase22_fresh_opportunity_batch,
    native_fresh_opportunity,
    turtle_geometry_opportunity,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _turtle_row() -> dict[str, object]:
    return {
        "signal_at": "2015-10-20T12:00:00+00:00",
        "entry_at": "2015-10-20T12:05:00+00:00",
        "exit_at": "2015-10-20T13:00:00+00:00",
        "side": "long",
        "entry_price": "100",
        "structural_stop": "99",
        "technical_target": "102",
        "exit_reason": "TARGET",
        "raw_net_010_r": "2",
        "scaled_net_010_r": "0.10",
        "risk_scale": "0.05",
    }


def test_turtle_normalization_uses_raw_structural_r_not_legacy_scale() -> None:
    opportunity = turtle_geometry_opportunity(
        trader_id="R43_GBPUSD",
        qore_symbol="GBPUSD",
        row=_turtle_row(),
        methodology_sha256=_sha("method"),
        source_evidence_ids=("v2-source", "frozen-method"),
    )

    assert opportunity.gross_structural_outcome_r == Decimal("2")
    assert opportunity.payload()["legacy_trader_sizing_used_for_cibo"] is False
    assert opportunity.payload()["volume"] is None


def test_native_vt31_vt08_surface_is_volume_free() -> None:
    row = {
        "signal_at": "2015-10-20T12:00:00+00:00",
        "entry_at": "2015-10-20T12:05:00+00:00",
        "exit_at": "2015-10-20T13:00:00+00:00",
        "side": "short",
        "entry": "100",
        "stop": "101",
        "target": "98",
        "exit_reason": "target",
        "realized_r": "2",
        "methodology_sha256": _sha("native-method"),
        "signal_fingerprint": _sha("signal"),
    }
    opportunity = native_fresh_opportunity(
        trader_id="VT31_NAS100",
        qore_symbol="NAS100",
        row=row,
        source_evidence_ids=("nas100-m1",),
    )
    assert opportunity.trader_id is TraderLineage.VT31_NAS100
    assert opportunity.payload()["volume"] is None


def _opportunity(trader_id: str, index: int) -> Phase22FreshOpportunity:
    lineage = TraderLineage(trader_id)
    at = datetime(2015, 10, 20, 12, index, tzinfo=UTC)
    if index % 2:
        side = "short"
        stop = Decimal("101")
        target = Decimal("98")
    else:
        side = "long"
        stop = Decimal("99")
        target = Decimal("102")
    return Phase22FreshOpportunity(
        trader_id=lineage,
        qore_symbol="NAS100" if trader_id == "VT31_NAS100" else "GBPUSD",
        signal_fingerprint=_sha(f"signal-{trader_id}"),
        signal_at=at,
        entry_at=at,
        exit_at=at.replace(hour=13),
        side=side,
        entry_price=Decimal("100"),
        structural_stop=stop,
        technical_target=target,
        exit_reason="TARGET",
        gross_structural_outcome_r=Decimal("2"),
        methodology_sha256=_sha(f"method-{trader_id}"),
        source_evidence_ids=(f"source-{trader_id}",),
    )


def test_batch_requires_exact_7_and_sorts_chronologically() -> None:
    traders = tuple(
        Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256=_sha(f"artifact-{trader_id}"),
            opportunities=(_opportunity(trader_id, 6 - index),),
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        for index, trader_id in enumerate(CANONICAL_PHASE22_TRADER_IDS)
    )
    batch = build_phase22_fresh_opportunity_batch(traders)

    assert tuple(item.trader_id for item in batch.traders) == (
        CANONICAL_PHASE22_TRADER_IDS
    )
    assert tuple(item.signal_at for item in batch.opportunities) == tuple(
        sorted(item.signal_at for item in batch.opportunities)
    )
    assert batch.legacy_trader_sizing_used_for_cibo is False
    assert batch.fingerprint().startswith("sha256:")


def test_batch_rejects_missing_trader() -> None:
    traders = tuple(
        Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256=_sha(f"artifact-{trader_id}"),
            opportunities=(),
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        for trader_id in CANONICAL_PHASE22_TRADER_IDS[:-1]
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact ordered 7/7",
    ):
        build_phase22_fresh_opportunity_batch(traders)
