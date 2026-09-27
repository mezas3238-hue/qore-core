"""Phase20D terminal outcome reconciliation for CIBO forward qualification.

A forward outcome is only produced from a terminal reconciled settlement plus
explicit evidence of the initial stop-risk actually carried by the executed
position. Requested/minimum seed risk is never silently substituted for
executed risk.

Research-only. No sizing, Risk, execution or broker mutation authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardEvidenceKind,
    Phase20ForwardOutcomeEvidence,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementState,
)


@dataclass(frozen=True, slots=True)
class Phase20ExecutedRiskEvidence:
    """Reconciled and independently auditable risk denominator."""

    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    qore_symbol: str
    provider_order_ref: str
    side: str
    position_id: int
    authorized_source_volume: Decimal
    filled_source_volume: Decimal
    weighted_fill_price: Decimal
    intended_entry_price: Decimal
    structural_stop_price: Decimal
    stop_risk_per_volume_at_intended_entry_usd: Decimal
    executed_initial_stop_risk_usd: Decimal
    observed_at: datetime
    fill_evidence_refs: tuple[str, ...]
    fill_reconciled: bool
    mutation_outcome_known: bool
    capital_deployed_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            not self.evidence_id
            or not self.signal_fingerprint
            or not self.qore_symbol
            or not self.provider_order_ref
        ):
            raise CiboCapitalManagementError(
                "Phase20D executed-risk evidence identity/signal/symbol required"
            )
        if (
            not isinstance(self.decision_evidence_sha256, str)
            or not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase20D executed-risk evidence requires decision SHA256"
            )
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase20D executed-risk position_id must be positive int"
            )
        for name in (
            "authorized_source_volume",
            "filled_source_volume",
            "weighted_fill_price",
            "intended_entry_price",
            "structural_stop_price",
            "stop_risk_per_volume_at_intended_entry_usd",
            "executed_initial_stop_risk_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20D executed-risk {name} must be finite positive Decimal"
                )
        if self.filled_source_volume > self.authorized_source_volume:
            raise CiboCapitalManagementError(
                "Phase20D filled source volume cannot exceed authorization"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "Phase20D executed-risk side must be long/short"
            )
        if (
            self.side == "long"
            and self.weighted_fill_price <= self.structural_stop_price
        ):
            raise CiboCapitalManagementError(
                "Phase20D long executed-risk fill must remain above stop"
            )
        if (
            self.side == "short"
            and self.weighted_fill_price >= self.structural_stop_price
        ):
            raise CiboCapitalManagementError(
                "Phase20D short executed-risk fill must remain below stop"
            )
        intended_distance = abs(
            self.intended_entry_price - self.structural_stop_price
        )
        executed_distance = abs(
            self.weighted_fill_price - self.structural_stop_price
        )
        if intended_distance <= 0 or executed_distance <= 0:
            raise CiboCapitalManagementError(
                "Phase20D executed-risk stop geometry is invalid"
            )
        reconstructed = (
            self.filled_source_volume
            * self.stop_risk_per_volume_at_intended_entry_usd
            * executed_distance
            / intended_distance
        )
        if reconstructed != self.executed_initial_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Phase20D executed-risk evidence is not arithmetically reproducible"
            )
        _aware(self.observed_at, name="executed-risk observed_at")
        if self.capital_deployed_at is not None:
            _aware(
                self.capital_deployed_at,
                name="executed-risk capital_deployed_at",
            )
            if self.capital_deployed_at > self.observed_at:
                raise CiboCapitalManagementError(
                    "Phase20D capital deployment cannot postdate risk reconciliation"
                )
        if not self.fill_evidence_refs or any(
            not isinstance(item, str) or not item
            for item in self.fill_evidence_refs
        ):
            raise CiboCapitalManagementError(
                "Phase20D executed-risk evidence requires fill references"
            )
        if len(self.fill_evidence_refs) != len(set(self.fill_evidence_refs)):
            raise CiboCapitalManagementError(
                "Phase20D executed-risk fill references must be unique"
            )
        if type(self.fill_reconciled) is not bool:
            raise CiboCapitalManagementError(
                "Phase20D fill_reconciled must be bool"
            )
        if type(self.mutation_outcome_known) is not bool:
            raise CiboCapitalManagementError(
                "Phase20D mutation_outcome_known must be bool"
            )
        if not self.fill_reconciled or not self.mutation_outcome_known:
            raise CiboCapitalManagementError(
                "Phase20D executed-risk evidence must be fully reconciled"
            )


def reconcile_phase20_forward_outcome_from_seal(
    *,
    decision: Phase20ForwardDecisionSeal,
    settlement: CmaSettlementState,
    executed_risk: Phase20ExecutedRiskEvidence,
    reconciled_at: datetime,
    capital_released_at: datetime | None = None,
) -> Phase20ForwardOutcomeEvidence:
    """Reconcile terminal outcome from durable decision evidence after restart."""

    if not isinstance(decision, Phase20ForwardDecisionSeal):
        raise CiboCapitalManagementError(
            "Phase20D durable outcome requires canonical decision seal"
        )
    if not isinstance(settlement, CmaSettlementState):
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation requires settlement state"
        )
    if not isinstance(executed_risk, Phase20ExecutedRiskEvidence):
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation requires executed-risk evidence"
        )
    _aware(reconciled_at, name="outcome reconciled_at")
    if executed_risk.decision_evidence_sha256 != decision.evidence_sha256:
        raise CiboCapitalManagementError(
            "Phase20D executed-risk decision digest mismatch"
        )
    if executed_risk.signal_fingerprint not in decision.signal_fingerprints:
        raise CiboCapitalManagementError(
            "Phase20D executed-risk signal was not sealed pre-decision"
        )
    return _reconcile_bound_outcome(
        decision_sha=decision.evidence_sha256,
        decision_at=decision.decision_at,
        sealed_signals=set(decision.signal_fingerprints),
        settlement=settlement,
        executed_risk=executed_risk,
        reconciled_at=reconciled_at,
        capital_released_at=capital_released_at,
    )


def reconcile_phase20_forward_outcome(
    *,
    decision: Phase20ForwardDecisionEvidence,
    settlement: CmaSettlementState,
    executed_risk: Phase20ExecutedRiskEvidence,
    reconciled_at: datetime,
    capital_released_at: datetime | None = None,
) -> Phase20ForwardOutcomeEvidence:
    """Create terminal structural R only from reconciled execution economics."""

    if not isinstance(decision, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation requires canonical decision"
        )
    if decision.evidence_kind is not Phase20ForwardEvidenceKind.FORWARD_OBSERVED:
        raise CiboCapitalManagementError(
            "Phase20D terminal outcome requires FORWARD_OBSERVED decision"
        )
    if not isinstance(settlement, CmaSettlementState):
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation requires settlement state"
        )
    if not isinstance(executed_risk, Phase20ExecutedRiskEvidence):
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation requires executed-risk evidence"
        )
    _aware(reconciled_at, name="outcome reconciled_at")

    decision_sha = phase20_forward_evidence_sha256(decision)
    sealed_signals = {
        item.candidate.signal_fingerprint
        for item in decision.candidates
    }
    return _reconcile_bound_outcome(
        decision_sha=decision_sha,
        decision_at=decision.decision_at,
        sealed_signals=sealed_signals,
        settlement=settlement,
        executed_risk=executed_risk,
        reconciled_at=reconciled_at,
        capital_released_at=capital_released_at,
    )


def _reconcile_bound_outcome(
    *,
    decision_sha: str,
    decision_at: datetime,
    sealed_signals: set[str],
    settlement: CmaSettlementState,
    executed_risk: Phase20ExecutedRiskEvidence,
    reconciled_at: datetime,
    capital_released_at: datetime | None = None,
) -> Phase20ForwardOutcomeEvidence:
    if executed_risk.decision_evidence_sha256 != decision_sha:
        raise CiboCapitalManagementError(
            "Phase20D executed-risk decision digest mismatch"
        )
    if executed_risk.signal_fingerprint not in sealed_signals:
        raise CiboCapitalManagementError(
            "Phase20D executed-risk signal was not sealed pre-decision"
        )
    if settlement.signal_fingerprint != executed_risk.signal_fingerprint:
        raise CiboCapitalManagementError(
            "Phase20D settlement/executed-risk signal mismatch"
        )
    if settlement.position_id != executed_risk.position_id:
        raise CiboCapitalManagementError(
            "Phase20D settlement/executed-risk position mismatch"
        )
    if not settlement.position_closed:
        raise CiboCapitalManagementError(
            "Phase20D outcome requires terminal closed settlement"
        )
    if not settlement.records:
        raise CiboCapitalManagementError(
            "Phase20D terminal settlement cannot be empty"
        )
    if settlement.records[-1].event != "CTRADER_DEMO_EXIT_SETTLEMENT":
        raise CiboCapitalManagementError(
            "Phase20D terminal settlement requires exit record"
        )
    if executed_risk.observed_at <= decision_at:
        raise CiboCapitalManagementError(
            "Phase20D executed-risk evidence must follow decision"
        )
    if (
        executed_risk.capital_deployed_at is not None
        and executed_risk.capital_deployed_at <= decision_at
    ):
        raise CiboCapitalManagementError(
            "Phase20D full-fill deployment must follow decision"
        )
    if reconciled_at <= executed_risk.observed_at:
        raise CiboCapitalManagementError(
            "Phase20D outcome reconciliation must follow risk evidence"
        )

    capital_deployed_at: datetime | None = None
    capital_minutes: Decimal | None = None
    if capital_released_at is not None:
        _aware(capital_released_at, name="capital_released_at")
        if executed_risk.capital_deployed_at is None:
            raise CiboCapitalManagementError(
                "Phase20D exact capital deployment timestamp is unavailable"
            )
        if capital_released_at <= executed_risk.capital_deployed_at:
            raise CiboCapitalManagementError(
                "Phase20D capital release must follow full-fill deployment"
            )
        capital_deployed_at = executed_risk.capital_deployed_at
        capital_minutes = Decimal(
            str(
                (
                    capital_released_at
                    - executed_risk.capital_deployed_at
                ).total_seconds()
            )
        ) / Decimal("60")

    structural_r = (
        settlement.realized_net_pnl_usd
        / executed_risk.executed_initial_stop_risk_usd
    )
    payload = {
        "decision_evidence_sha256": decision_sha,
        "signal_fingerprint": executed_risk.signal_fingerprint,
        "position_id": executed_risk.position_id,
        "executed_risk_evidence_id": executed_risk.evidence_id,
        "fill_evidence_refs": list(executed_risk.fill_evidence_refs),
        "settlement_deal_ids": [
            item.deal_id for item in settlement.records
        ],
        "realized_net_pnl_usd": format(
            settlement.realized_net_pnl_usd,
            "f",
        ),
        "executed_initial_stop_risk_usd": format(
            executed_risk.executed_initial_stop_risk_usd,
            "f",
        ),
        "capital_deployed_at": (
            None
            if capital_deployed_at is None
            else capital_deployed_at.isoformat()
        ),
        "capital_released_at": (
            None
            if capital_released_at is None
            else capital_released_at.isoformat()
        ),
        "capital_minutes": (
            None
            if capital_minutes is None
            else format(capital_minutes, "f")
        ),
        "reconciled_at": reconciled_at.isoformat(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return Phase20ForwardOutcomeEvidence(
        evidence_id=f"phase20d-outcome:{sha256(raw).hexdigest()}",
        decision_evidence_sha256=decision_sha,
        signal_fingerprint=executed_risk.signal_fingerprint,
        position_id=executed_risk.position_id,
        execution_risk_evidence_id=executed_risk.evidence_id,
        settlement_deal_ids=tuple(
            item.deal_id for item in settlement.records
        ),
        fill_evidence_refs=executed_risk.fill_evidence_refs,
        observed_at=reconciled_at,
        realized_net_pnl_usd=settlement.realized_net_pnl_usd,
        executed_initial_stop_risk_usd=(
            executed_risk.executed_initial_stop_risk_usd
        ),
        realized_structural_outcome_r=structural_r,
        outcome_reconciled=True,
        capital_deployed_at=capital_deployed_at,
        capital_released_at=capital_released_at,
        capital_minutes=capital_minutes,
    )


def append_reconciled_phase20_forward_outcome_from_seal(
    *,
    store: DurablePhase20ForwardEvidenceStore,
    decision: Phase20ForwardDecisionSeal,
    settlement: CmaSettlementState,
    executed_risk: Phase20ExecutedRiskEvidence,
    reconciled_at: datetime,
    capital_released_at: datetime | None = None,
) -> VersionedPhase20ForwardEvidenceBook:
    """Append terminal outcome using only restart-safe durable decision evidence."""

    if not isinstance(store, DurablePhase20ForwardEvidenceStore):
        raise CiboCapitalManagementError(
            "Phase20D outcome store must be canonical durable store"
        )
    outcome = reconcile_phase20_forward_outcome_from_seal(
        decision=decision,
        settlement=settlement,
        executed_risk=executed_risk,
        reconciled_at=reconciled_at,
        capital_released_at=capital_released_at,
    )
    current = store.load()
    return store.append_outcome(
        outcome,
        expected_generation=current.generation,
    )


def append_reconciled_phase20_forward_outcome(
    *,
    store: DurablePhase20ForwardEvidenceStore,
    decision: Phase20ForwardDecisionEvidence,
    settlement: CmaSettlementState,
    executed_risk: Phase20ExecutedRiskEvidence,
    reconciled_at: datetime,
    capital_released_at: datetime | None = None,
) -> VersionedPhase20ForwardEvidenceBook:
    """Reconcile and append exactly one terminal outcome with generation CAS."""

    if not isinstance(store, DurablePhase20ForwardEvidenceStore):
        raise CiboCapitalManagementError(
            "Phase20D outcome store must be canonical durable store"
        )
    outcome = reconcile_phase20_forward_outcome(
        decision=decision,
        settlement=settlement,
        executed_risk=executed_risk,
        reconciled_at=reconciled_at,
        capital_released_at=capital_released_at,
    )
    current = store.load()
    return store.append_outcome(
        outcome,
        expected_generation=current.generation,
    )


def _aware(value: datetime, *, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"Phase20D {name} must be timezone-aware"
        )
