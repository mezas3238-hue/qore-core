"""Frozen evidence bindings for Phase22 V4 fresh Trader lanes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshTraderEvidence,
    native_fresh_opportunity,
    turtle_geometry_opportunity,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    ACTIVE_PHASE22_TRADER_PARITY_MANIFEST,
    Phase22TraderParityReceipt,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    Phase22V4SourceBinding,
    load_phase22_v4_source_receipt,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_RECEIPT_PATH = Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")
TURTLE_SURFACE = (
    ("R34_XAUUSD", "XAUUSD"),
    ("R38_EURUSD", "EURUSD"),
    ("R43_GBPUSD", "GBPUSD"),
    ("R38_GBPJPY", "GBPJPY"),
    ("R42_AUDJPY", "AUDJPY"),
)


def _sha(value: str) -> str:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError("V4 lane artifact SHA invalid")
    return value


def _source_receipt():
    return load_phase22_v4_source_receipt(_SOURCE_RECEIPT_PATH)


def parity_receipt(trader_id: str) -> Phase22TraderParityReceipt:
    parity = ACTIVE_PHASE22_TRADER_PARITY_MANIFEST
    if parity is None:
        raise CiboCapitalManagementError("V4 parity manifest missing")
    matches = tuple(x for x in parity.receipts if x.trader_id == trader_id)
    if len(matches) != 1:
        raise CiboCapitalManagementError("V4 parity receipt missing")
    return matches[0]


def source_binding(symbol: str, timeframe: str) -> Phase22V4SourceBinding:
    receipt = _source_receipt()
    matches = tuple(
        x
        for x in receipt.bindings
        if x.symbol == symbol and x.timeframe == timeframe
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError("V4 source binding missing")
    return matches[0]


def _unique_source_binding_for_symbol(symbol: str) -> Phase22V4SourceBinding:
    matches = tuple(
        item
        for item in _source_receipt().bindings
        if item.symbol == symbol
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "V4 source binding missing or ambiguous for symbol"
        )
    return matches[0]


def source_evidence_ids(
    *,
    trader_id: str,
    symbol: str,
) -> tuple[str, ...]:
    parity = parity_receipt(trader_id)
    receipt = _source_receipt()
    source = _unique_source_binding_for_symbol(symbol)
    values = (
        receipt.fingerprint(),
        source.artifact_digest,
        f"git:{parity.methodology_git_sha}",
        parity.parity_artifact_digest,
    )
    if len(values) != len(set(values)):
        raise CiboCapitalManagementError("V4 source evidence duplicated")
    return values


def native_trader_evidence(
    *,
    trader_id: str,
    payload: Mapping[str, object],
    lane_artifact_sha256: str,
) -> Phase22FreshTraderEvidence:
    if (
        payload.get("candidate_id") != V4_CANDIDATE_ID
        or payload.get("trader_id") != trader_id
    ):
        raise CiboCapitalManagementError("V4 native identity drift")
    for name, expected in (
        ("fresh_outcomes_executed", True),
        ("methodology_changed", False),
        ("legacy_trader_sizing_used_for_cibo", False),
        ("productive_authority", False),
    ):
        if payload.get(name) is not expected:
            raise CiboCapitalManagementError(f"V4 native governance drift: {name}")
    if payload.get("broker_mutation_performed", False) is not False:
        raise CiboCapitalManagementError("V4 native broker mutation detected")
    rows = payload.get("opportunities")
    if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
        raise CiboCapitalManagementError("V4 native opportunities invalid")
    parity = parity_receipt(trader_id)
    opportunities = []
    for raw in rows:
        row = dict(raw)
        symbol = str(row.get("symbol", ""))
        if not symbol:
            raise CiboCapitalManagementError("V4 native symbol missing")
        if str(row.get("methodology_sha256", "")) != parity.parameter_sha256:
            raise CiboCapitalManagementError("V4 native methodology drift")
        opportunities.append(
            native_fresh_opportunity(
                trader_id=trader_id,
                qore_symbol=symbol,
                row=row,
                source_evidence_ids=source_evidence_ids(
                    trader_id=trader_id,
                    symbol=symbol,
                ),
            )
        )
    return Phase22FreshTraderEvidence(
        trader_id=trader_id,
        source_artifact_sha256=_sha(lane_artifact_sha256),
        opportunities=tuple(opportunities),
        fresh_outcomes_executed=True,
        methodology_changed=False,
        legacy_trader_sizing_used_for_cibo=False,
    )


def turtle_trader_evidence(
    *,
    trader_id: str,
    rows: Sequence[Mapping[str, object]],
    lane_artifact_sha256: str,
) -> Phase22FreshTraderEvidence:
    symbol = dict(TURTLE_SURFACE).get(trader_id)
    if symbol is None or any(not isinstance(x, dict) for x in rows):
        raise CiboCapitalManagementError("V4 Turtle surface drift")
    parity = parity_receipt(trader_id)
    ids = source_evidence_ids(trader_id=trader_id, symbol=symbol)
    opportunities = tuple(
        turtle_geometry_opportunity(
            trader_id=trader_id,
            qore_symbol=symbol,
            row=dict(row),
            methodology_sha256=parity.parameter_sha256,
            source_evidence_ids=ids,
        )
        for row in rows
    )
    return Phase22FreshTraderEvidence(
        trader_id=trader_id,
        source_artifact_sha256=_sha(lane_artifact_sha256),
        opportunities=opportunities,
        fresh_outcomes_executed=True,
        methodology_changed=False,
        legacy_trader_sizing_used_for_cibo=False,
    )
