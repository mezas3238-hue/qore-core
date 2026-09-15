"""Append-only Trader Historical Intelligence contracts.

This module owns the exact, immutable, deterministic value objects that carry a
Trader's longitudinal technical/scientific biography: an exact Trader version,
its bounded studies, epistemic status, sufficiency, quantitative claims, and
consumed holdout partitions.

``TRADER HISTORY IS APPEND-ONLY``: no value object here mutates and no history
owns a destructive transition. ``CURRENT CAPABILITY = PROJECTION OF CERTIFIED
HISTORICAL EVIDENCE``: the projection in ``registry.py`` derives a current view
from certified records only, and never invents evidence for stages not actually
completed.

Every value object is ``frozen``/``slots``, enforces exact runtime types (so
``bool`` cannot launder as ``int`` and ``float`` cannot launder as ``Decimal``),
and carries a deterministic ``logical_values()`` projection used for equality,
replay, and fingerprinting. No value object here carries an order, account,
quantity, provider instruction, Risk approval, or Production/real-capital
authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_sample_partition import SampleRole
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)
from qore.kernel.errors import InfrastructureError

_CODE_RE = r"[a-z][a-z0-9._-]*"
_MARKET_RE = r"[A-Z0-9][A-Z0-9._/-]*"
_TOKEN_RE = r"[A-Za-z0-9][A-Za-z0-9._/+:-]*"
_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"
_SHA256_HEX_RE = r"[0-9a-f]{64}"
_SHA_HEX_RE = r"[0-9a-f]{40}"

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)


class TraderHistoryError(InfrastructureError):
    """Base error for the append-only Trader Historical Intelligence Registry."""

    __slots__ = ()


class TraderHistoryValidationError(TraderHistoryError):
    """A historical intelligence value violates a deterministic invariant."""

    __slots__ = ()


class TraderHistoryBlockedError(TraderHistoryError):
    """Fail-closed result when a history operation cannot be performed safely."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise TraderHistoryValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderHistoryValidationError(f"{field_name} must be timezone-aware")


def _utc_iso(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_sha256(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_SHA256_HEX_RE, value) is None:
        raise TraderHistoryValidationError(
            f"{field_name} must be 64 lowercase hex characters"
        )


def _validate_sha(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_SHA_HEX_RE, value) is None:
        raise TraderHistoryValidationError(
            f"{field_name} must be 40 lowercase hex characters"
        )


def _validate_code(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise TraderHistoryValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    return value


def _validate_token(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_TOKEN_RE, value) is None:
        raise TraderHistoryValidationError(
            f"{field_name} must use canonical version-token syntax"
        )


def _validate_market(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_MARKET_RE, value) is None:
        raise TraderHistoryValidationError(
            f"{field_name} must use canonical uppercase market syntax"
        )


def _validate_opaque_ref(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_OPAQUE_REF_RE, value) is None:
        raise TraderHistoryValidationError(
            f"{field_name} must use canonical lowercase opaque-ref syntax"
        )
    if any(part in value for part in _SENSITIVE_PARTS):
        raise TraderHistoryValidationError(
            f"{field_name} must not contain sensitive material"
        )


def _canonical_decimal(value: Decimal) -> str:
    if type(value) is not Decimal or not value.is_finite():
        raise TraderHistoryValidationError(
            "quantitative value must be a finite Decimal"
        )
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def _canonical_json(payload: object) -> bytes:
    def _default(value: object) -> str:
        if type(value) is Decimal:
            return _canonical_decimal(value)
        if type(value) is UUID:
            return str(value)
        if type(value) is datetime:
            return value.astimezone(UTC).isoformat(timespec="microseconds")
        raise TraderHistoryValidationError(
            f"unsupported canonical material: {type(value).__qualname__}"
        )

    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_default,
    ).encode("utf-8")


class TraderHistoryStudyKind(StrEnum):
    """Closed set of longitudinal study kinds, in canonical declaration order."""

    REPLAY = "replay"
    BACKTEST = "backtest"
    FAST_FORWARD = "fast-forward"
    WALK_FORWARD = "walk-forward"
    OOS = "oos"
    STRESS = "stress"
    MONTE_CARLO = "monte-carlo"
    ECONOMIC_EVALUATION = "economic-evaluation"
    RISK_REVIEW = "risk-review"
    CIBO_REVIEW = "cibo-review"
    INDEPENDENT_VALIDATION = "independent-validation"
    DEMO = "demo"
    CHARACTERIZATION = "characterization"
    FAILURE_ANALYSIS = "failure-analysis"
    HYPOTHESIS = "hypothesis"
    HYPOTHESIS_FALSIFICATION = "hypothesis-falsification"
    HYPOTHESIS_CONFIRMATION = "hypothesis-confirmation"
    RETURN_TO_LAB = "return-to-lab"
    REMEDIATION = "remediation"


class TraderHistoryEpistemicStatus(StrEnum):
    """Explicit epistemic status; weak observations can never launder into facts."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"
    FALSIFIED = "falsified"
    CERTIFIED = "certified"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    STALE = "stale"
    SUPERSEDED = "superseded"


class TraderHistorySufficiency(StrEnum):
    """Explicit sample/evidence sufficiency state."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class TraderHistorySide(StrEnum):
    """Deterministic trade side where evidence supports it."""

    BUY = "buy"
    SELL = "sell"


class TraderHistoryFavorableKind(StrEnum):
    """Favorable/weak/degraded/adverse regime classification."""

    FAVORABLE = "favorable"
    WEAK = "weak"
    DEGRADED = "degraded"
    ADVERSE = "adverse"


class TraderHistoryAuthorityKind(StrEnum):
    """Exact certifying authority kind for a longitudinal study.

    ``CERTIFIED`` is never caller assertion: a certified study must carry a
    certification envelope whose authority kind exactly owns the study kind, so a
    caller cannot forge a Risk/CIBO/independent-validation certification for a
    Lab stage (or vice versa).
    """

    TRADER_LAB = "trader-lab"
    RISK = "risk"
    CIBO = "cibo"
    INDEPENDENT_VALIDATION = "independent-validation"
    ECONOMIC = "economic"


_KIND_AUTHORITY: dict[TraderHistoryStudyKind, TraderHistoryAuthorityKind] = {
    TraderHistoryStudyKind.REPLAY: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.BACKTEST: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.FAST_FORWARD: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.WALK_FORWARD: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.OOS: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.STRESS: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.MONTE_CARLO: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.ECONOMIC_EVALUATION: TraderHistoryAuthorityKind.ECONOMIC,
    TraderHistoryStudyKind.RISK_REVIEW: TraderHistoryAuthorityKind.RISK,
    TraderHistoryStudyKind.CIBO_REVIEW: TraderHistoryAuthorityKind.CIBO,
    TraderHistoryStudyKind.INDEPENDENT_VALIDATION: (
        TraderHistoryAuthorityKind.INDEPENDENT_VALIDATION
    ),
    TraderHistoryStudyKind.DEMO: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.CHARACTERIZATION: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.FAILURE_ANALYSIS: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.HYPOTHESIS: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.HYPOTHESIS_FALSIFICATION: (
        TraderHistoryAuthorityKind.TRADER_LAB
    ),
    TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION: (
        TraderHistoryAuthorityKind.TRADER_LAB
    ),
    TraderHistoryStudyKind.RETURN_TO_LAB: TraderHistoryAuthorityKind.TRADER_LAB,
    TraderHistoryStudyKind.REMEDIATION: TraderHistoryAuthorityKind.TRADER_LAB,
}


@dataclass(frozen=True, slots=True)
class TraderHistorySoftwareSha:
    """Exact software revision/SHA (40 lowercase hex Git SHA) of one study/version."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha(self.value, field_name="software sha")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderVersionFingerprint:
    """Canonical SHA-256 digest of the complete exact Trader version identity."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="trader version fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderVersionIdentity:
    """Exact immutable Trader version: code, version, config, methodology, software.

    A new code/config/methodology/software identity is a *new* historical version;
    it never overwrites or relabels evidence belonging to an older version.
    """

    trader_code: DemoTradingTraderCode
    version: DemoTradingTraderVersion
    config_fingerprint: DemoTradingConfigFingerprint
    methodology_id: DemoTradingMethodologyId
    methodology_version: DemoTradingMethodologyVersion
    methodology_fingerprint: DemoTradingMethodologyFingerprint
    software_sha: TraderHistorySoftwareSha
    fingerprint: TraderVersionFingerprint

    def __post_init__(self) -> None:
        if type(self.trader_code) is not DemoTradingTraderCode:
            raise TraderHistoryValidationError(
                "trader version requires DemoTradingTraderCode"
            )
        if type(self.version) is not DemoTradingTraderVersion:
            raise TraderHistoryValidationError(
                "trader version requires DemoTradingTraderVersion"
            )
        if type(self.config_fingerprint) is not DemoTradingConfigFingerprint:
            raise TraderHistoryValidationError(
                "trader version requires DemoTradingConfigFingerprint"
            )
        if type(self.methodology_id) is not DemoTradingMethodologyId:
            raise TraderHistoryValidationError(
                "trader version requires DemoTradingMethodologyId"
            )
        if type(self.methodology_version) is not DemoTradingMethodologyVersion:
            raise TraderHistoryValidationError(
                "trader version requires DemoTradingMethodologyVersion"
            )
        if type(self.methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
            raise TraderHistoryValidationError(
                "trader version requires DemoTradingMethodologyFingerprint"
            )
        if type(self.software_sha) is not TraderHistorySoftwareSha:
            raise TraderHistoryValidationError(
                "trader version requires TraderHistorySoftwareSha"
            )
        if type(self.fingerprint) is not TraderVersionFingerprint:
            raise TraderHistoryValidationError(
                "trader version requires TraderVersionFingerprint"
            )
        expected = compute_trader_version_fingerprint(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=self.config_fingerprint,
            methodology_id=self.methodology_id,
            methodology_version=self.methodology_version,
            methodology_fingerprint=self.methodology_fingerprint,
            software_sha=self.software_sha,
        )
        if self.fingerprint != expected:
            raise TraderHistoryValidationError(
                "trader version fingerprint must match the exact identity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_code.value,
            self.version.value,
            self.config_fingerprint.value,
            self.methodology_id.value,
            self.methodology_version.value,
            self.methodology_fingerprint.value,
            self.software_sha.value,
            self.fingerprint.value,
        )


def compute_trader_version_fingerprint(
    *,
    trader_code: DemoTradingTraderCode,
    version: DemoTradingTraderVersion,
    config_fingerprint: DemoTradingConfigFingerprint,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    methodology_fingerprint: DemoTradingMethodologyFingerprint,
    software_sha: TraderHistorySoftwareSha,
) -> TraderVersionFingerprint:
    """Hash the exact Trader version identity (code/version/config/methodology/SHA)."""

    if type(trader_code) is not DemoTradingTraderCode:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires DemoTradingTraderCode"
        )
    if type(version) is not DemoTradingTraderVersion:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires DemoTradingTraderVersion"
        )
    if type(config_fingerprint) is not DemoTradingConfigFingerprint:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires DemoTradingConfigFingerprint"
        )
    if type(methodology_id) is not DemoTradingMethodologyId:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires DemoTradingMethodologyId"
        )
    if type(methodology_version) is not DemoTradingMethodologyVersion:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires DemoTradingMethodologyVersion"
        )
    if type(methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires DemoTradingMethodologyFingerprint"
        )
    if type(software_sha) is not TraderHistorySoftwareSha:
        raise TraderHistoryValidationError(
            "trader version fingerprint requires TraderHistorySoftwareSha"
        )
    canonical = {
        "schema": "qore.trader_history.trader_version.v1",
        "trader_code": trader_code.value,
        "version": version.value,
        "config_fingerprint": config_fingerprint.value,
        "methodology_id": methodology_id.value,
        "methodology_version": methodology_version.value,
        "methodology_fingerprint": methodology_fingerprint.value,
        "software_sha": software_sha.value,
    }
    return TraderVersionFingerprint(sha256(_canonical_json(canonical)).hexdigest())


def build_trader_version_identity(
    *,
    trader_code: DemoTradingTraderCode,
    version: DemoTradingTraderVersion,
    config_fingerprint: DemoTradingConfigFingerprint,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    methodology_fingerprint: DemoTradingMethodologyFingerprint,
    software_sha: TraderHistorySoftwareSha,
) -> TraderVersionIdentity:
    """Build an exact Trader version identity without executing or evaluating."""

    fingerprint = compute_trader_version_fingerprint(
        trader_code=trader_code,
        version=version,
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        software_sha=software_sha,
    )
    return TraderVersionIdentity(
        trader_code=trader_code,
        version=version,
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        software_sha=software_sha,
        fingerprint=fingerprint,
    )


@dataclass(frozen=True, slots=True)
class TraderHistoryStudyId:
    """Immutable identity of one longitudinal study."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TraderHistoryValidationError("study id must be a UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderHistoryStudyVersion:
    """Explicit immutable study version token."""

    value: str

    def __post_init__(self) -> None:
        _validate_token(self.value, field_name="study version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryProducerId:
    """Canonical provenance / producer identity of one study."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="producer id"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryMarketRef:
    """Canonical market/instrument symbol one study scoped itself to."""

    value: str

    def __post_init__(self) -> None:
        _validate_market(self.value, field_name="market ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryTimeframeRef:
    """Canonical timeframe code (e.g. ``h1``, ``m15``, ``d1``)."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="timeframe ref"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistorySessionRef:
    """Canonical session/time-bucket code."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="session ref"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryRegimeRef:
    """Canonical regime/volatility/trend-range condition code."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="regime ref"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryEvidenceRef:
    """Opaque sanitized reference to certified historical evidence."""

    value: str

    def __post_init__(self) -> None:
        _validate_opaque_ref(self.value, field_name="evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryPartitionIdentity:
    """Exact evidence/dataset/partition identity a study consumed.

    ``role`` reuses the canonical research ``SampleRole`` so a holdout
    (``EXTERNAL_VALIDATION``) is semantically exact and can never be relabeled as
    a development/calibration sample.
    """

    partition_id: UUID
    dataset_fingerprint: str
    role: SampleRole

    def __post_init__(self) -> None:
        if type(self.partition_id) is not UUID:
            raise TraderHistoryValidationError("partition id must be a UUID")
        _validate_sha256(self.dataset_fingerprint, field_name="dataset fingerprint")
        if type(self.role) is not SampleRole:
            raise TraderHistoryValidationError("partition role must be SampleRole")

    def logical_values(self) -> tuple[object, ...]:
        return (str(self.partition_id), self.dataset_fingerprint, self.role.value)


@dataclass(frozen=True, slots=True)
class TraderHistoryHypothesisId:
    """Canonical hypothesis identity token (e.g. ``HYP-VT08-001``)."""

    value: str

    def __post_init__(self) -> None:
        _validate_token(self.value, field_name="hypothesis id")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryMetric:
    """One quantitative claim bound to at least one exact evidence reference.

    A metric with no backing evidence reference is rejected at construction, so an
    unsupported quantitative claim can never reach the certified projection.
    """

    metric_code: str
    value: Decimal
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_code",
            _validate_code(self.metric_code, field_name="metric code"),
        )
        _canonical_decimal(self.value)
        if type(self.evidence_refs) is not tuple or not self.evidence_refs:
            raise TraderHistoryValidationError(
                "quantitative metric requires non-empty backing evidence refs"
            )
        if any(
            type(item) is not TraderHistoryEvidenceRef for item in self.evidence_refs
        ):
            raise TraderHistoryValidationError(
                "metric evidence refs must be TraderHistoryEvidenceRef"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise TraderHistoryValidationError(
                "metric evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_code,
            _canonical_decimal(self.value),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class TraderHistoryFinding:
    """One typed finding/diagnosis bound to exact evidence references."""

    finding_code: str
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "finding_code",
            _validate_code(self.finding_code, field_name="finding code"),
        )
        if type(self.evidence_refs) is not tuple or not self.evidence_refs:
            raise TraderHistoryValidationError(
                "finding requires non-empty backing evidence refs"
            )
        if any(
            type(item) is not TraderHistoryEvidenceRef for item in self.evidence_refs
        ):
            raise TraderHistoryValidationError(
                "finding evidence refs must be TraderHistoryEvidenceRef"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise TraderHistoryValidationError(
                "finding evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.finding_code,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class TraderHistoryStudyFingerprint:
    """Canonical SHA-256 digest of the complete study record."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="study fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderHistoryCertification:
    """Sealed certification envelope: authority kind/id, subject, issuance time.

    A study is ``CERTIFIED`` only when it carries exactly one certification
    envelope whose authority kind exactly owns the study kind, whose
    ``issued_at`` is not before ``produced_at``, and whose subject binding exactly
    matches the study identity (``study_id`` + ``study_version``). The envelope is
    hashed into the study fingerprint, so it can never be detached, reassigned,
    or forged without invalidating the record.

    ``CERTIFIED`` is never caller assertion: the envelope binds an exact
    ``authority_id`` (a UUID), the exact study identity it certifies, and is
    sealed with an ``_issued`` marker that no in-repo constructor can set. Only an
    owning authority OUTSIDE this module (or a trusted test double) can mint a
    certification, so a caller cannot forge an authority-backed certification for
    a study, nor replay an issued envelope onto a different study.
    """

    authority_kind: TraderHistoryAuthorityKind
    authority_id: UUID
    issued_at: datetime
    study_id: TraderHistoryStudyId
    study_version: TraderHistoryStudyVersion
    _issued: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self._issued is not True:
            raise TraderHistoryValidationError(
                "certification must be issued by an owning authority"
            )
        if type(self.authority_kind) is not TraderHistoryAuthorityKind:
            raise TraderHistoryValidationError(
                "certification authority kind must be TraderHistoryAuthorityKind"
            )
        if type(self.authority_id) is not UUID:
            raise TraderHistoryValidationError(
                "certification authority id must be a UUID"
            )
        if type(self.study_id) is not TraderHistoryStudyId:
            raise TraderHistoryValidationError(
                "certification study id must be TraderHistoryStudyId"
            )
        if type(self.study_version) is not TraderHistoryStudyVersion:
            raise TraderHistoryValidationError(
                "certification study version must be TraderHistoryStudyVersion"
            )
        _validate_timestamp(self.issued_at, field_name="certification issued_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.authority_kind.value,
            str(self.authority_id),
            _utc_iso(self.issued_at, field_name="certification issued_at"),
            str(self.study_id.value),
            self.study_version.value,
        )


@dataclass(frozen=True, slots=True)
class TraderHistoryLedgerRoot:
    """Canonical SHA-256 digest of the complete append-only ledger.

    A reconstructed (possibly truncated) ledger is authenticated only against an
    authoritative external root; a self-consistent truncated ledger can never
    authenticate itself.
    """

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="ledger root")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_trader_identity_family(trader_code: DemoTradingTraderCode) -> str:
    """Return the single canonical CIBO decision-evaluator family for a Trader code.

    This is the one identity convention shared by the Registry, the Trader Lab
    and the CIBO capability path (``vt-08`` -> ``virtual.trader.vt08``). No
    caller may assert a divergent family (e.g. ``qore.trader.*``).
    """

    if type(trader_code) is not DemoTradingTraderCode:
        raise TraderHistoryValidationError(
            "trader identity family requires DemoTradingTraderCode"
        )
    return "virtual.trader." + trader_code.value.replace("-", "")


def _canonical_markets(
    values: tuple[TraderHistoryMarketRef, ...],
) -> tuple[TraderHistoryMarketRef, ...]:
    if type(values) is not tuple or not values:
        raise TraderHistoryValidationError(
            "market scope must be a non-empty immutable market tuple"
        )
    if any(type(item) is not TraderHistoryMarketRef for item in values):
        raise TraderHistoryValidationError(
            "market scope must contain TraderHistoryMarketRef"
        )
    for item in values:
        item.__post_init__()
    if len(set(values)) != len(values):
        raise TraderHistoryValidationError("market scope must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _canonical_timeframes(
    values: tuple[TraderHistoryTimeframeRef, ...],
) -> tuple[TraderHistoryTimeframeRef, ...]:
    if type(values) is not tuple or not values:
        raise TraderHistoryValidationError(
            "timeframe scope must be a non-empty immutable timeframe tuple"
        )
    if any(type(item) is not TraderHistoryTimeframeRef for item in values):
        raise TraderHistoryValidationError(
            "timeframe scope must contain TraderHistoryTimeframeRef"
        )
    for item in values:
        item.__post_init__()
    if len(set(values)) != len(values):
        raise TraderHistoryValidationError(
            "timeframe scope must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


def _canonical_partitions(
    values: tuple[TraderHistoryPartitionIdentity, ...],
) -> tuple[TraderHistoryPartitionIdentity, ...]:
    if type(values) is not tuple or any(
        type(item) is not TraderHistoryPartitionIdentity for item in values
    ):
        raise TraderHistoryValidationError(
            "partitions must be an immutable TraderHistoryPartitionIdentity tuple"
        )
    for item in values:
        item.__post_init__()
    if len(set(values)) != len(values):
        raise TraderHistoryValidationError("partitions must not contain duplicates")
    dataset_fingerprints = [item.dataset_fingerprint for item in values]
    if len(set(dataset_fingerprints)) != len(dataset_fingerprints):
        raise TraderHistoryValidationError(
            "partitions must not contain duplicate dataset fingerprints within one study"
        )
    return tuple(sorted(values, key=lambda item: str(item.partition_id)))


def _canonical_metrics(
    values: tuple[TraderHistoryMetric, ...],
) -> tuple[TraderHistoryMetric, ...]:
    if type(values) is not tuple or any(
        type(item) is not TraderHistoryMetric for item in values
    ):
        raise TraderHistoryValidationError(
            "quantitative claims must be an immutable TraderHistoryMetric tuple"
        )
    for item in values:
        item.__post_init__()
    codes = tuple(item.metric_code for item in values)
    if len(set(codes)) != len(codes):
        raise TraderHistoryValidationError("metric codes must be unique")
    return tuple(sorted(values, key=lambda item: item.metric_code))


def _canonical_findings(
    values: tuple[TraderHistoryFinding, ...],
) -> tuple[TraderHistoryFinding, ...]:
    if type(values) is not tuple or any(
        type(item) is not TraderHistoryFinding for item in values
    ):
        raise TraderHistoryValidationError(
            "findings must be an immutable TraderHistoryFinding tuple"
        )
    for item in values:
        item.__post_init__()
    codes = tuple(item.finding_code for item in values)
    if len(set(codes)) != len(codes):
        raise TraderHistoryValidationError("finding codes must be unique")
    return tuple(sorted(values, key=lambda item: item.finding_code))


def _canonical_evidence_refs(
    values: tuple[TraderHistoryEvidenceRef, ...],
) -> tuple[TraderHistoryEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(item) is not TraderHistoryEvidenceRef for item in values
    ):
        raise TraderHistoryValidationError(
            "evidence refs must be an immutable TraderHistoryEvidenceRef tuple"
        )
    for item in values:
        item.__post_init__()
    if len(set(values)) != len(values):
        raise TraderHistoryValidationError("evidence refs must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _canonical_limitations(values: tuple[str, ...]) -> tuple[str, ...]:
    if type(values) is not tuple or any(
        type(item) is not str or not item for item in values
    ):
        raise TraderHistoryValidationError(
            "limitations must be an immutable non-empty-str tuple"
        )
    normalized = tuple(_validate_code(item, field_name="limitation") for item in values)
    if len(set(normalized)) != len(normalized):
        raise TraderHistoryValidationError("limitations must not contain duplicates")
    return tuple(sorted(normalized))


def _canonical_study_ids(
    values: tuple[TraderHistoryStudyId, ...],
) -> tuple[TraderHistoryStudyId, ...]:
    if type(values) is not tuple or any(
        type(item) is not TraderHistoryStudyId for item in values
    ):
        raise TraderHistoryValidationError(
            "supersedes must be an immutable TraderHistoryStudyId tuple"
        )
    for item in values:
        item.__post_init__()
    if len(set(values)) != len(values):
        raise TraderHistoryValidationError("supersedes must not contain duplicates")
    return tuple(sorted(values, key=lambda item: str(item.value)))


def compute_study_fingerprint(
    *,
    study_id: TraderHistoryStudyId,
    study_version: TraderHistoryStudyVersion,
    trader_version: TraderVersionIdentity,
    kind: TraderHistoryStudyKind,
    epistemic_status: TraderHistoryEpistemicStatus,
    sufficiency: TraderHistorySufficiency,
    produced_at: datetime,
    producer: TraderHistoryProducerId,
    certification: TraderHistoryCertification | None,
    market_scope: tuple[TraderHistoryMarketRef, ...],
    timeframe_scope: tuple[TraderHistoryTimeframeRef, ...],
    partitions: tuple[TraderHistoryPartitionIdentity, ...],
    side: TraderHistorySide | None,
    session: TraderHistorySessionRef | None,
    regime: TraderHistoryRegimeRef | None,
    condition: TraderHistoryFavorableKind | None,
    quantitative_claims: tuple[TraderHistoryMetric, ...],
    findings: tuple[TraderHistoryFinding, ...],
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...],
    hypothesis_id: TraderHistoryHypothesisId | None,
    parent_study: TraderHistoryStudyId | None,
    supersedes: tuple[TraderHistoryStudyId, ...],
    limitations: tuple[str, ...],
) -> TraderHistoryStudyFingerprint:
    """Hash the complete logical content of one study record."""

    if type(study_id) is not TraderHistoryStudyId:
        raise TraderHistoryValidationError("study_id must be TraderHistoryStudyId")
    if type(study_version) is not TraderHistoryStudyVersion:
        raise TraderHistoryValidationError(
            "study_version must be TraderHistoryStudyVersion"
        )
    if type(trader_version) is not TraderVersionIdentity:
        raise TraderHistoryValidationError(
            "trader_version must be TraderVersionIdentity"
        )
    if type(kind) is not TraderHistoryStudyKind:
        raise TraderHistoryValidationError("kind must be TraderHistoryStudyKind")
    if type(epistemic_status) is not TraderHistoryEpistemicStatus:
        raise TraderHistoryValidationError(
            "epistemic_status must be TraderHistoryEpistemicStatus"
        )
    if type(sufficiency) is not TraderHistorySufficiency:
        raise TraderHistoryValidationError(
            "sufficiency must be TraderHistorySufficiency"
        )
    _validate_timestamp(produced_at, field_name="study produced_at")
    if type(producer) is not TraderHistoryProducerId:
        raise TraderHistoryValidationError("producer must be TraderHistoryProducerId")
    if certification is not None and type(
        certification
    ) is not TraderHistoryCertification:
        raise TraderHistoryValidationError(
            "certification must be TraderHistoryCertification or None"
        )
    if side is not None and type(side) is not TraderHistorySide:
        raise TraderHistoryValidationError("side must be TraderHistorySide or None")
    if session is not None and type(session) is not TraderHistorySessionRef:
        raise TraderHistoryValidationError(
            "session must be TraderHistorySessionRef or None"
        )
    if regime is not None and type(regime) is not TraderHistoryRegimeRef:
        raise TraderHistoryValidationError(
            "regime must be TraderHistoryRegimeRef or None"
        )
    if condition is not None and type(condition) is not TraderHistoryFavorableKind:
        raise TraderHistoryValidationError(
            "condition must be TraderHistoryFavorableKind or None"
        )
    if hypothesis_id is not None and type(
        hypothesis_id
    ) is not TraderHistoryHypothesisId:
        raise TraderHistoryValidationError(
            "hypothesis_id must be TraderHistoryHypothesisId or None"
        )
    if parent_study is not None and type(parent_study) is not TraderHistoryStudyId:
        raise TraderHistoryValidationError(
            "parent_study must be TraderHistoryStudyId or None"
        )

    canonical = {
        "schema": "qore.trader_history.study.v1",
        "study_id": str(study_id.value),
        "study_version": study_version.value,
        "trader_version_fingerprint": trader_version.fingerprint.value,
        "kind": kind.value,
        "epistemic_status": epistemic_status.value,
        "sufficiency": sufficiency.value,
        "produced_at": _utc_iso(produced_at, field_name="study produced_at"),
        "producer": producer.value,
        "certification": None
        if certification is None
        else list(certification.logical_values()),
        "market_scope": [item.value for item in _canonical_markets(market_scope)],
        "timeframe_scope": [
            item.value for item in _canonical_timeframes(timeframe_scope)
        ],
        "partitions": [
            list(item.logical_values()) for item in _canonical_partitions(partitions)
        ],
        "side": None if side is None else side.value,
        "session": None if session is None else session.value,
        "regime": None if regime is None else regime.value,
        "condition": None if condition is None else condition.value,
        "quantitative_claims": [
            list(item.logical_values())
            for item in _canonical_metrics(quantitative_claims)
        ],
        "findings": [list(item.logical_values()) for item in _canonical_findings(findings)],
        "evidence_refs": [
            item.value for item in _canonical_evidence_refs(evidence_refs)
        ],
        "hypothesis_id": None if hypothesis_id is None else hypothesis_id.value,
        "parent_study": None if parent_study is None else str(parent_study.value),
        "supersedes": [str(item.value) for item in _canonical_study_ids(supersedes)],
        "limitations": list(_canonical_limitations(limitations)),
    }
    return TraderHistoryStudyFingerprint(sha256(_canonical_json(canonical)).hexdigest())


_KIND_STATUS: dict[TraderHistoryStudyKind, TraderHistoryEpistemicStatus] = {
    TraderHistoryStudyKind.HYPOTHESIS: TraderHistoryEpistemicStatus.HYPOTHESIS,
    TraderHistoryStudyKind.HYPOTHESIS_FALSIFICATION: TraderHistoryEpistemicStatus.FALSIFIED,
    TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION: TraderHistoryEpistemicStatus.CERTIFIED,
}


@dataclass(frozen=True, slots=True)
class TraderHistoryStudyRecord:
    """Immutable, canonically ordered, fingerprinted longitudinal study record.

    A study binds one exact Trader version, one study identity/version, an exact
    market/timeframe scope, explicit timezone-aware timestamps, provenance, kind,
    epistemic status, sufficiency, consumed partitions, quantitative claims,
    findings, and hypothesis lineage. Duplicate logical identities with
    contradictory payloads fail closed (see ``registry.append_study``).
    """

    study_id: TraderHistoryStudyId
    study_version: TraderHistoryStudyVersion
    trader_version: TraderVersionIdentity
    kind: TraderHistoryStudyKind
    epistemic_status: TraderHistoryEpistemicStatus
    sufficiency: TraderHistorySufficiency
    produced_at: datetime
    producer: TraderHistoryProducerId
    market_scope: tuple[TraderHistoryMarketRef, ...]
    timeframe_scope: tuple[TraderHistoryTimeframeRef, ...]
    fingerprint: TraderHistoryStudyFingerprint
    certification: TraderHistoryCertification | None = None
    partitions: tuple[TraderHistoryPartitionIdentity, ...] = ()
    side: TraderHistorySide | None = None
    session: TraderHistorySessionRef | None = None
    regime: TraderHistoryRegimeRef | None = None
    condition: TraderHistoryFavorableKind | None = None
    quantitative_claims: tuple[TraderHistoryMetric, ...] = ()
    findings: tuple[TraderHistoryFinding, ...] = ()
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...] = ()
    hypothesis_id: TraderHistoryHypothesisId | None = None
    parent_study: TraderHistoryStudyId | None = None
    supersedes: tuple[TraderHistoryStudyId, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_study_record_invariants(self)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.study_id.logical_values(),
            self.study_version.logical_values(),
            self.trader_version.logical_values(),
            self.kind.value,
            self.epistemic_status.value,
            self.sufficiency.value,
            _utc_iso(self.produced_at, field_name="study produced_at"),
            self.producer.logical_values(),
            None if self.certification is None else self.certification.logical_values(),
            tuple(item.logical_values() for item in self.market_scope),
            tuple(item.logical_values() for item in self.timeframe_scope),
            tuple(item.logical_values() for item in self.partitions),
            None if self.side is None else self.side.value,
            None if self.session is None else self.session.logical_values(),
            None if self.regime is None else self.regime.logical_values(),
            None if self.condition is None else self.condition.value,
            tuple(item.logical_values() for item in self.quantitative_claims),
            tuple(item.logical_values() for item in self.findings),
            tuple(item.logical_values() for item in self.evidence_refs),
            None if self.hypothesis_id is None else self.hypothesis_id.logical_values(),
            None if self.parent_study is None else self.parent_study.logical_values(),
            tuple(item.logical_values() for item in self.supersedes),
            self.limitations,
            self.fingerprint.logical_values(),
        )


def _validate_study_record_invariants(record: TraderHistoryStudyRecord) -> None:
    """Validate every invariant of one study record (construction + revalidation)."""

    if type(record.study_id) is not TraderHistoryStudyId:
        raise TraderHistoryValidationError("study_id must be TraderHistoryStudyId")
    if type(record.study_version) is not TraderHistoryStudyVersion:
        raise TraderHistoryValidationError(
            "study_version must be TraderHistoryStudyVersion"
        )
    if type(record.trader_version) is not TraderVersionIdentity:
        raise TraderHistoryValidationError(
            "trader_version must be TraderVersionIdentity"
        )
    TraderVersionIdentity.__post_init__(record.trader_version)
    if type(record.kind) is not TraderHistoryStudyKind:
        raise TraderHistoryValidationError("kind must be TraderHistoryStudyKind")
    if type(record.epistemic_status) is not TraderHistoryEpistemicStatus:
        raise TraderHistoryValidationError(
            "epistemic_status must be TraderHistoryEpistemicStatus"
        )
    if type(record.sufficiency) is not TraderHistorySufficiency:
        raise TraderHistoryValidationError(
            "sufficiency must be TraderHistorySufficiency"
        )
    _validate_timestamp(record.produced_at, field_name="study produced_at")
    if type(record.producer) is not TraderHistoryProducerId:
        raise TraderHistoryValidationError("producer must be TraderHistoryProducerId")
    if type(record.fingerprint) is not TraderHistoryStudyFingerprint:
        raise TraderHistoryValidationError(
            "fingerprint must be TraderHistoryStudyFingerprint"
        )
    if record.certification is not None and type(
        record.certification
    ) is not TraderHistoryCertification:
        raise TraderHistoryValidationError(
            "certification must be TraderHistoryCertification or None"
        )
    if record.certification is not None:
        TraderHistoryCertification.__post_init__(record.certification)
        if (
            record.certification.study_id != record.study_id
            or record.certification.study_version != record.study_version
        ):
            raise TraderHistoryValidationError(
                "certification must bind the exact study identity"
            )

    object.__setattr__(record, "market_scope", _canonical_markets(record.market_scope))
    object.__setattr__(
        record, "timeframe_scope", _canonical_timeframes(record.timeframe_scope)
    )
    object.__setattr__(record, "partitions", _canonical_partitions(record.partitions))
    object.__setattr__(
        record,
        "quantitative_claims",
        _canonical_metrics(record.quantitative_claims),
    )
    object.__setattr__(record, "findings", _canonical_findings(record.findings))
    object.__setattr__(
        record, "evidence_refs", _canonical_evidence_refs(record.evidence_refs)
    )
    object.__setattr__(
        record, "supersedes", _canonical_study_ids(record.supersedes)
    )
    object.__setattr__(
        record, "limitations", _canonical_limitations(record.limitations)
    )

    if record.side is not None and type(record.side) is not TraderHistorySide:
        raise TraderHistoryValidationError("side must be TraderHistorySide or None")
    if record.session is not None and type(record.session) is not TraderHistorySessionRef:
        raise TraderHistoryValidationError(
            "session must be TraderHistorySessionRef or None"
        )
    if record.regime is not None and type(record.regime) is not TraderHistoryRegimeRef:
        raise TraderHistoryValidationError(
            "regime must be TraderHistoryRegimeRef or None"
        )
    if record.condition is not None and type(
        record.condition
    ) is not TraderHistoryFavorableKind:
        raise TraderHistoryValidationError(
            "condition must be TraderHistoryFavorableKind or None"
        )
    if record.hypothesis_id is not None and type(
        record.hypothesis_id
    ) is not TraderHistoryHypothesisId:
        raise TraderHistoryValidationError(
            "hypothesis_id must be TraderHistoryHypothesisId or None"
        )
    if record.parent_study is not None and type(
        record.parent_study
    ) is not TraderHistoryStudyId:
        raise TraderHistoryValidationError(
            "parent_study must be TraderHistoryStudyId or None"
        )

    # Epistemic coherence: a study kind whose semantics are fixed must carry the
    # matching status; a HYPOTHESIS can never be constructed as a certified fact.
    expected_status = _KIND_STATUS.get(record.kind)
    if expected_status is not None and record.epistemic_status is not expected_status:
        raise TraderHistoryValidationError(
            f"{record.kind.value} study must carry {expected_status.value} status"
        )
    if record.epistemic_status is TraderHistoryEpistemicStatus.CERTIFIED:
        if record.sufficiency is not TraderHistorySufficiency.SUFFICIENT:
            raise TraderHistoryValidationError(
                "certified study requires sufficient sample/evidence"
            )
        if record.quantitative_claims and not record.partitions:
            raise TraderHistoryValidationError(
                "certified quantitative claims require at least one partition identity"
            )
        # CERTIFIED is never caller assertion: it requires a sealed certification
        # envelope whose authority kind exactly owns the study kind and whose
        # issuance is not before the study was produced.
        if record.certification is None:
            raise TraderHistoryValidationError(
                "certified study requires a certification envelope"
            )
        if record.certification.issued_at < record.produced_at:
            raise TraderHistoryValidationError(
                "certification issued_at cannot predate study produced_at"
            )
        expected_authority = _KIND_AUTHORITY.get(record.kind)
        if expected_authority is not None and (
            record.certification.authority_kind is not expected_authority
        ):
            raise TraderHistoryValidationError(
                f"{record.kind.value} study requires {expected_authority.value} "
                "certification authority"
            )
    elif record.certification is not None:
        raise TraderHistoryValidationError(
            "non-certified study must not carry a certification envelope"
        )
    # Reverse kind->status coherence: a kind-specific epistemic status can never
    # launder onto an unrelated study kind.
    if (
        record.epistemic_status is TraderHistoryEpistemicStatus.HYPOTHESIS
        and record.kind is not TraderHistoryStudyKind.HYPOTHESIS
    ):
        raise TraderHistoryValidationError(
            "hypothesis status requires a hypothesis study kind"
        )
    if (
        record.epistemic_status is TraderHistoryEpistemicStatus.FALSIFIED
        and record.kind is not TraderHistoryStudyKind.HYPOTHESIS_FALSIFICATION
    ):
        raise TraderHistoryValidationError(
            "falsified status requires a hypothesis-falsification study kind"
        )
    if record.epistemic_status is TraderHistoryEpistemicStatus.INSUFFICIENT_EVIDENCE:
        if record.sufficiency is not TraderHistorySufficiency.INSUFFICIENT:
            raise TraderHistoryValidationError(
                "insufficient-evidence study requires insufficient sufficiency"
            )
    if record.kind is TraderHistoryStudyKind.FAILURE_ANALYSIS:
        if record.epistemic_status is not TraderHistoryEpistemicStatus.INFERRED:
            raise TraderHistoryValidationError(
                "failure analysis must be a diagnostic (inferred) study"
            )
    if record.kind is TraderHistoryStudyKind.CHARACTERIZATION:
        if record.epistemic_status not in (
            TraderHistoryEpistemicStatus.OBSERVED,
            TraderHistoryEpistemicStatus.INFERRED,
        ):
            raise TraderHistoryValidationError(
                "characterization must be descriptive/diagnostic"
            )
    if record.kind is TraderHistoryStudyKind.HYPOTHESIS:
        if record.hypothesis_id is None:
            raise TraderHistoryValidationError(
                "hypothesis study requires a hypothesis id token"
            )
    if record.kind in (
        TraderHistoryStudyKind.HYPOTHESIS_FALSIFICATION,
        TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
    ):
        if record.hypothesis_id is None or record.parent_study is None:
            raise TraderHistoryValidationError(
                "hypothesis confirmation/falsification requires hypothesis lineage"
            )
    # Out-of-sample stages can never be laundered from development/calibration
    # data: a study that projects an out-of-sample CIBO stage (OOS, walk-forward,
    # or independent validation) must consume a held-out external-validation
    # partition, otherwise its CIBO stage label is fabricated.
    if record.kind in (
        TraderHistoryStudyKind.OOS,
        TraderHistoryStudyKind.WALK_FORWARD,
        TraderHistoryStudyKind.INDEPENDENT_VALIDATION,
    ):
        if not any(
            partition.role is SampleRole.EXTERNAL_VALIDATION
            for partition in record.partitions
        ):
            raise TraderHistoryValidationError(
                f"{record.kind.value} study requires an external-validation "
                "holdout partition"
            )

    # A quantitative claim can only be an observation, diagnosis, or certified
    # fact; never a hypothesis, falsified claim, or insufficient-evidence claim.
    if record.quantitative_claims and record.epistemic_status not in (
        TraderHistoryEpistemicStatus.OBSERVED,
        TraderHistoryEpistemicStatus.INFERRED,
        TraderHistoryEpistemicStatus.CERTIFIED,
    ):
        raise TraderHistoryValidationError(
            "quantitative claims require observed/inferred/certified status"
        )

    expected = compute_study_fingerprint(
        study_id=record.study_id,
        study_version=record.study_version,
        trader_version=record.trader_version,
        kind=record.kind,
        epistemic_status=record.epistemic_status,
        sufficiency=record.sufficiency,
        produced_at=record.produced_at,
        producer=record.producer,
        certification=record.certification,
        market_scope=record.market_scope,
        timeframe_scope=record.timeframe_scope,
        partitions=record.partitions,
        side=record.side,
        session=record.session,
        regime=record.regime,
        condition=record.condition,
        quantitative_claims=record.quantitative_claims,
        findings=record.findings,
        evidence_refs=record.evidence_refs,
        hypothesis_id=record.hypothesis_id,
        parent_study=record.parent_study,
        supersedes=record.supersedes,
        limitations=record.limitations,
    )
    if record.fingerprint != expected:
        raise TraderHistoryValidationError(
            "study fingerprint must match the exact record"
        )


def validate_study_record(record: TraderHistoryStudyRecord) -> None:
    """Re-validate a study record at a trust boundary."""

    if type(record) is not TraderHistoryStudyRecord:
        raise TraderHistoryValidationError("record must be TraderHistoryStudyRecord")
    _validate_study_record_invariants(record)


def build_study_record(
    *,
    study_id: TraderHistoryStudyId,
    study_version: TraderHistoryStudyVersion,
    trader_version: TraderVersionIdentity,
    kind: TraderHistoryStudyKind,
    epistemic_status: TraderHistoryEpistemicStatus,
    sufficiency: TraderHistorySufficiency,
    produced_at: datetime,
    producer: TraderHistoryProducerId,
    market_scope: tuple[TraderHistoryMarketRef, ...],
    timeframe_scope: tuple[TraderHistoryTimeframeRef, ...],
    certification: TraderHistoryCertification | None = None,
    partitions: tuple[TraderHistoryPartitionIdentity, ...] = (),
    side: TraderHistorySide | None = None,
    session: TraderHistorySessionRef | None = None,
    regime: TraderHistoryRegimeRef | None = None,
    condition: TraderHistoryFavorableKind | None = None,
    quantitative_claims: tuple[TraderHistoryMetric, ...] = (),
    findings: tuple[TraderHistoryFinding, ...] = (),
    evidence_refs: tuple[TraderHistoryEvidenceRef, ...] = (),
    hypothesis_id: TraderHistoryHypothesisId | None = None,
    parent_study: TraderHistoryStudyId | None = None,
    supersedes: tuple[TraderHistoryStudyId, ...] = (),
    limitations: tuple[str, ...] = (),
) -> TraderHistoryStudyRecord:
    """Build an immutable study record without executing or evaluating anything."""

    fingerprint = compute_study_fingerprint(
        study_id=study_id,
        study_version=study_version,
        trader_version=trader_version,
        kind=kind,
        epistemic_status=epistemic_status,
        sufficiency=sufficiency,
        produced_at=produced_at,
        producer=producer,
        certification=certification,
        market_scope=market_scope,
        timeframe_scope=timeframe_scope,
        partitions=partitions,
        side=side,
        session=session,
        regime=regime,
        condition=condition,
        quantitative_claims=quantitative_claims,
        findings=findings,
        evidence_refs=evidence_refs,
        hypothesis_id=hypothesis_id,
        parent_study=parent_study,
        supersedes=supersedes,
        limitations=limitations,
    )
    return TraderHistoryStudyRecord(
        study_id=study_id,
        study_version=study_version,
        trader_version=trader_version,
        kind=kind,
        epistemic_status=epistemic_status,
        sufficiency=sufficiency,
        produced_at=produced_at,
        producer=producer,
        market_scope=market_scope,
        timeframe_scope=timeframe_scope,
        fingerprint=fingerprint,
        certification=certification,
        partitions=partitions,
        side=side,
        session=session,
        regime=regime,
        condition=condition,
        quantitative_claims=quantitative_claims,
        findings=findings,
        evidence_refs=evidence_refs,
        hypothesis_id=hypothesis_id,
        parent_study=parent_study,
        supersedes=supersedes,
        limitations=limitations,
    )
