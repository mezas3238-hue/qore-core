"""Provider-neutral operating authority for CIBO Trader Manager.

CIBO owns the management posture of a selected Trader.  It may decide to build,
protect, bank, attack, lock, reduce or suspend.  Any capital-bearing posture is
expressed as a request to Risk; this module deliberately has no execution,
provider-order or RiskAuthorization fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.cibo_trader_manager import (
    CiboDemoManagementState,
    CiboManagementDecision,
    CiboRiskMode,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.errors import InfrastructureError


class CiboOperatingManagerError(InfrastructureError):
    """Base error for CIBO Trader operating-management contracts."""

    __slots__ = ()


class CiboOperatingManagerValidationError(CiboOperatingManagerError):
    """An operating-management input violates a fail-closed invariant."""

    __slots__ = ()


class CiboOperatingPosture(StrEnum):
    """CIBO-owned strategic posture for one managed Trader."""

    BUILD = "build"
    PROTECT = "protect"
    BANK = "bank"
    ATTACK = "attack"
    LOCK = "lock"
    REDUCE = "reduce"
    SUSPEND = "suspend"


class CiboRiskRequestMode(StrEnum):
    """Non-authoritative Risk request emitted by CIBO."""

    BASE = "base"
    REDUCED = "reduced"
    ATTACK = "attack"
    LOCK = "lock"
    ZERO = "zero"


def _decimal(value: Decimal, *, field_name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboOperatingManagerValidationError(
            f"{field_name} must be a finite Decimal"
        )
    return value


def _timestamp(value: datetime, *, field_name: str) -> datetime:
    if type(value) is not datetime:
        raise CiboOperatingManagerValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboOperatingManagerValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value


def _refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboOperatingManagerValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboOperatingManagerValidationError(
            f"{field_name} must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboOperatingAuthority:
    """Exact Trader binding under which CIBO may issue operating decisions.

    A production/DEMO authority should be derived from a SELECTED
    ``CiboManagementDecision``. Research may construct an explicitly marked
    research authority, which cannot be confused with execution authorization.
    """

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    risk_mode: CiboRiskMode
    authority_ref: CiboEvidenceRef
    research_only: bool

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboOperatingManagerValidationError(
                "operating authority requires exact Trader identity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboOperatingManagerValidationError(
                "operating authority requires exact config fingerprint"
            )
        if self.risk_mode is not CiboRiskMode.CIBO_MANAGED_TRADERS_RISK:
            raise CiboOperatingManagerValidationError(
                "operating authority requires CIBO_MANAGED_TRADERS_RISK"
            )
        if not isinstance(self.authority_ref, CiboEvidenceRef):
            raise CiboOperatingManagerValidationError(
                "operating authority requires evidence reference"
            )
        if type(self.research_only) is not bool:
            raise CiboOperatingManagerValidationError(
                "research_only must be bool"
            )

    @classmethod
    def from_selected_management(
        cls,
        decision: CiboManagementDecision,
        *,
        authority_ref: CiboEvidenceRef,
    ) -> CiboOperatingAuthority:
        """Bind operating authority to a prior exact SELECTED manager decision."""

        if not isinstance(decision, CiboManagementDecision):
            raise CiboOperatingManagerValidationError(
                "selected management decision is required"
            )
        CiboManagementDecision.__post_init__(decision)
        if decision.state is not CiboDemoManagementState.SELECTED:
            raise CiboOperatingManagerValidationError(
                "operating authority requires SELECTED Trader state"
            )
        if decision.risk_mode is not CiboRiskMode.CIBO_MANAGED_TRADERS_RISK:
            raise CiboOperatingManagerValidationError(
                "selected Trader must use CIBO-managed Risk mode"
            )
        return cls(
            trader_identity=decision.trader_identity,
            config_fingerprint=decision.config_fingerprint,
            risk_mode=decision.risk_mode,
            authority_ref=authority_ref,
            research_only=False,
        )


@dataclass(frozen=True, slots=True)
class CiboCapitalSnapshot:
    """Evidence-bound capital context observed by CIBO before a decision."""

    starting_equity: Decimal
    equity: Decimal
    peak_equity: Decimal
    day_start_equity: Decimal
    risk_floor: Decimal
    current_banked_floor: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        values = {
            "starting_equity": self.starting_equity,
            "equity": self.equity,
            "peak_equity": self.peak_equity,
            "day_start_equity": self.day_start_equity,
            "risk_floor": self.risk_floor,
            "current_banked_floor": self.current_banked_floor,
        }
        for name, value in values.items():
            _decimal(value, field_name=name)
        if min(
            self.starting_equity,
            self.equity,
            self.peak_equity,
            self.day_start_equity,
        ) <= 0:
            raise CiboOperatingManagerValidationError(
                "equity values must be positive"
            )
        if self.peak_equity < self.equity:
            raise CiboOperatingManagerValidationError(
                "peak equity cannot be below current equity"
            )
        if not Decimal(0) <= self.risk_floor <= self.equity:
            raise CiboOperatingManagerValidationError(
                "risk floor must be within current equity"
            )
        if not Decimal(0) <= self.current_banked_floor <= self.equity:
            raise CiboOperatingManagerValidationError(
                "banked floor must be within current equity"
            )
        _timestamp(self.observed_at, field_name="observed_at")

    @property
    def effective_floor(self) -> Decimal:
        return max(self.risk_floor, self.current_banked_floor)


@dataclass(frozen=True, slots=True)
class CiboRiskRequest:
    """CIBO request to Risk; never a Risk authorization."""

    mode: CiboRiskRequestMode
    requested_envelope_ref: CiboEvidenceRef | None
    cibo_loss_budget_ceiling: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CiboRiskRequestMode):
            raise CiboOperatingManagerValidationError(
                "risk request mode must be CiboRiskRequestMode"
            )
        _decimal(
            self.cibo_loss_budget_ceiling,
            field_name="cibo_loss_budget_ceiling",
        )
        if self.cibo_loss_budget_ceiling < 0:
            raise CiboOperatingManagerValidationError(
                "CIBO loss budget ceiling cannot be negative"
            )
        if self.mode is CiboRiskRequestMode.ZERO:
            if self.requested_envelope_ref is not None:
                raise CiboOperatingManagerValidationError(
                    "ZERO request cannot carry Risk envelope"
                )
            if self.cibo_loss_budget_ceiling != 0:
                raise CiboOperatingManagerValidationError(
                    "ZERO request must have zero CIBO loss budget"
                )
        elif not isinstance(self.requested_envelope_ref, CiboEvidenceRef):
            raise CiboOperatingManagerValidationError(
                "capital-bearing request requires Risk-envelope evidence"
            )


@dataclass(frozen=True, slots=True)
class CiboOperatingDecision:
    """Immutable CIBO operating decision with no execution authority."""

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    posture: CiboOperatingPosture
    protected_capital_floor: Decimal
    free_cushion: Decimal
    risk_request: CiboRiskRequest
    reasons: tuple[str, ...]
    evidence_refs: tuple[CiboEvidenceRef, ...]
    decided_at: datetime
    research_only: bool

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboOperatingManagerValidationError(
                "operating decision requires exact Trader identity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboOperatingManagerValidationError(
                "operating decision requires exact config fingerprint"
            )
        if not isinstance(self.posture, CiboOperatingPosture):
            raise CiboOperatingManagerValidationError(
                "operating decision requires CIBO posture"
            )
        _decimal(
            self.protected_capital_floor,
            field_name="protected_capital_floor",
        )
        _decimal(self.free_cushion, field_name="free_cushion")
        if self.protected_capital_floor < 0 or self.free_cushion < 0:
            raise CiboOperatingManagerValidationError(
                "capital floors and cushions cannot be negative"
            )
        if not isinstance(self.risk_request, CiboRiskRequest):
            raise CiboOperatingManagerValidationError(
                "operating decision requires CiboRiskRequest"
            )
        if not isinstance(self.reasons, tuple) or not self.reasons:
            raise CiboOperatingManagerValidationError(
                "operating decision requires reasons"
            )
        if any(not isinstance(item, str) or not item for item in self.reasons):
            raise CiboOperatingManagerValidationError(
                "operating reasons must be non-empty strings"
            )
        if len(set(self.reasons)) != len(self.reasons):
            raise CiboOperatingManagerValidationError(
                "operating reasons must not contain duplicates"
            )
        object.__setattr__(self, "reasons", tuple(sorted(self.reasons)))
        object.__setattr__(
            self,
            "evidence_refs",
            _refs(self.evidence_refs, field_name="operating evidence refs"),
        )
        _timestamp(self.decided_at, field_name="decided_at")
        if type(self.research_only) is not bool:
            raise CiboOperatingManagerValidationError(
                "research_only must be bool"
            )


_POSTURE_TO_RISK_MODE = {
    CiboOperatingPosture.BUILD: CiboRiskRequestMode.BASE,
    CiboOperatingPosture.PROTECT: CiboRiskRequestMode.BASE,
    CiboOperatingPosture.BANK: CiboRiskRequestMode.BASE,
    CiboOperatingPosture.ATTACK: CiboRiskRequestMode.ATTACK,
    CiboOperatingPosture.LOCK: CiboRiskRequestMode.LOCK,
    CiboOperatingPosture.REDUCE: CiboRiskRequestMode.REDUCED,
    CiboOperatingPosture.SUSPEND: CiboRiskRequestMode.ZERO,
}


@dataclass(frozen=True, slots=True)
class CiboTraderOperatingManager:
    """CIBO-owned Trader operating authority, bounded only by Risk sovereignty."""

    def issue(
        self,
        authority: CiboOperatingAuthority,
        posture: CiboOperatingPosture,
        capital: CiboCapitalSnapshot,
        *,
        protected_capital_floor: Decimal,
        requested_risk_envelope: CiboEvidenceRef | None,
        decided_at: datetime,
        reasons: tuple[str, ...],
        evidence_refs: tuple[CiboEvidenceRef, ...] = (),
    ) -> CiboOperatingDecision:
        """Issue CIBO posture and a non-authoritative request to Risk."""

        if not isinstance(authority, CiboOperatingAuthority):
            raise CiboOperatingManagerValidationError(
                "operating decision requires CiboOperatingAuthority"
            )
        CiboOperatingAuthority.__post_init__(authority)
        if not isinstance(posture, CiboOperatingPosture):
            raise CiboOperatingManagerValidationError(
                "posture must be CiboOperatingPosture"
            )
        if not isinstance(capital, CiboCapitalSnapshot):
            raise CiboOperatingManagerValidationError(
                "operating decision requires CiboCapitalSnapshot"
            )
        CiboCapitalSnapshot.__post_init__(capital)
        _timestamp(decided_at, field_name="decided_at")
        if decided_at < capital.observed_at:
            raise CiboOperatingManagerValidationError(
                "decision cannot predate capital observation"
            )

        floor = _decimal(
            protected_capital_floor,
            field_name="protected_capital_floor",
        )
        if floor < capital.current_banked_floor:
            raise CiboOperatingManagerValidationError(
                "CIBO cannot unbank previously protected capital"
            )
        if floor > capital.equity:
            raise CiboOperatingManagerValidationError(
                "protected capital floor cannot exceed current equity"
            )

        effective_floor = max(capital.risk_floor, floor)
        free_cushion = max(Decimal(0), capital.equity - effective_floor)
        mode = _POSTURE_TO_RISK_MODE[posture]

        if posture is CiboOperatingPosture.ATTACK:
            if floor <= capital.starting_equity:
                raise CiboOperatingManagerValidationError(
                    "ATTACK requires banked profit above starting equity"
                )
            if free_cushion <= 0:
                raise CiboOperatingManagerValidationError(
                    "ATTACK requires positive unprotected free cushion"
                )

        if posture is CiboOperatingPosture.BANK and floor <= capital.current_banked_floor:
            raise CiboOperatingManagerValidationError(
                "BANK must increase protected capital"
            )

        if mode is CiboRiskRequestMode.ZERO:
            envelope = None
            budget = Decimal(0)
        else:
            if not isinstance(requested_risk_envelope, CiboEvidenceRef):
                raise CiboOperatingManagerValidationError(
                    "capital-bearing CIBO posture requires Risk envelope"
                )
            envelope = requested_risk_envelope
            budget = free_cushion

        refs = _refs(evidence_refs, field_name="operating evidence refs")
        return CiboOperatingDecision(
            trader_identity=authority.trader_identity,
            config_fingerprint=authority.config_fingerprint,
            posture=posture,
            protected_capital_floor=floor,
            free_cushion=free_cushion,
            risk_request=CiboRiskRequest(
                mode=mode,
                requested_envelope_ref=envelope,
                cibo_loss_budget_ceiling=budget,
            ),
            reasons=reasons,
            evidence_refs=(authority.authority_ref, *refs),
            decided_at=decided_at,
            research_only=authority.research_only,
        )
