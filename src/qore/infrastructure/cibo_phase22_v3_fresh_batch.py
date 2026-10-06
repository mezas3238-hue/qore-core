"""Canonical exact-7/7 fresh opportunity batch for Phase22 V3."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
)
from qore.infrastructure.cibo_phase22_next_exam_governance import NEXT_CANDIDATE_ID
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


@dataclass(frozen=True, slots=True)
class Phase22V3FreshOpportunityBatch:
    candidate_id: str
    traders: tuple[Phase22FreshTraderEvidence, ...]
    opportunities: tuple[Phase22FreshOpportunity, ...]
    legacy_trader_sizing_used_for_cibo: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != NEXT_CANDIDATE_ID:
            raise CiboCapitalManagementError("V3 batch candidate drift")
        ids = tuple(item.trader_id for item in self.traders)
        if ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError("V3 batch requires exact 7/7 Traders")
        flattened = tuple(
            opportunity
            for trader in self.traders
            for opportunity in trader.opportunities
        )
        expected = tuple(
            sorted(
                flattened,
                key=lambda item: (
                    item.signal_at,
                    item.trader_id.value,
                    item.signal_fingerprint,
                ),
            )
        )
        if self.opportunities != expected:
            raise CiboCapitalManagementError("V3 batch chronology drift")
        fingerprints = tuple(item.signal_fingerprint for item in self.opportunities)
        if len(fingerprints) != len(set(fingerprints)):
            raise CiboCapitalManagementError("V3 batch duplicate signal")
        if self.legacy_trader_sizing_used_for_cibo or self.productive_authority:
            raise CiboCapitalManagementError("V3 batch governance contamination")

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.cibo.phase22.v3-fresh-opportunity-batch.v1",
            "candidate_id": self.candidate_id,
            "trader_evidence_sha256s": [
                [item.trader_id, item.fingerprint()] for item in self.traders
            ],
            "opportunity_fingerprints": [
                item.fingerprint() for item in self.opportunities
            ],
            "legacy_trader_sizing_used_for_cibo": False,
            "productive_authority": False,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_phase22_v3_fresh_batch(
    traders: tuple[Phase22FreshTraderEvidence, ...],
) -> Phase22V3FreshOpportunityBatch:
    opportunities = tuple(
        sorted(
            (
                opportunity
                for trader in traders
                for opportunity in trader.opportunities
            ),
            key=lambda item: (
                item.signal_at,
                item.trader_id.value,
                item.signal_fingerprint,
            ),
        )
    )
    return Phase22V3FreshOpportunityBatch(
        candidate_id=NEXT_CANDIDATE_ID,
        traders=traders,
        opportunities=opportunities,
    )
