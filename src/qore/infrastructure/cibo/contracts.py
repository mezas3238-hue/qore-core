"""Shared provider-neutral contracts for the CIBO functional executive system.

Every functional domain (CF-01..CF-20) builds on these types. They encode the
canonical separation ``FUNCTIONAL OUTPUT != EXECUTION AUTHORITY``: the authority
ceiling of any functional output is a recommendation/request/abstention/escalation,
never an order, a Risk decision, a provider instruction, or a code/config mutation.

Authority-root law (Correction 003):

- ``PUBLICLY CONSTRUCTIBLE RECORD != AUTHORITY-ROOTED ATTESTATION``
- ``TYPE VALIDITY != PROVENANCE AUTHENTICITY``
- ``CIBO FUNCTIONS != TRADER LAB APPROVAL AUTHORITY``
- ``NO TRADER LAB PASS RECEIPT -> EVIDENCE_DEPENDENT / FAIL CLOSED``

A well-typed producer value record is still only a public value record.  CIBO may
treat evidence as ``SUFFICIENT`` only when Trader Lab has executed the exact CIBO
function gate, observed PASS, and issued a sealed chained receipt.  CIBO cannot
mint that receipt, skip the preceding function, or convert FAIL into PASS.  Owner
authority remains above Trader Lab.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.errors import InfrastructureError

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboFunctionalError(InfrastructureError):
    """Base error for the CIBO functional executive system."""

    __slots__ = ()


class CiboFunctionalValidationError(CiboFunctionalError):
    """A functional input violates a deterministic CIBO invariant."""

    __slots__ = ()


class CiboFunctionalBlockedError(CiboFunctionalError):
    """Fail-closed result when a functional step cannot proceed safely."""

    __slots__ = ()


class CiboFunctionalAuthority(StrEnum):
    """Authority ceiling of a functional output.

    There is deliberately no EXECUTION/ORDER/DECISION member: functional outputs
    may only observe, opine, recommend, abstain, escalate, or request work.
    """

    OBSERVATION = "observation"
    OPINION = "opinion"
    RECOMMENDATION = "recommendation"
    ABSTENTION = "abstention"
    ESCALATION = "escalation"
    REQUEST = "request"


class CiboEvidenceStatus(StrEnum):
    """Evidence-sufficiency status a functional step may conclude.

    ``SUFFICIENT`` is an external-authority-injected outcome.  It is valid only
    with a sealed Trader Lab PASS receipt for the exact sequential CIBO function
    gate.  CIBO cannot self-mint such a receipt; without it, evidence remains
    ``EVIDENCE_DEPENDENT`` or a fail-closed negative status.
    """

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    STALE = "stale"
    CONTRADICTORY = "contradictory"
    MISSING = "missing"
    EVIDENCE_DEPENDENT = "evidence-dependent"


class CiboGovernedEvidenceKind(StrEnum):
    """Closed catalog of external-authority dependency kinds.

    These are the four owning authorities whose provenance a CIBO Function can
    never self-certify: Risk, Market Intelligence, Economic Intelligence, and the
    Trader Lab. When a functional conclusion is ``EVIDENCE_DEPENDENT`` it must name
    exactly one of these kinds plus explicit seam reasons; it can never be inferred
    to SUFFICIENT.
    """

    LAB = "lab"
    MARKET = "market"
    ECONOMIC = "economic"
    RISK = "risk"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    # Exact runtime type: a datetime subclass could override the ordering
    # operators used by temporal-provenance checks, so subclasses are rejected.
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _validate_trader_lab_pass_receipts(
    values: tuple[object, ...],
    *,
    as_of: datetime,
) -> tuple[object, ...]:
    """Validate external Trader Lab PASS receipts without creating an import cycle."""

    if not isinstance(values, tuple):
        raise CiboFunctionalValidationError(
            "Trader Lab PASS receipts must be an immutable tuple"
        )
    from qore.infrastructure.trader_lab.cibo_functional_receipt import (
        TraderLabCiboFunctionPassReceipt,
        validate_trader_lab_cibo_function_pass_receipt,
    )

    normalized: dict[str, TraderLabCiboFunctionPassReceipt] = {}
    for receipt in values:
        if type(receipt) is not TraderLabCiboFunctionPassReceipt:
            raise CiboFunctionalValidationError(
                "functional evidence accepts only exact Trader Lab PASS receipts"
            )
        try:
            validate_trader_lab_cibo_function_pass_receipt(receipt)
        except Exception as error:
            raise CiboFunctionalValidationError(
                "invalid Trader Lab PASS receipt"
            ) from error
        if receipt.approved_at > as_of:
            raise CiboFunctionalValidationError(
                "Trader Lab PASS receipt cannot postdate functional evidence as_of"
            )
        existing = normalized.get(receipt.receipt_sha256)
        if existing is not None and existing.logical_values() != receipt.logical_values():
            raise CiboFunctionalValidationError(
                "duplicate Trader Lab PASS fingerprint with differing material"
            )
        normalized[receipt.receipt_sha256] = receipt
    return tuple(
        sorted(
            normalized.values(),
            key=lambda item: (
                item.candidate.fingerprint.value,
                item.function.value,
                item.receipt_sha256,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class CiboFunctionalEvidence:
    """Evidence assessment with an external Trader-Lab authority seam.

    CIBO still cannot self-certify. SUFFICIENT is constructible only when at
    least one sealed Trader Lab PASS receipt is supplied and revalidated. A plain
    ref, UUID, timestamp, public value record, or CIBO-produced object can never
    manufacture sufficiency.

    Owner authority remains above Trader Lab; this type only models the technical
    Trader-Lab to CIBO evidence boundary.
    """

    status: CiboEvidenceStatus
    evidence_refs: tuple[CiboEvidenceRef, ...]
    as_of: datetime
    dependency_kind: CiboGovernedEvidenceKind | None = None
    reasons: tuple[str, ...] = ()
    trader_lab_pass_receipts: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        if type(self.status) is not CiboEvidenceStatus:
            raise CiboFunctionalValidationError(
                "functional evidence requires exact CiboEvidenceStatus"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        if (
            self.dependency_kind is not None
            and type(self.dependency_kind) is not CiboGovernedEvidenceKind
        ):
            raise CiboFunctionalValidationError(
                "functional evidence dependency kind must be exact "
                "CiboGovernedEvidenceKind"
            )
        _validate_timestamp(self.as_of, field_name="functional evidence as_of")
        object.__setattr__(
            self,
            "reasons",
            _validate_codes(self.reasons, field_name="evidence reasons"),
        )
        receipts = _validate_trader_lab_pass_receipts(
            self.trader_lab_pass_receipts,
            as_of=self.as_of,
        )
        object.__setattr__(self, "trader_lab_pass_receipts", receipts)

        if self.status is CiboEvidenceStatus.SUFFICIENT:
            if not receipts:
                raise CiboFunctionalValidationError(
                    "SUFFICIENT requires a sealed Trader Lab PASS receipt"
                )
            if self.dependency_kind is not None:
                raise CiboFunctionalValidationError(
                    "SUFFICIENT evidence cannot carry an unresolved dependency kind"
                )
            if self.reasons:
                raise CiboFunctionalValidationError(
                    "SUFFICIENT evidence cannot carry unresolved seam reasons"
                )
            receipt_refs = {receipt.evidence_ref for receipt in receipts}
            if not receipt_refs.issubset(set(self.evidence_refs)):
                raise CiboFunctionalValidationError(
                    "SUFFICIENT evidence refs must include every Trader Lab PASS receipt"
                )
        else:
            if receipts:
                raise CiboFunctionalValidationError(
                    "Trader Lab PASS receipts are only valid with SUFFICIENT evidence"
                )
            if self.status is CiboEvidenceStatus.EVIDENCE_DEPENDENT:
                if self.dependency_kind is None:
                    raise CiboFunctionalValidationError(
                        "evidence-dependent evidence requires an explicit dependency kind"
                    )
                if not self.reasons:
                    raise CiboFunctionalValidationError(
                        "evidence-dependent evidence requires an explicit seam reason"
                    )
            elif self.dependency_kind is not None:
                raise CiboFunctionalValidationError(
                    "dependency kind is only valid for evidence-dependent evidence"
                )

        if (
            self.status is not CiboEvidenceStatus.CONTRADICTORY
            and not self.evidence_refs
            and not self.reasons
        ):
            raise CiboFunctionalValidationError(
                "non-contradictory evidence without refs requires a reason"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.as_of.isoformat(),
            None if self.dependency_kind is None else self.dependency_kind.value,
            self.reasons,
            tuple(
                receipt.logical_values()
                for receipt in self.trader_lab_pass_receipts
            ),
        )


def synthesize_evidence(
    assessments: tuple[CiboFunctionalEvidence, ...],
    *,
    as_of: datetime,
) -> CiboFunctionalEvidence:
    """Reduce evidence while preserving external Trader Lab authority.

    Negative or blocked evidence dominates. SUFFICIENT is synthesized only when
    every input is already SUFFICIENT and every carried Trader Lab PASS receipt
    revalidates. CIBO combines external approval; it never manufactures approval.
    """

    if not isinstance(assessments, tuple) or any(
        not isinstance(item, CiboFunctionalEvidence) for item in assessments
    ):
        raise CiboFunctionalValidationError(
            "assessments must be a tuple of CiboFunctionalEvidence"
        )
    revalidated = tuple(
        CiboFunctionalEvidence(
            status=item.status,
            evidence_refs=item.evidence_refs,
            as_of=item.as_of,
            dependency_kind=item.dependency_kind,
            reasons=item.reasons,
            trader_lab_pass_receipts=item.trader_lab_pass_receipts,
        )
        for item in assessments
    )
    _validate_timestamp(as_of, field_name="synthesize as_of")
    statuses = {item.status for item in revalidated}
    if CiboEvidenceStatus.CONTRADICTORY in statuses:
        status = CiboEvidenceStatus.CONTRADICTORY
    elif CiboEvidenceStatus.STALE in statuses:
        status = CiboEvidenceStatus.STALE
    elif CiboEvidenceStatus.EVIDENCE_DEPENDENT in statuses:
        status = CiboEvidenceStatus.EVIDENCE_DEPENDENT
    elif CiboEvidenceStatus.MISSING in statuses:
        status = CiboEvidenceStatus.MISSING
    elif CiboEvidenceStatus.INSUFFICIENT in statuses:
        status = CiboEvidenceStatus.INSUFFICIENT
    elif not assessments:
        status = CiboEvidenceStatus.MISSING
    else:
        status = CiboEvidenceStatus.SUFFICIENT

    dependency_kind: CiboGovernedEvidenceKind | None = None
    if status is CiboEvidenceStatus.EVIDENCE_DEPENDENT:
        kinds = {
            item.dependency_kind
            for item in revalidated
            if item.status is CiboEvidenceStatus.EVIDENCE_DEPENDENT
        }
        if len(kinds) != 1:
            raise CiboFunctionalValidationError(
                "synthesized evidence-dependent evidence requires a single "
                "dependency kind"
            )
        dependency_kind = next(iter(kinds))

    refs = tuple(
        sorted(
            {ref for item in revalidated for ref in item.evidence_refs},
            key=lambda ref: ref.value,
        )
    )
    reasons = tuple(
        sorted({reason for item in revalidated for reason in item.reasons})
    )
    receipts: tuple[object, ...] = ()
    if status is CiboEvidenceStatus.SUFFICIENT:
        by_fingerprint = {
            receipt.receipt_sha256: receipt
            for item in revalidated
            for receipt in item.trader_lab_pass_receipts
        }
        receipts = tuple(
            sorted(
                by_fingerprint.values(),
                key=lambda item: (
                    item.candidate.fingerprint.value,
                    item.function.value,
                    item.receipt_sha256,
                ),
            )
        )
        reasons = ()

    return CiboFunctionalEvidence(
        status=status,
        evidence_refs=refs,
        as_of=as_of,
        dependency_kind=dependency_kind,
        reasons=reasons,
        trader_lab_pass_receipts=receipts,
    )
