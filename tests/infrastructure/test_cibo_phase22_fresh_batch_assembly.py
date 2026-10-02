from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    build_phase22_execution_claim,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_fresh_batch_assembly import (
    assemble_phase22_fresh_batch,
    frozen_source_evidence_ids,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import CANDIDATE_ID
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
    CANONICAL_PHASE22_TRADER_IDS,
)

T0 = datetime(2016, 1, 4, 10, 0, tzinfo=UTC)


def _sha(label: str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _parity(trader_id: str):
    manifest = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    assert manifest is not None
    return next(item for item in manifest.receipts if item.trader_id == trader_id)


def _claim():
    manifest = build_phase22_execution_manifest()
    return build_phase22_execution_claim(
        candidate_id=CANDIDATE_ID,
        execution_manifest_sha256=manifest.fingerprint(),
        claim_head_sha="a" * 40,
        claim_run_id=123,
        claim_run_attempt=1,
    )


def _native_row(trader_id: str, symbol: str, minute: int) -> dict[str, object]:
    parity = _parity(trader_id)
    at = T0 + timedelta(minutes=minute)
    return {
        "trader_id": trader_id,
        "symbol": symbol,
        "signal_fingerprint": _sha(f"{trader_id}-signal"),
        "signal_at": at.isoformat(),
        "entry_at": (at + timedelta(minutes=1)).isoformat(),
        "exit_at": (at + timedelta(minutes=20)).isoformat(),
        "side": "long",
        "entry": "100",
        "stop": "99",
        "target": "102",
        "exit_reason": "target",
        "realized_r": "2",
        "methodology_sha256": parity.parameter_sha256,
    }


def _native_payload(
    trader_id: str,
    symbol: str,
    minute: int,
) -> dict[str, object]:
    return {
        "candidate_id": CANDIDATE_ID,
        "trader_id": trader_id,
        "opportunities": [_native_row(trader_id, symbol, minute)],
        "fresh_outcomes_executed": True,
        "methodology_changed": False,
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
    }


def _turtle_row(trader_id: str, minute: int) -> dict[str, object]:
    at = T0 + timedelta(minutes=minute)
    return {
        "signal_at": at.isoformat(),
        "entry_at": (at + timedelta(minutes=1)).isoformat(),
        "exit_at": (at + timedelta(minutes=20)).isoformat(),
        "side": "long",
        "entry_price": "100",
        "structural_stop": "99",
        "technical_target": "102",
        "exit_reason": "target",
        "raw_net_010_r": "2",
    }


def _surface():
    turtle_ids = (
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
    )
    turtle = {
        trader_id: (_turtle_row(trader_id, 10 + index),)
        for index, trader_id in enumerate(turtle_ids)
    }
    digests = {
        trader_id: _sha(f"lane-{trader_id}")
        for trader_id in CANONICAL_PHASE22_TRADER_IDS
    }
    return turtle, digests


def test_assembly_builds_exact_seven_trader_chronological_surface() -> None:
    turtle, digests = _surface()
    batch = assemble_phase22_fresh_batch(
        vt08_payload=_native_payload("VT08_FOREX", "GBPUSD", 1),
        turtle_rows=turtle,
        vt31_payload=_native_payload("VT31_NAS100", "NAS100", 30),
        lane_artifact_sha256s=digests,
        consumption_receipt=_claim(),
    )

    assert tuple(item.trader_id for item in batch.traders) == (
        CANONICAL_PHASE22_TRADER_IDS
    )
    assert len(batch.opportunities) == 7
    assert tuple(item.signal_at for item in batch.opportunities) == tuple(
        sorted(item.signal_at for item in batch.opportunities)
    )
    assert all(item.payload()["volume"] is None for item in batch.opportunities)
    assert batch.productive_authority is False


def test_assembly_requires_durable_claim_before_fresh_results() -> None:
    turtle, digests = _surface()

    with pytest.raises(
        CiboCapitalManagementError,
        match="durable one-shot claim",
    ):
        assemble_phase22_fresh_batch(
            vt08_payload=_native_payload("VT08_FOREX", "GBPUSD", 1),
            turtle_rows=turtle,
            vt31_payload=_native_payload("VT31_NAS100", "NAS100", 30),
            lane_artifact_sha256s=digests,
            consumption_receipt=None,
        )


def test_native_methodology_drift_is_rejected() -> None:
    turtle, digests = _surface()
    vt31 = _native_payload("VT31_NAS100", "NAS100", 30)
    row = dict(vt31["opportunities"][0])  # type: ignore[index]
    row["methodology_sha256"] = _sha("wrong-methodology")
    vt31["opportunities"] = [row]

    with pytest.raises(
        CiboCapitalManagementError,
        match="methodology drift",
    ):
        assemble_phase22_fresh_batch(
            vt08_payload=_native_payload("VT08_FOREX", "GBPUSD", 1),
            turtle_rows=turtle,
            vt31_payload=vt31,
            lane_artifact_sha256s=digests,
            consumption_receipt=_claim(),
        )


def test_vt31_source_lineage_is_bound_to_m1_not_m5() -> None:
    ids = frozen_source_evidence_ids(
        trader_id="VT31_NAS100",
        qore_symbol="NAS100",
    )

    assert _parity("VT31_NAS100").parity_artifact_digest in ids
    assert any(
        item.artifact_digest in ids and item.timeframe == "M1"
        for item in __import__(
            "qore.infrastructure.cibo_phase22_holdout_v2_source_receipt",
            fromlist=["V2_SOURCE_BINDINGS"],
        ).V2_SOURCE_BINDINGS
        if item.symbol == "NAS100"
    )


def test_lane_digest_surface_must_be_exact_7_of_7() -> None:
    turtle, digests = _surface()
    digests.pop("R34_XAUUSD")

    with pytest.raises(
        CiboCapitalManagementError,
        match="lane artifact surface drift",
    ):
        assemble_phase22_fresh_batch(
            vt08_payload=_native_payload("VT08_FOREX", "GBPUSD", 1),
            turtle_rows=turtle,
            vt31_payload=_native_payload("VT31_NAS100", "NAS100", 30),
            lane_artifact_sha256s=digests,
            consumption_receipt=_claim(),
        )
