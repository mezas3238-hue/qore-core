"""A2 Phase22 historical Compound adapter for capital-science closure.

The active Phase22 V2 examination is a historical replay. Historical outcomes
must not be forced through the live CompoundCapitalLot identity because that
identity intentionally requires positive broker position/deal identifiers.

This adapter creates research-only Compound lineage directly from canonical
Phase22 historical replay outcomes. It never invents broker identifiers and
never grants runtime, LIVE, real-capital, integration, or certification
authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)

ADAPTER_ID = "CIBO_PHASE22_HISTORICAL_COMPOUND_LINEAGE_ADAPTER_V1"
A1_CONSUMER_CONTRACT_ID = (
    "CIBO_A1_PHASE22_HISTORICAL_COMPOUND_LINEAGE_DEPENDENCY_V1"
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"A2 historical Compound {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCompoundCapitalError(
            f"A2 historical Compound {name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalCompoundLot:
    lot_id: str
    source_outcome_evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    trader_id: str
    amount_usd: Decimal
    realized_at: datetime
    generation: int = 1
    broker_position_id: None = None
    broker_deal_ids: tuple[()] = ()
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not self.lot_id.startswith("phase22-historical-compound:"):
            raise CiboCompoundCapitalError(
                "A2 historical Compound lot identity drift"
            )
        if not self.source_outcome_evidence_id.startswith(
            "phase22-replay-outcome:"
        ):
            raise CiboCompoundCapitalError(
                "A2 historical Compound source outcome identity drift"
            )
        _sha(self.decision_evidence_sha256, "decision_evidence_sha256")
        if not self.signal_fingerprint or not self.trader_id:
            raise CiboCompoundCapitalError(
                "A2 historical Compound signal/trader identity required"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "A2 historical Compound lot requires positive realized profit"
            )
        _aware(self.realized_at, "realized_at")
        if self.generation != 1:
            raise CiboCompoundCapitalError(
                "A2 historical replay source lots must start at generation 1"
            )
        if self.broker_position_id is not None or self.broker_deal_ids:
            raise CiboCompoundCapitalError(
                "A2 historical Compound cannot emit historical broker ids"
            )
        if self.runtime_authority:
            raise CiboCompoundCapitalError(
                "A2 historical Compound lot grants no runtime authority"
            )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalCompoundLedger:
    adapter_identity: str
    source_population_sha256: str
    a1_manifest_sha256: str
    amendment_sha256: str
    lots: tuple[Phase22HistoricalCompoundLot, ...]
    total_realized_profit_usd: Decimal
    realized_profit_only: bool
    floating_pnl_used_as_capital: bool
    capital_conservation_proven: bool
    double_spend_detected: bool
    decision_before_outcome_preserved: bool
    deterministic_replay: bool
    historical_broker_ids_emitted: bool
    fabricated_execution_ids_used: bool
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.adapter_identity != ADAPTER_ID:
            raise CiboCompoundCapitalError(
                "A2 historical Compound adapter identity drift"
            )
        for name in (
            "source_population_sha256",
            "a1_manifest_sha256",
            "amendment_sha256",
        ):
            _sha(getattr(self, name), name)
        if not self.lots:
            raise CiboCompoundCapitalError(
                "A2 historical Compound requires positive realized-profit lineage"
            )
        origins = tuple(item.source_outcome_evidence_id for item in self.lots)
        if len(origins) != len(set(origins)):
            raise CiboCompoundCapitalError(
                "A2 historical Compound detected duplicate outcome spend"
            )
        expected_total = sum(
            (item.amount_usd for item in self.lots),
            Decimal(0),
        )
        if self.total_realized_profit_usd != expected_total:
            raise CiboCompoundCapitalError(
                "A2 historical Compound capital conservation drift"
            )
        required_true = (
            self.realized_profit_only,
            self.capital_conservation_proven,
            self.decision_before_outcome_preserved,
            self.deterministic_replay,
        )
        if not all(required_true):
            raise CiboCompoundCapitalError(
                "A2 historical Compound scientific invariants incomplete"
            )
        prohibited = (
            self.floating_pnl_used_as_capital,
            self.double_spend_detected,
            self.historical_broker_ids_emitted,
            self.fabricated_execution_ids_used,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
        )
        if any(prohibited):
            raise CiboCompoundCapitalError(
                "A2 historical Compound replay/governance violation"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["total_realized_profit_usd"] = format(
            self.total_realized_profit_usd,
            "f",
        )
        for lot in payload["lots"]:
            lot["amount_usd"] = format(lot["amount_usd"], "f")
            lot["realized_at"] = lot["realized_at"].isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class A2HistoricalCompoundLineageReceipt:
    contract_id: str
    source_workstream: str
    source_head: str
    artifact_sha256: str
    source_population_sha256: str
    a1_manifest_sha256: str
    adapter_identity: str
    historical_replay_supported: bool
    historical_broker_ids_required: bool
    historical_broker_ids_emitted: bool
    current_demo_ids_relabelled_as_historical: bool
    fabricated_execution_ids_used: bool
    realized_profit_only: bool
    floating_pnl_used_as_capital: bool
    capital_conservation_proven: bool
    double_spend_detected: bool
    decision_before_outcome_preserved: bool
    deterministic_replay: bool
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    a1_closes_source_workstream: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != A1_CONSUMER_CONTRACT_ID:
            raise CiboCompoundCapitalError(
                "A2 historical Compound consumer contract drift"
            )
        if self.source_workstream != "COMPOUND_ENGINE":
            raise CiboCompoundCapitalError(
                "A2 historical Compound receipt source drift"
            )
        if _SHA1_RE.fullmatch(self.source_head) is None:
            raise CiboCompoundCapitalError(
                "A2 historical Compound source HEAD invalid"
            )
        for name in (
            "artifact_sha256",
            "source_population_sha256",
            "a1_manifest_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.adapter_identity != ADAPTER_ID:
            raise CiboCompoundCapitalError(
                "A2 historical Compound receipt adapter drift"
            )
        required_true = (
            self.historical_replay_supported,
            self.realized_profit_only,
            self.capital_conservation_proven,
            self.decision_before_outcome_preserved,
            self.deterministic_replay,
        )
        prohibited = (
            self.historical_broker_ids_required,
            self.historical_broker_ids_emitted,
            self.current_demo_ids_relabelled_as_historical,
            self.fabricated_execution_ids_used,
            self.floating_pnl_used_as_capital,
            self.double_spend_detected,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
            self.a1_closes_source_workstream,
        )
        if not all(required_true) or any(prohibited):
            raise CiboCompoundCapitalError(
                "A2 historical Compound receipt is not scientifically admissible"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_phase22_historical_compound_ledger(
    *,
    evidence_book: VersionedPhase22HistoricalReplayEvidenceBook,
    source_population_sha256: str,
    a1_manifest_sha256: str,
) -> Phase22HistoricalCompoundLedger:
    """Create deterministic Compound source lots from positive realized replay PnL."""

    if not isinstance(
        evidence_book,
        VersionedPhase22HistoricalReplayEvidenceBook,
    ):
        raise CiboCompoundCapitalError(
            "A2 historical Compound requires canonical Phase22 replay book"
        )
    _sha(source_population_sha256, "source_population_sha256")
    _sha(a1_manifest_sha256, "a1_manifest_sha256")

    decision_by_sha = {
        item.evidence_sha256: item for item in evidence_book.decisions
    }
    lots: list[Phase22HistoricalCompoundLot] = []
    for outcome in sorted(
        evidence_book.outcomes,
        key=lambda item: (item.observed_at, item.evidence_id),
    ):
        if (
            not outcome.counterfactual_historical_replay
            or outcome.historical_broker_fills_claimed
            or outcome.fabricated_execution_evidence_used
        ):
            raise CiboCompoundCapitalError(
                "A2 historical Compound source outcome violates replay law"
            )
        decision = decision_by_sha.get(outcome.decision_evidence_sha256)
        if decision is None or decision.decision_at >= outcome.observed_at:
            raise CiboCompoundCapitalError(
                "A2 historical Compound decision/outcome chronology drift"
            )
        if outcome.realized_net_pnl_usd <= 0:
            continue
        material = "|".join(
            (
                ADAPTER_ID,
                outcome.evidence_id,
                outcome.decision_evidence_sha256,
                outcome.signal_fingerprint,
                format(outcome.realized_net_pnl_usd, "f"),
            )
        )
        lot_id = (
            "phase22-historical-compound:"
            + hashlib.sha256(material.encode("utf-8")).hexdigest()
        )
        lots.append(
            Phase22HistoricalCompoundLot(
                lot_id=lot_id,
                source_outcome_evidence_id=outcome.evidence_id,
                decision_evidence_sha256=outcome.decision_evidence_sha256,
                signal_fingerprint=outcome.signal_fingerprint,
                trader_id=outcome.trader_id,
                amount_usd=outcome.realized_net_pnl_usd,
                realized_at=outcome.observed_at,
            )
        )

    total = sum((item.amount_usd for item in lots), Decimal(0))
    return Phase22HistoricalCompoundLedger(
        adapter_identity=ADAPTER_ID,
        source_population_sha256=source_population_sha256,
        a1_manifest_sha256=a1_manifest_sha256,
        amendment_sha256=evidence_book.amendment_sha256,
        lots=tuple(lots),
        total_realized_profit_usd=total,
        realized_profit_only=True,
        floating_pnl_used_as_capital=False,
        capital_conservation_proven=True,
        double_spend_detected=False,
        decision_before_outcome_preserved=True,
        deterministic_replay=True,
        historical_broker_ids_emitted=False,
        fabricated_execution_ids_used=False,
    )


def build_a1_historical_compound_lineage_receipt(
    *,
    ledger: Phase22HistoricalCompoundLedger,
    source_head: str,
    artifact_sha256: str,
) -> A2HistoricalCompoundLineageReceipt:
    """Emit the exact JSON-compatible receipt required by the A1 consumer."""

    if not isinstance(ledger, Phase22HistoricalCompoundLedger):
        raise CiboCompoundCapitalError(
            "A2 historical Compound receipt requires canonical adapter ledger"
        )
    _sha(artifact_sha256, "artifact_sha256")
    return A2HistoricalCompoundLineageReceipt(
        contract_id=A1_CONSUMER_CONTRACT_ID,
        source_workstream="COMPOUND_ENGINE",
        source_head=source_head,
        artifact_sha256=artifact_sha256,
        source_population_sha256=ledger.source_population_sha256,
        a1_manifest_sha256=ledger.a1_manifest_sha256,
        adapter_identity=ledger.adapter_identity,
        historical_replay_supported=True,
        historical_broker_ids_required=False,
        historical_broker_ids_emitted=ledger.historical_broker_ids_emitted,
        current_demo_ids_relabelled_as_historical=False,
        fabricated_execution_ids_used=ledger.fabricated_execution_ids_used,
        realized_profit_only=ledger.realized_profit_only,
        floating_pnl_used_as_capital=ledger.floating_pnl_used_as_capital,
        capital_conservation_proven=ledger.capital_conservation_proven,
        double_spend_detected=ledger.double_spend_detected,
        decision_before_outcome_preserved=ledger.decision_before_outcome_preserved,
        deterministic_replay=ledger.deterministic_replay,
    )
