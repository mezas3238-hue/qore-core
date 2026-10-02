"""Fail-closed assembly of the exact seven-Trader Phase22 V2 fresh surface.

This module never runs Trader logic and never reads the fresh source corpus.
It accepts already-produced fresh lane payloads only after a durable one-shot
claim exists, binds every opportunity to frozen parity/source identities, and
returns the canonical chronological volume-free batch.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
    load_phase22_execution_consumption_receipt,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunityBatch,
    Phase22FreshTraderEvidence,
    build_phase22_fresh_opportunity_batch,
    native_fresh_opportunity,
    turtle_geometry_opportunity,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
    V2_SOURCE_BINDINGS,
    phase22_v2_holdout_source_receipt_sha256,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
    CANONICAL_PHASE22_TRADER_IDS,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TURTLE_SURFACE = (
    ("R34_XAUUSD", "XAUUSD"),
    ("R38_EURUSD", "EURUSD"),
    ("R43_GBPUSD", "GBPUSD"),
    ("R38_GBPJPY", "GBPJPY"),
    ("R42_AUDJPY", "AUDJPY"),
)
_NATIVE_SURFACE = {
    "VT08_FOREX",
    "VT31_NAS100",
}


def _require_sha256(value: str, name: str) -> str:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"Phase22 fresh assembly {name} must be sha256"
        )
    return value


def _parity_receipt(trader_id: str):
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    if parity is None:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly parity manifest missing"
        )
    for receipt in parity.receipts:
        if receipt.trader_id == trader_id:
            return receipt
    raise CiboCapitalManagementError(
        f"Phase22 fresh assembly parity receipt missing: {trader_id}"
    )


def _source_binding(symbol: str, *, timeframe: str):
    matches = tuple(
        item
        for item in V2_SOURCE_BINDINGS
        if item.symbol == symbol and item.timeframe == timeframe
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly exact source binding missing"
        )
    return matches[0]


def frozen_source_evidence_ids(
    *,
    trader_id: str,
    qore_symbol: str,
) -> tuple[str, ...]:
    """Return only identities frozen before fresh outcomes were observed."""

    parity = _parity_receipt(trader_id)
    timeframe = "M1" if trader_id == "VT31_NAS100" else "M5"
    source = _source_binding(qore_symbol, timeframe=timeframe)
    values = (
        phase22_v2_holdout_source_receipt_sha256(),
        source.artifact_digest,
        f"git:{parity.methodology_git_sha}",
        parity.parity_artifact_digest,
    )
    if len(values) != len(set(values)):
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly source evidence duplicated"
        )
    return values


def assert_durable_phase22_claim(
    receipt: Phase22ExecutionConsumptionReceipt | None = None,
) -> Phase22ExecutionConsumptionReceipt:
    """Require the irreversible claim before fresh lane results are assembled."""

    if receipt is None:
        receipt = load_phase22_execution_consumption_receipt()
    if receipt is None:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly requires durable one-shot claim"
        )
    manifest = build_phase22_execution_manifest()
    if (
        not receipt.claim_committed
        or receipt.outcomes_emitted
        or receipt.candidate_id != CANDIDATE_ID
        or receipt.execution_manifest_sha256 != manifest.fingerprint()
    ):
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly durable claim state invalid"
        )
    return receipt


def _validate_native_payload(
    *,
    trader_id: str,
    payload: Mapping[str, object],
) -> Sequence[Mapping[str, object]]:
    if trader_id not in _NATIVE_SURFACE:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly native Trader drift"
        )
    if payload.get("candidate_id") != CANDIDATE_ID:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly native candidate drift"
        )
    if payload.get("trader_id") != trader_id:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly native Trader identity drift"
        )
    for name, expected in (
        ("fresh_outcomes_executed", True),
        ("methodology_changed", False),
        ("legacy_trader_sizing_used_for_cibo", False),
        ("productive_authority", False),
    ):
        if payload.get(name) is not expected:
            raise CiboCapitalManagementError(
                f"Phase22 fresh assembly native governance drift: {name}"
            )
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list) or any(
        not isinstance(item, dict) for item in opportunities
    ):
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly native opportunities invalid"
        )
    return opportunities


def build_native_trader_evidence(
    *,
    trader_id: str,
    payload: Mapping[str, object],
    lane_artifact_sha256: str,
) -> Phase22FreshTraderEvidence:
    rows = _validate_native_payload(trader_id=trader_id, payload=payload)
    parity = _parity_receipt(trader_id)
    opportunities = []
    for raw in rows:
        row = dict(raw)
        symbol = str(row.get("symbol", ""))
        if trader_id == "VT31_NAS100" and symbol != "NAS100":
            raise CiboCapitalManagementError(
                "Phase22 VT31 fresh assembly symbol drift"
            )
        if not symbol:
            raise CiboCapitalManagementError(
                "Phase22 native fresh assembly symbol missing"
            )
        if str(row.get("methodology_sha256", "")) != parity.parameter_sha256:
            raise CiboCapitalManagementError(
                "Phase22 native fresh assembly methodology drift"
            )
        opportunities.append(
            native_fresh_opportunity(
                trader_id=trader_id,
                qore_symbol=symbol,
                row=row,
                source_evidence_ids=frozen_source_evidence_ids(
                    trader_id=trader_id,
                    qore_symbol=symbol,
                ),
            )
        )
    return Phase22FreshTraderEvidence(
        trader_id=trader_id,
        source_artifact_sha256=_require_sha256(
            lane_artifact_sha256,
            "lane_artifact_sha256",
        ),
        opportunities=tuple(opportunities),
        fresh_outcomes_executed=True,
        methodology_changed=False,
        legacy_trader_sizing_used_for_cibo=False,
        productive_authority=False,
    )


def build_turtle_trader_evidence(
    *,
    trader_id: str,
    rows: Sequence[Mapping[str, object]],
    lane_artifact_sha256: str,
) -> Phase22FreshTraderEvidence:
    surface = dict(_TURTLE_SURFACE)
    symbol = surface.get(trader_id)
    if symbol is None:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly Turtle Trader drift"
        )
    if any(not isinstance(item, dict) for item in rows):
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly Turtle rows invalid"
        )
    parity = _parity_receipt(trader_id)
    source_ids = frozen_source_evidence_ids(
        trader_id=trader_id,
        qore_symbol=symbol,
    )
    opportunities = tuple(
        turtle_geometry_opportunity(
            trader_id=trader_id,
            qore_symbol=symbol,
            row=dict(item),
            methodology_sha256=parity.parameter_sha256,
            source_evidence_ids=source_ids,
        )
        for item in rows
    )
    return Phase22FreshTraderEvidence(
        trader_id=trader_id,
        source_artifact_sha256=_require_sha256(
            lane_artifact_sha256,
            "lane_artifact_sha256",
        ),
        opportunities=opportunities,
        fresh_outcomes_executed=True,
        methodology_changed=False,
        legacy_trader_sizing_used_for_cibo=False,
        productive_authority=False,
    )


def assemble_phase22_fresh_batch(
    *,
    vt08_payload: Mapping[str, object],
    turtle_rows: Mapping[str, Sequence[Mapping[str, object]]],
    vt31_payload: Mapping[str, object],
    lane_artifact_sha256s: Mapping[str, str],
    consumption_receipt: Phase22ExecutionConsumptionReceipt | None = None,
) -> Phase22FreshOpportunityBatch:
    """Build exact 7/7 chronological batch; never infer missing lanes."""

    assert_durable_phase22_claim(consumption_receipt)
    expected_keys = set(CANONICAL_PHASE22_TRADER_IDS)
    if set(lane_artifact_sha256s) != expected_keys:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly lane artifact surface drift"
        )
    if set(turtle_rows) != {item[0] for item in _TURTLE_SURFACE}:
        raise CiboCapitalManagementError(
            "Phase22 fresh assembly Turtle surface drift"
        )

    by_id: dict[str, Phase22FreshTraderEvidence] = {
        "VT08_FOREX": build_native_trader_evidence(
            trader_id="VT08_FOREX",
            payload=vt08_payload,
            lane_artifact_sha256=lane_artifact_sha256s["VT08_FOREX"],
        ),
        "VT31_NAS100": build_native_trader_evidence(
            trader_id="VT31_NAS100",
            payload=vt31_payload,
            lane_artifact_sha256=lane_artifact_sha256s["VT31_NAS100"],
        ),
    }
    for trader_id, _symbol in _TURTLE_SURFACE:
        by_id[trader_id] = build_turtle_trader_evidence(
            trader_id=trader_id,
            rows=turtle_rows[trader_id],
            lane_artifact_sha256=lane_artifact_sha256s[trader_id],
        )
    traders = tuple(by_id[item] for item in CANONICAL_PHASE22_TRADER_IDS)
    return build_phase22_fresh_opportunity_batch(traders)
