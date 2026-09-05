"""Shared provider-neutral contracts for the CIBO functional executive system.

Every functional domain (CF-01..CF-20) builds on these types. They encode the
canonical separation ``FUNCTIONAL OUTPUT != EXECUTION AUTHORITY``: the authority
ceiling of any functional output is a recommendation/request/abstention/escalation,
never an order, a Risk decision, a provider instruction, or a code/config mutation.

Authority-root law (Correction 003):

- ``PUBLICLY CONSTRUCTIBLE RECORD != AUTHORITY-ROOTED ATTESTATION``
- ``TYPE VALIDITY != PROVENANCE AUTHENTICITY``
- ``CIBO FUNCTIONS != RISK / MARKET / ECONOMIC / LAB CERTIFICATION AUTHORITY``
- ``NO AUTHORITY ROOT -> EVIDENCE_DEPENDENT / FAIL CLOSED``

A well-typed producer value record (a resolved ``risk.`` ``FunctionalDecision``, a
qualified market observation, or a research economic result) is a *public value
record*, not a receipt proving the owning authority emitted it. QORE currently
exposes no authority-rooted issuance/receipt/verifier boundary for any of the four
governed kinds, so CIBO Functions cannot establish provenance and therefore cannot
manufacture ``SUFFICIENT`` governed evidence. Every such kind surfaces through the
explicit fail-closed ``EVIDENCE_DEPENDENT`` seam instead.
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

    ``SUFFICIENT`` remains in the catalog only as the *external-authority-injected*
    outcome: a CIBO Function is not a Risk / Market / Economic / Lab certification
    authority and has no authority-rooted receipt, so ``CiboFunctionalEvidence``
    refuses to construct a SUFFICIENT assessment. Every CIBO-manufacturable
    evidence-bearing conclusion is therefore ``EVIDENCE_DEPENDENT`` (an explicit
    external-authority dependency seam) or a fail-closed negative status.
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


@dataclass(frozen=True, slots=True)
class CiboFunctionalEvidence:
    """Explicit evidence assessment bound to refs, freshness, and authority dependency.

    ``SUFFICIENT`` is the only status under which a downstream functional step may
    treat a fact as authoritative, and it requires an external authority-rooted
    receipt. CIBO Functions are not certification authorities and expose no such
    receipt, so ``CiboFunctionalEvidence`` refuses to construct SUFFICIENT: a caller
    can never manufacture governed sufficiency. Every evidence-bearing conclusion
    is instead ``EVIDENCE_DEPENDENT`` (explicit dependency kind + seam reasons) or a
    fail-closed negative status.

    Temporal provenance is enforced here: evidence is assessed at an explicit
    timezone-aware ``as_of`` instant; no hidden clock is ever consulted.
    """

    status: CiboEvidenceStatus
    evidence_refs: tuple[CiboEvidenceRef, ...]
    as_of: datetime
    dependency_kind: CiboGovernedEvidenceKind | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Exact runtime enum type: no StrEnum subclass / value-equal laundering.
        if type(self.status) is not CiboEvidenceStatus:
            raise CiboFunctionalValidationError(
                "functional evidence requires exact CiboEvidenceStatus"
            )
        # Authority-root law: CIBO is not a certification authority, so it cannot
        # manufacture SUFFICIENT governed evidence.
        if self.status is CiboEvidenceStatus.SUFFICIENT:
            raise CiboFunctionalValidationError(
                "CIBO functions are not certification authorities; SUFFICIENT "
                "requires an external authority-rooted receipt that CIBO cannot "
                "manufacture"
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
        )


def synthesize_evidence(
    assessments: tuple[CiboFunctionalEvidence, ...],
    *,
    as_of: datetime,
) -> CiboFunctionalEvidence:
    """Deterministically reduce a set of evidence assessments to one conclusion.

    Every nested assessment is reconstructed (recursively revalidated) before its
    status, refs, and dependency are consumed, so reflective corruption or
    malformed nested material fails closed instead of being trusted. Contradiction
    dominates; then stale/evidence-dependent/missing/insufficient. SUFFICIENT is
    never synthesized because a CIBO Function cannot manufacture it.
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
        # Unreachable: a non-empty assessment set without any negative status would
        # be all-SUFFICIENT, which a CIBO Function cannot manufacture.
        raise CiboFunctionalValidationError(
            "synthesize_evidence cannot conclude SUFFICIENT without an authority root"
        )
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
    return CiboFunctionalEvidence(
        status=status,
        evidence_refs=refs,
        as_of=as_of,
        dependency_kind=dependency_kind,
        reasons=reasons,
    )
