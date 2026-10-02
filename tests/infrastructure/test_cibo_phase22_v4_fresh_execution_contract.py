from __future__ import annotations

from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshTraderEvidence,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_fresh_batch import (
    build_phase22_v4_fresh_batch,
)
from qore.infrastructure.cibo_phase22_v4_fresh_evidence import (
    TURTLE_SURFACE,
    source_evidence_ids,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID


def test_v4_empty_lane_contract_still_requires_exact_ordered_7_7() -> None:
    traders = tuple(
        Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256="sha256:" + f"{index + 1:064x}",
            opportunities=(),
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        for index, trader_id in enumerate(CANONICAL_PHASE22_TRADER_IDS)
    )
    batch = build_phase22_v4_fresh_batch(traders)

    assert batch.candidate_id == V4_CANDIDATE_ID
    assert tuple(item.trader_id for item in batch.traders) == (
        CANONICAL_PHASE22_TRADER_IDS
    )
    assert batch.opportunities == ()
    assert batch.productive_authority is False


def test_v4_source_evidence_is_receipt_and_parity_bound() -> None:
    ids = source_evidence_ids(
        trader_id="VT31_NAS100",
        symbol="NAS100",
    )

    assert len(ids) == 4
    assert ids[0].startswith("sha256:")
    assert ids[1].startswith("sha256:")
    assert ids[2].startswith("git:")
    assert ids[3].startswith("sha256:")


def test_v4_turtle_surface_is_exact_five_lane_contract() -> None:
    assert TURTLE_SURFACE == (
        ("R34_XAUUSD", "XAUUSD"),
        ("R38_EURUSD", "EURUSD"),
        ("R43_GBPUSD", "GBPUSD"),
        ("R38_GBPJPY", "GBPJPY"),
        ("R42_AUDJPY", "AUDJPY"),
    )
