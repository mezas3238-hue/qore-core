"""Canonical seven-Trader fresh-opportunity surface for Phase22 V2.

Trader replay emits structural opportunities and structural outcomes only.
Legacy Trader risk_scale / scaled PnL never enters this surface: CIBO owns
capital and sizing downstream.

The batch is chronological, exact-7/7, volume-free and deterministic.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    reconstructed_signal_fingerprint,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase22 fresh opportunity {name} must be timezone-aware"
        )


def _decimal(value: object, name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"Phase22 fresh opportunity {name} invalid"
        ) from error
    if not parsed.is_finite():
        raise CiboCapitalManagementError(
            f"Phase22 fresh opportunity {name} must be finite"
        )
    return parsed


@dataclass(frozen=True, slots=True)
class Phase22FreshOpportunity:
    trader_id: TraderLineage
    qore_symbol: str
    signal_fingerprint: str
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    side: str
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    exit_reason: str
    gross_structural_outcome_r: Decimal
    methodology_sha256: str
    source_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.trader_id, TraderLineage):
            raise CiboCapitalManagementError(
                "Phase22 fresh opportunity Trader lineage invalid"
            )
        if not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase22 fresh opportunity symbol required"
            )
        if _SHA256_RE.fullmatch(self.signal_fingerprint) is None:
            raise CiboCapitalManagementError(
                "Phase22 fresh opportunity signal fingerprint invalid"
            )
        if _SHA256_RE.fullmatch(self.methodology_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 fresh opportunity methodology digest invalid"
            )
        for name, value in (
            ("signal_at", self.signal_at),
            ("entry_at", self.entry_at),
            ("exit_at", self.exit_at),
        ):
            _aware(value, name)
        if self.entry_at < self.signal_at or self.exit_at <= self.entry_at:
            raise CiboCapitalManagementError(
                "Phase22 fresh opportunity chronology invalid"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "Phase22 fresh opportunity side invalid"
            )
        for name, value in (
            ("entry_price", self.entry_price),
            ("structural_stop", self.structural_stop),
            ("technical_target", self.technical_target),
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise CiboCapitalManagementError(
                    f"Phase22 fresh opportunity {name} invalid"
                )
        if self.side == "long":
            if not self.structural_stop < self.entry_price < self.technical_target:
                raise CiboCapitalManagementError(
                    "Phase22 fresh long geometry invalid"
                )
        else:
            if not self.technical_target < self.entry_price < self.structural_stop:
                raise CiboCapitalManagementError(
                    "Phase22 fresh short geometry invalid"
                )
        if (
            not isinstance(self.gross_structural_outcome_r, Decimal)
            or not self.gross_structural_outcome_r.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Phase22 fresh structural outcome R invalid"
            )
        if not self.exit_reason:
            raise CiboCapitalManagementError(
                "Phase22 fresh exit reason required"
            )
        if not self.source_evidence_ids or any(
            not item for item in self.source_evidence_ids
        ):
            raise CiboCapitalManagementError(
                "Phase22 fresh source evidence is required"
            )
        if len(self.source_evidence_ids) != len(set(self.source_evidence_ids)):
            raise CiboCapitalManagementError(
                "Phase22 fresh source evidence cannot duplicate"
            )

    def payload(self) -> dict[str, object]:
        return {
            "trader_id": self.trader_id.value,
            "qore_symbol": self.qore_symbol,
            "signal_fingerprint": self.signal_fingerprint,
            "signal_at": self.signal_at.isoformat(),
            "entry_at": self.entry_at.isoformat(),
            "exit_at": self.exit_at.isoformat(),
            "side": self.side,
            "entry_price": format(self.entry_price, "f"),
            "structural_stop": format(self.structural_stop, "f"),
            "technical_target": format(self.technical_target, "f"),
            "exit_reason": self.exit_reason,
            "gross_structural_outcome_r": format(
                self.gross_structural_outcome_r,
                "f",
            ),
            "methodology_sha256": self.methodology_sha256,
            "source_evidence_ids": list(self.source_evidence_ids),
            "volume": None,
            "legacy_trader_sizing_used_for_cibo": False,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def turtle_geometry_opportunity(
    *,
    trader_id: str,
    qore_symbol: str,
    row: dict[str, object],
    methodology_sha256: str,
    source_evidence_ids: tuple[str, ...],
) -> Phase22FreshOpportunity:
    """Normalize Turtle geometry using raw structural R, never legacy scaling."""

    lineage = TraderLineage(trader_id)
    signal_at = datetime.fromisoformat(str(row["signal_at"]))
    entry_at = datetime.fromisoformat(str(row["entry_at"]))
    exit_at = datetime.fromisoformat(str(row["exit_at"]))
    entry = _decimal(row["entry_price"], "entry_price")
    stop = _decimal(row["structural_stop"], "structural_stop")
    target = _decimal(row["technical_target"], "technical_target")
    side = str(row["side"]).lower()
    signal_fingerprint = reconstructed_signal_fingerprint(
        trader_id=lineage,
        qore_symbol=qore_symbol,
        side=side,
        signal_at=signal_at,
        entry_at=entry_at,
        entry_price=entry,
        structural_stop=stop,
        technical_target=target,
        source_evidence_ids=source_evidence_ids,
    )
    if "raw_net_010_r" not in row:
        raise CiboCapitalManagementError(
            "Phase22 Turtle fresh row missing raw structural R"
        )
    return Phase22FreshOpportunity(
        trader_id=lineage,
        qore_symbol=qore_symbol,
        signal_fingerprint=signal_fingerprint,
        signal_at=signal_at,
        entry_at=entry_at,
        exit_at=exit_at,
        side=side,
        entry_price=entry,
        structural_stop=stop,
        technical_target=target,
        exit_reason=str(row["exit_reason"]),
        gross_structural_outcome_r=_decimal(
            row["raw_net_010_r"],
            "raw_net_010_r",
        ),
        methodology_sha256=methodology_sha256,
        source_evidence_ids=source_evidence_ids,
    )


def native_fresh_opportunity(
    *,
    trader_id: str,
    qore_symbol: str,
    row: dict[str, object],
    source_evidence_ids: tuple[str, ...],
) -> Phase22FreshOpportunity:
    """Normalize VT08/VT31 native fresh opportunity payloads."""

    lineage = TraderLineage(trader_id)
    signal_at = datetime.fromisoformat(str(row["signal_at"]))
    entry_at = datetime.fromisoformat(str(row["entry_at"]))
    exit_at = datetime.fromisoformat(str(row["exit_at"]))
    methodology = str(row["methodology_sha256"])
    signal = str(row["signal_fingerprint"])
    return Phase22FreshOpportunity(
        trader_id=lineage,
        qore_symbol=qore_symbol,
        signal_fingerprint=signal,
        signal_at=signal_at,
        entry_at=entry_at,
        exit_at=exit_at,
        side=str(row["side"]).lower(),
        entry_price=_decimal(row["entry"], "entry_price"),
        structural_stop=_decimal(row["stop"], "structural_stop"),
        technical_target=_decimal(row["target"], "technical_target"),
        exit_reason=str(row["exit_reason"]),
        gross_structural_outcome_r=_decimal(
            row["realized_r"],
            "realized_r",
        ),
        methodology_sha256=methodology,
        source_evidence_ids=source_evidence_ids,
    )


@dataclass(frozen=True, slots=True)
class Phase22FreshTraderEvidence:
    trader_id: str
    source_artifact_sha256: str
    opportunities: tuple[Phase22FreshOpportunity, ...]
    fresh_outcomes_executed: bool
    methodology_changed: bool
    legacy_trader_sizing_used_for_cibo: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.trader_id not in CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 fresh Trader evidence identity drift"
            )
        if _SHA256_RE.fullmatch(self.source_artifact_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 fresh Trader source artifact digest invalid"
            )
        if any(item.trader_id.value != self.trader_id for item in self.opportunities):
            raise CiboCapitalManagementError(
                "Phase22 fresh Trader evidence contains foreign opportunity"
            )
        if not self.fresh_outcomes_executed:
            raise CiboCapitalManagementError(
                "Phase22 fresh Trader evidence must represent executed fresh outcomes"
            )
        if (
            self.methodology_changed
            or self.legacy_trader_sizing_used_for_cibo
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 fresh Trader evidence governance contamination"
            )

    def fingerprint(self) -> str:
        payload = {
            "trader_id": self.trader_id,
            "source_artifact_sha256": self.source_artifact_sha256,
            "opportunities": [item.payload() for item in self.opportunities],
            "fresh_outcomes_executed": True,
            "methodology_changed": False,
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


@dataclass(frozen=True, slots=True)
class Phase22FreshOpportunityBatch:
    candidate_id: str
    traders: tuple[Phase22FreshTraderEvidence, ...]
    opportunities: tuple[Phase22FreshOpportunity, ...]
    legacy_trader_sizing_used_for_cibo: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "Phase22 fresh batch candidate drift"
            )
        ids = tuple(item.trader_id for item in self.traders)
        if ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 fresh batch requires exact ordered 7/7 Traders"
            )
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
            raise CiboCapitalManagementError(
                "Phase22 fresh batch chronology drift"
            )
        fingerprints = tuple(
            item.signal_fingerprint for item in self.opportunities
        )
        if len(fingerprints) != len(set(fingerprints)):
            raise CiboCapitalManagementError(
                "Phase22 fresh batch duplicate signal fingerprint"
            )
        if self.legacy_trader_sizing_used_for_cibo or self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 fresh batch governance contamination"
            )

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.cibo.phase22.fresh-opportunity-batch.v1",
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


def build_phase22_fresh_opportunity_batch(
    traders: tuple[Phase22FreshTraderEvidence, ...],
) -> Phase22FreshOpportunityBatch:
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
    return Phase22FreshOpportunityBatch(
        candidate_id=CANDIDATE_ID,
        traders=traders,
        opportunities=opportunities,
    )
