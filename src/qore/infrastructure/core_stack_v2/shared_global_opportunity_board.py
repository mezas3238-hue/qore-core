"""STI-3 global opportunity attention board fed by frozen STI-2 cognition.

The board is a deterministic global attention map.  It never ranks orders,
creates Trader setups, allocates capital, authorizes Risk or executes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Iterable

from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityMechanism,
    SharedOpportunityTrajectoryAssessment,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)

_ATTENTION_MATURITIES = frozenset(
    {
        SharedOpportunityMaturity.EARLY,
        SharedOpportunityMaturity.DEVELOPING,
        SharedOpportunityMaturity.MATURE,
        SharedOpportunityMaturity.DETERIORATING,
    }
)


def _bps(value: int, *, name: str) -> None:
    if type(value) is not int or not 0 <= value <= 10_000:
        raise SharedTraderIntelligenceValidationError(
            f"{name} must be int within 0..10000"
        )


@dataclass(frozen=True, slots=True)
class SharedOpportunityBoardCandidate:
    candidate_id: str
    assessment: SharedOpportunityTrajectoryAssessment
    observed_at: datetime
    evidence_cutoff_at: datetime
    horizon: str
    data_health_bps: int
    relevant_traders: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.horizon.strip():
            raise SharedTraderIntelligenceValidationError(
                "opportunity board candidate identity/horizon must be non-empty"
            )
        for name in ("observed_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.observed_at:
            raise SharedTraderIntelligenceValidationError(
                "opportunity board candidate cannot use future evidence"
            )
        _bps(self.data_health_bps, name="data_health_bps")
        if self.relevant_traders != tuple(sorted(set(self.relevant_traders))):
            raise SharedTraderIntelligenceValidationError(
                "relevant_traders must be unique and canonical"
            )
        if not self.provenance_refs or self.provenance_refs != tuple(
            sorted(set(self.provenance_refs))
        ):
            raise SharedTraderIntelligenceValidationError(
                "provenance_refs must be non-empty, unique and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedOpportunityBoardEntry:
    candidate_id: str
    market: str
    horizon: str
    maturity: SharedOpportunityMaturity
    trajectory: SharedOpportunityMechanism | None
    trajectory_score_bps: int
    support_bps: int
    contradiction_bps: int
    uncertainty_bps: int
    data_health_bps: int
    relevant_traders: tuple[str, ...]
    observed_at: datetime
    evidence_cutoff_at: datetime
    provenance_refs: tuple[str, ...]
    attention_only: bool = True
    ranking_is_order_priority: bool = False
    creates_trader_setup: bool = False
    execution_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.market.strip() or not self.horizon.strip():
            raise SharedTraderIntelligenceValidationError(
                "opportunity board entry identity must be non-empty"
            )
        for name in (
            "trajectory_score_bps",
            "support_bps",
            "contradiction_bps",
            "uncertainty_bps",
            "data_health_bps",
        ):
            _bps(getattr(self, name), name=name)
        if self.relevant_traders != tuple(sorted(set(self.relevant_traders))):
            raise SharedTraderIntelligenceValidationError(
                "opportunity board relevant_traders must be canonical"
            )
        if self.evidence_cutoff_at > self.observed_at:
            raise SharedTraderIntelligenceValidationError(
                "opportunity board entry cannot use future evidence"
            )
        if (
            not self.attention_only
            or self.ranking_is_order_priority
            or self.creates_trader_setup
            or self.execution_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board is attention only"
            )


@dataclass(frozen=True, slots=True)
class SharedGlobalOpportunityAttentionBoard:
    board_id: str
    as_of: datetime
    evidence_cutoff_at: datetime
    entries: tuple[SharedOpportunityBoardEntry, ...]
    ranking_semantics: str = "CANONICAL_IDENTITY_NOT_EXECUTION_PRIORITY"
    empty_board_valid: bool = True
    execution_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.board_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board_id must be non-empty"
            )
        for name in ("as_of", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.as_of:
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board cannot use future evidence"
            )
        identities = tuple(
            (entry.market, entry.horizon, entry.candidate_id) for entry in self.entries
        )
        if identities != tuple(sorted(identities)):
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board entries must use canonical identity order"
            )
        if len(identities) != len(set(identities)):
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board entries must be unique"
            )
        if any(entry.observed_at > self.as_of for entry in self.entries):
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board cannot contain future entry"
            )
        if self.ranking_semantics != "CANONICAL_IDENTITY_NOT_EXECUTION_PRIORITY":
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board cannot encode execution ranking"
            )
        if (
            not self.empty_board_valid
            or self.execution_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "global opportunity board cannot carry sovereign authority"
            )

    @property
    def is_empty(self) -> bool:
        return not self.entries

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["as_of"] = self.as_of.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = self.evidence_cutoff_at.astimezone(UTC).isoformat()
        for entry in payload["entries"]:
            entry["maturity"] = str(entry["maturity"])
            entry["trajectory"] = (
                None if entry["trajectory"] is None else str(entry["trajectory"])
            )
            entry["observed_at"] = entry["observed_at"].astimezone(UTC).isoformat()
            entry["evidence_cutoff_at"] = (
                entry["evidence_cutoff_at"].astimezone(UTC).isoformat()
            )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


def _entry(candidate: SharedOpportunityBoardCandidate) -> SharedOpportunityBoardEntry | None:
    assessment = candidate.assessment
    if assessment.maturity not in _ATTENTION_MATURITIES:
        return None

    dominant = assessment.dominant_mechanism
    dominant_state = next(
        (
            state
            for state in assessment.head_states
            if state.mechanism is dominant
        ),
        None,
    )
    trajectory_score = 0 if dominant_state is None else dominant_state.trajectory_score_bps
    support = max(
        0,
        min(
            10_000,
            trajectory_score
            - assessment.contradiction_bps // 2
            - assessment.uncertainty_bps // 2,
        ),
    )
    return SharedOpportunityBoardEntry(
        candidate_id=candidate.candidate_id,
        market=assessment.asset,
        horizon=candidate.horizon,
        maturity=assessment.maturity,
        trajectory=dominant,
        trajectory_score_bps=trajectory_score,
        support_bps=support,
        contradiction_bps=assessment.contradiction_bps,
        uncertainty_bps=assessment.uncertainty_bps,
        data_health_bps=candidate.data_health_bps,
        relevant_traders=candidate.relevant_traders,
        observed_at=candidate.observed_at,
        evidence_cutoff_at=candidate.evidence_cutoff_at,
        provenance_refs=candidate.provenance_refs,
    )


def build_global_opportunity_attention_board(
    *,
    board_id: str,
    as_of: datetime,
    evidence_cutoff_at: datetime,
    candidates: Iterable[SharedOpportunityBoardCandidate],
) -> SharedGlobalOpportunityAttentionBoard:
    entries = tuple(
        sorted(
            (
                entry
                for candidate in candidates
                if (entry := _entry(candidate)) is not None
            ),
            key=lambda item: (item.market, item.horizon, item.candidate_id),
        )
    )
    return SharedGlobalOpportunityAttentionBoard(
        board_id=board_id,
        as_of=as_of,
        evidence_cutoff_at=evidence_cutoff_at,
        entries=entries,
    )
