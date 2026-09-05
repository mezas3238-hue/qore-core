"""CF-08 — Profit / Trade Outcome Journal.

Functional record SEMANTICS only (no persistence): an immutable outcome record
binds an exact Trader version/config to its fills, decisions and economic results.
Economics (PnL/MFE/MAE/exposure) may only be recorded when fill evidence exists —
they can never be invented absent fills.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalError,
    CiboFunctionalValidationError,
    _validate_code,
    _validate_evidence_refs,
    _validate_timestamp,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileValidationError,
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchRunValidationError
from qore.kernel.result import Failure, Result, Success


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboFunctionalValidationError(f"{field_name} must be a finite Decimal")


def _decimal_logical(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def _revalidate_identity(identity: ResearchDecisionEvaluatorIdentity) -> None:
    try:
        ResearchDecisionEvaluatorIdentity.__post_init__(identity)
        identity.family.__post_init__()
        identity.schema_version.__post_init__()
        identity.software_revision.__post_init__()
    except (
        ResearchLineageValidationError,
        ResearchRunValidationError,
        AttributeError,
        TypeError,
    ):
        raise CiboFunctionalValidationError(
            "trader identity must be a valid ResearchDecisionEvaluatorIdentity"
        ) from None


def _revalidate_fingerprint(fingerprint: CiboTraderConfigFingerprint) -> None:
    try:
        CiboTraderConfigFingerprint.__post_init__(fingerprint)
    except (CiboCapabilityProfileValidationError, AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "config fingerprint must be a valid CiboTraderConfigFingerprint"
        ) from None


def _validate_optional_ref(
    value: CiboEvidenceRef | None,
    *,
    field_name: str,
) -> CiboEvidenceRef | None:
    if value is None:
        return None
    if not isinstance(value, CiboEvidenceRef):
        raise CiboFunctionalValidationError(f"{field_name} must be a CiboEvidenceRef or None")
    try:
        CiboEvidenceRef.__post_init__(value)
    except (CiboCapabilityProfileValidationError, AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a valid CiboEvidenceRef"
        ) from None
    return value


@dataclass(frozen=True, slots=True)
class CiboOutcomeRecord:
    """Immutable outcome record semantics; no persistence and no execution authority."""

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    instrument_code: str
    regime_code: str
    decision_refs: tuple[CiboEvidenceRef, ...]
    mode_code: str
    action_code: str
    risk_decision_ref: CiboEvidenceRef | None
    demo_fill_refs: tuple[CiboEvidenceRef, ...]
    reconciliation_refs: tuple[CiboEvidenceRef, ...]
    gross_pnl: Decimal | None
    net_pnl: Decimal | None
    mfe: Decimal | None
    mae: Decimal | None
    exposure: Decimal | None
    stop_target_lifecycle_code: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "outcome record requires ResearchDecisionEvaluatorIdentity"
            )
        _revalidate_identity(self.trader_identity)
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboFunctionalValidationError(
                "outcome record requires CiboTraderConfigFingerprint"
            )
        _revalidate_fingerprint(self.config_fingerprint)
        object.__setattr__(
            self,
            "instrument_code",
            _validate_code(self.instrument_code, field_name="instrument code"),
        )
        object.__setattr__(
            self,
            "regime_code",
            _validate_code(self.regime_code, field_name="regime code"),
        )
        object.__setattr__(
            self,
            "decision_refs",
            _validate_evidence_refs(self.decision_refs, field_name="decision refs"),
        )
        object.__setattr__(
            self,
            "mode_code",
            _validate_code(self.mode_code, field_name="mode code"),
        )
        object.__setattr__(
            self,
            "action_code",
            _validate_code(self.action_code, field_name="action code"),
        )
        object.__setattr__(
            self,
            "risk_decision_ref",
            _validate_optional_ref(self.risk_decision_ref, field_name="risk decision ref"),
        )
        object.__setattr__(
            self,
            "demo_fill_refs",
            _validate_evidence_refs(self.demo_fill_refs, field_name="demo fill refs"),
        )
        object.__setattr__(
            self,
            "reconciliation_refs",
            _validate_evidence_refs(
                self.reconciliation_refs,
                field_name="reconciliation refs",
            ),
        )
        economics = (
            ("gross_pnl", self.gross_pnl),
            ("net_pnl", self.net_pnl),
            ("mfe", self.mfe),
            ("mae", self.mae),
            ("exposure", self.exposure),
        )
        for name, value in economics:
            if value is not None:
                _validate_decimal(value, field_name=name)
        object.__setattr__(
            self,
            "stop_target_lifecycle_code",
            _validate_code(
                self.stop_target_lifecycle_code,
                field_name="stop target lifecycle code",
            ),
        )
        _validate_timestamp(self.recorded_at, field_name="outcome recorded_at")
        if any(value is not None for _, value in economics) and not self.demo_fill_refs:
            raise CiboFunctionalValidationError(
                "outcome economics require demo fill evidence; cannot invent fills"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.instrument_code,
            self.regime_code,
            tuple(item.logical_values() for item in self.decision_refs),
            self.mode_code,
            self.action_code,
            None if self.risk_decision_ref is None else self.risk_decision_ref.logical_values(),
            tuple(item.logical_values() for item in self.demo_fill_refs),
            tuple(item.logical_values() for item in self.reconciliation_refs),
            _decimal_logical(self.gross_pnl),
            _decimal_logical(self.net_pnl),
            _decimal_logical(self.mfe),
            _decimal_logical(self.mae),
            _decimal_logical(self.exposure),
            self.stop_target_lifecycle_code,
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboOutcomeJournal:
    """Deterministic, stateless outcome journal (functional record semantics only)."""

    def record(
        self,
        *,
        trader_identity: ResearchDecisionEvaluatorIdentity,
        config_fingerprint: CiboTraderConfigFingerprint,
        instrument_code: str,
        regime_code: str,
        decision_refs: tuple[CiboEvidenceRef, ...],
        mode_code: str,
        action_code: str,
        risk_decision_ref: CiboEvidenceRef | None,
        demo_fill_refs: tuple[CiboEvidenceRef, ...],
        reconciliation_refs: tuple[CiboEvidenceRef, ...],
        gross_pnl: Decimal | None,
        net_pnl: Decimal | None,
        mfe: Decimal | None,
        mae: Decimal | None,
        exposure: Decimal | None,
        stop_target_lifecycle_code: str,
        recorded_at: datetime,
    ) -> Result[CiboOutcomeRecord, CiboFunctionalError]:
        """Record an immutable outcome bound to exact trader/version/config evidence."""
        try:
            return Success(
                CiboOutcomeRecord(
                    trader_identity=trader_identity,
                    config_fingerprint=config_fingerprint,
                    instrument_code=instrument_code,
                    regime_code=regime_code,
                    decision_refs=decision_refs,
                    mode_code=mode_code,
                    action_code=action_code,
                    risk_decision_ref=risk_decision_ref,
                    demo_fill_refs=demo_fill_refs,
                    reconciliation_refs=reconciliation_refs,
                    gross_pnl=gross_pnl,
                    net_pnl=net_pnl,
                    mfe=mfe,
                    mae=mae,
                    exposure=exposure,
                    stop_target_lifecycle_code=stop_target_lifecycle_code,
                    recorded_at=recorded_at,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
