"""Shared deterministic DEMO Trader identity/config/methodology/state contracts.

This module is the provider-neutral foundation for the first five specialized
DEMO Traders (VT-01, VT-08, VT-09, VT-17, VT-31). It owns exact, versioned,
evidence-bound Trader identity so that ``MARKET EVIDENCE -> EXACT TRADER
VERSION/CONFIG/METHODOLOGY -> SETUP / STATE / ABSTAIN`` is deterministic and
replayable.

Every value object is immutable and carries a ``logical_values()`` projection
so a caller can derive a reproducible logical identity. No value object here
carries an order, account, quantity, provider instruction, Risk approval, or
Production/real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.kernel.errors import InfrastructureError

_CODE_RE = r"[a-z][a-z0-9._-]*"
_TRADER_CODE_RE = r"vt-(?:0[1-9]|[12][0-9]|3[01])"
_VERSION_TOKEN_RE = r"[A-Za-z0-9][A-Za-z0-9._/+:-]*"
_SHA256_HEX_RE = r"[0-9a-f]{64}"
_EVIDENCE_REF_RE = r"[a-z][a-z0-9._:/-]*"


class DemoTradingError(InfrastructureError):
    """Base error for deterministic DEMO Trader contracts."""

    __slots__ = ()


class DemoTradingValidationError(DemoTradingError):
    """Violation of a deterministic DEMO Trader contract invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise DemoTradingValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DemoTradingValidationError(f"{field_name} must be timezone-aware")


def _utc_iso(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_sha256(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_SHA256_HEX_RE, value) is None:
        raise DemoTradingValidationError(
            f"{field_name} must be 64 lowercase hex characters"
        )


def _validate_version_token(value: str, *, field_name: str) -> None:
    if type(value) is not str or fullmatch(_VERSION_TOKEN_RE, value) is None:
        raise DemoTradingValidationError(
            f"{field_name} must use canonical version-token syntax"
        )


def _validate_code(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise DemoTradingValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    return value


def _canonical_decimal(value: Decimal) -> str:
    if type(value) is not Decimal or not value.is_finite():
        raise DemoTradingValidationError("decimal value must be a finite Decimal")
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def _canonical_json(payload: object) -> bytes:
    def _default(value: object) -> str:
        if isinstance(value, Decimal):
            return _canonical_decimal(value)
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat(timespec="microseconds")
        raise TypeError(f"unsupported canonical material: {type(value).__qualname__}")

    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_default,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DemoTradingTraderCode:
    """Canonical catalog Trader code (``vt-01``..``vt-31``)."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or fullmatch(_TRADER_CODE_RE, self.value) is None:
            raise DemoTradingValidationError(
                "trader code must use canonical vt-NN syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DemoTradingTraderVersion:
    """Explicit immutable Trader version token.

    A config/methodology change requires a new version (and therefore a new
    config fingerprint); a terminal Trader Lab rejection cannot resume through
    the same version.
    """

    value: str

    def __post_init__(self) -> None:
        _validate_version_token(self.value, field_name="trader version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DemoTradingConfigFingerprint:
    """Canonical SHA-256 fingerprint of the exact trader config content."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="config fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DemoTradingMethodologyId:
    """Canonical methodology identity code (e.g. ``ny-precision-core``)."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="methodology id"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DemoTradingMethodologyVersion:
    """Explicit immutable methodology version token."""

    value: str

    def __post_init__(self) -> None:
        _validate_version_token(self.value, field_name="methodology version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DemoTradingMethodologyFingerprint:
    """Canonical SHA-256 fingerprint of the frozen methodology semantics."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="methodology fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DemoTradingEvidenceRef:
    """Opaque sanitized reference to exact retained market evidence."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or fullmatch(_EVIDENCE_REF_RE, self.value) is None:
            raise DemoTradingValidationError(
                "evidence ref must use canonical lowercase opaque-ref syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _sorted_evidence_refs(
    values: tuple[DemoTradingEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[DemoTradingEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(item) is not DemoTradingEvidenceRef for item in values
    ):
        raise DemoTradingValidationError(
            f"{field_name} must be an immutable DemoTradingEvidenceRef tuple"
        )
    if len(set(values)) != len(values):
        raise DemoTradingValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


DemoTradingConfigParameterValue = str | bool | int | Decimal


@dataclass(frozen=True, slots=True)
class DemoTradingConfigParameter:
    """One typed immutable trader configuration parameter."""

    name: str
    value: DemoTradingConfigParameterValue

    def __post_init__(self) -> None:
        if type(self.name) is not str or fullmatch(
            r"[a-z][a-z0-9._-]{0,79}", self.name
        ) is None:
            raise DemoTradingValidationError(
                "config parameter name must use canonical lowercase syntax"
            )
        if type(self.value) is bool:
            return
        if type(self.value) is int:
            return
        if isinstance(self.value, Decimal):
            _canonical_decimal(self.value)
            return
        if type(self.value) is str:
            if not self.value:
                raise DemoTradingValidationError(
                    "config string parameter must not be empty"
                )
            return
        raise DemoTradingValidationError(
            "config parameter value must be str, bool, int, or Decimal"
        )

    def canonical_value(self) -> dict[str, object]:
        if type(self.value) is bool:
            return {"type": "bool", "value": self.value}
        if type(self.value) is int:
            return {"type": "int", "value": str(self.value)}
        if isinstance(self.value, Decimal):
            return {"type": "decimal", "value": _canonical_decimal(self.value)}
        if type(self.value) is str:
            return {"type": "str", "value": self.value}
        raise DemoTradingValidationError(
            "config parameter value must be str, bool, int, or Decimal"
        )

    def logical_values(self) -> tuple[object, ...]:
        canonical = self.canonical_value()
        return (self.name, canonical["type"], canonical["value"])


def _canonical_parameters(
    parameters: tuple[DemoTradingConfigParameter, ...],
) -> tuple[DemoTradingConfigParameter, ...]:
    if type(parameters) is not tuple or any(
        type(item) is not DemoTradingConfigParameter for item in parameters
    ):
        raise DemoTradingValidationError(
            "config parameters must be an immutable DemoTradingConfigParameter tuple"
        )
    for item in parameters:
        # Re-enter validation so a reflectively corrupted retained parameter
        # (e.g. a float smuggled in after construction) fails closed instead of
        # being silently hashed into the config fingerprint.
        item.__post_init__()
    names = tuple(item.name for item in parameters)
    if len(set(names)) != len(names):
        raise DemoTradingValidationError("config parameter names must be unique")
    return tuple(sorted(parameters, key=lambda item: item.name))


def compute_trader_config_fingerprint(
    *,
    schema_version: str,
    parameters: tuple[DemoTradingConfigParameter, ...],
) -> DemoTradingConfigFingerprint:
    """Hash exact configuration content (schema + parameters), not identity/time."""

    if type(schema_version) is not str or fullmatch(
        _VERSION_TOKEN_RE, schema_version
    ) is None:
        raise DemoTradingValidationError(
            "config schema_version must use canonical version-token syntax"
        )
    ordered = _canonical_parameters(parameters)
    canonical = {
        "schema": "qore.trader.config.v1",
        "schema_version": schema_version,
        "parameters": [
            {"name": item.name, **item.canonical_value()} for item in ordered
        ],
    }
    return DemoTradingConfigFingerprint(sha256(_canonical_json(canonical)).hexdigest())


def compute_trader_methodology_fingerprint(
    *,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    timeframe: str,
    session: str,
    ruleset: str,
) -> DemoTradingMethodologyFingerprint:
    """Hash the frozen methodology identity and semantics (not process time)."""

    if type(methodology_id) is not DemoTradingMethodologyId:
        raise DemoTradingValidationError(
            "methodology fingerprint requires DemoTradingMethodologyId"
        )
    if type(methodology_version) is not DemoTradingMethodologyVersion:
        raise DemoTradingValidationError(
            "methodology fingerprint requires DemoTradingMethodologyVersion"
        )
    if type(timeframe) is not str or not timeframe:
        raise DemoTradingValidationError("methodology timeframe must be non-empty str")
    if type(session) is not str or not session:
        raise DemoTradingValidationError("methodology session must be non-empty str")
    if type(ruleset) is not str or not ruleset:
        raise DemoTradingValidationError("methodology ruleset must be non-empty str")
    canonical = {
        "schema": "qore.trader.methodology.v1",
        "methodology_id": methodology_id.value,
        "methodology_version": methodology_version.value,
        "timeframe": timeframe,
        "session": session,
        "ruleset": ruleset,
    }
    return DemoTradingMethodologyFingerprint(
        sha256(_canonical_json(canonical)).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class DemoTradingTraderIdentity:
    """Immutable exact Trader identity: code + version + config fingerprint."""

    trader_code: DemoTradingTraderCode
    version: DemoTradingTraderVersion
    config_fingerprint: DemoTradingConfigFingerprint

    def __post_init__(self) -> None:
        if type(self.trader_code) is not DemoTradingTraderCode:
            raise DemoTradingValidationError(
                "trader identity requires DemoTradingTraderCode"
            )
        if type(self.version) is not DemoTradingTraderVersion:
            raise DemoTradingValidationError(
                "trader identity requires DemoTradingTraderVersion"
            )
        if type(self.config_fingerprint) is not DemoTradingConfigFingerprint:
            raise DemoTradingValidationError(
                "trader identity requires DemoTradingConfigFingerprint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_code.logical_values(),
            self.version.logical_values(),
            self.config_fingerprint.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DemoTradingMethodologyIdentity:
    """Immutable exact methodology identity: id + version + fingerprint."""

    methodology_id: DemoTradingMethodologyId
    version: DemoTradingMethodologyVersion
    fingerprint: DemoTradingMethodologyFingerprint

    def __post_init__(self) -> None:
        if type(self.methodology_id) is not DemoTradingMethodologyId:
            raise DemoTradingValidationError(
                "methodology identity requires DemoTradingMethodologyId"
            )
        if type(self.version) is not DemoTradingMethodologyVersion:
            raise DemoTradingValidationError(
                "methodology identity requires DemoTradingMethodologyVersion"
            )
        if type(self.fingerprint) is not DemoTradingMethodologyFingerprint:
            raise DemoTradingValidationError(
                "methodology identity requires DemoTradingMethodologyFingerprint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.methodology_id.logical_values(),
            self.version.logical_values(),
            self.fingerprint.logical_values(),
        )


class DemoTradingDecision(StrEnum):
    """Closed deterministic decision: a setup exists or the trader abstains."""

    SETUP = "setup"
    ABSTAIN = "abstain"


class DemoTradingSetupSide(StrEnum):
    """Deterministic setup direction; never a quantity or provider action."""

    LONG = "long"
    SHORT = "short"


class DemoTradingAbstainReason(StrEnum):
    """Explicit deterministic abstain reasons; abstention is never silent."""

    NO_SESSION = "no-session"
    WINDOW_CLOSED = "window-closed"
    NO_SWEEP = "no-sweep"
    NO_FALSE_BREAK = "no-false-break"
    NO_FVG = "no-fvg"
    NO_STRUCTURE = "no-structure"
    NO_CYCLE = "no-cycle"
    PARTIAL_CANDLE = "partial-candle"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    INVERSION_MISSING = "inversion-missing"


@dataclass(frozen=True, slots=True)
class DemoTradingSetupSpec:
    """Deterministic setup outcome: side, entry reference, invalidation, exit."""

    side: DemoTradingSetupSide
    entry_price: Decimal
    invalidation_price: Decimal
    take_profit_price: Decimal
    entry_reason: str

    def __post_init__(self) -> None:
        if type(self.side) is not DemoTradingSetupSide:
            raise DemoTradingValidationError(
                "setup side must be DemoTradingSetupSide"
            )
        entry = self.entry_price
        invalidation = self.invalidation_price
        take_profit = self.take_profit_price
        for name, value in (
            ("entry_price", entry),
            ("invalidation_price", invalidation),
            ("take_profit_price", take_profit),
        ):
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                raise DemoTradingValidationError(f"setup {name} must be positive Decimal")
        if self.side is DemoTradingSetupSide.LONG:
            if not invalidation < entry < take_profit:
                raise DemoTradingValidationError(
                    "long setup requires invalidation < entry < take-profit"
                )
        elif not take_profit < entry < invalidation:
            raise DemoTradingValidationError(
                "short setup requires take-profit < entry < invalidation"
            )
        if type(self.entry_reason) is not str or not self.entry_reason.strip():
            raise DemoTradingValidationError("setup entry_reason must be non-empty")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.side.value,
            _canonical_decimal(self.entry_price),
            _canonical_decimal(self.invalidation_price),
            _canonical_decimal(self.take_profit_price),
            self.entry_reason,
        )


@dataclass(frozen=True, slots=True)
class DemoTradingOutput:
    """Deterministic, versioned, evidence-bound Trader output.

    Binds exact trader identity, methodology identity, input evidence, timeframe,
    session/window identity, and the deterministic decision (setup or abstain)
    plus explicit invalidation/exit semantics. The ``output_fingerprint`` is the
    reproducible logical identity used for replay: the same trader identity,
    methodology identity, evidence refs, decision, and evaluated-at timestamp
    reproduce the same logical output.
    """

    trader_code: DemoTradingTraderCode
    version: DemoTradingTraderVersion
    config_fingerprint: DemoTradingConfigFingerprint
    methodology_id: DemoTradingMethodologyId
    methodology_version: DemoTradingMethodologyVersion
    methodology_fingerprint: DemoTradingMethodologyFingerprint
    evidence_refs: tuple[DemoTradingEvidenceRef, ...]
    timeframe: str
    session: str
    decision: DemoTradingDecision
    side: DemoTradingSetupSide | None
    setup: DemoTradingSetupSpec | None
    abstain_reason: DemoTradingAbstainReason | None
    evaluated_at: datetime
    output_fingerprint: DemoTradingConfigFingerprint

    def __post_init__(self) -> None:
        if type(self.trader_code) is not DemoTradingTraderCode:
            raise DemoTradingValidationError("output requires DemoTradingTraderCode")
        if type(self.version) is not DemoTradingTraderVersion:
            raise DemoTradingValidationError("output requires DemoTradingTraderVersion")
        if type(self.config_fingerprint) is not DemoTradingConfigFingerprint:
            raise DemoTradingValidationError(
                "output requires DemoTradingConfigFingerprint"
            )
        if type(self.methodology_id) is not DemoTradingMethodologyId:
            raise DemoTradingValidationError("output requires DemoTradingMethodologyId")
        if type(self.methodology_version) is not DemoTradingMethodologyVersion:
            raise DemoTradingValidationError(
                "output requires DemoTradingMethodologyVersion"
            )
        if type(self.methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
            raise DemoTradingValidationError(
                "output requires DemoTradingMethodologyFingerprint"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _sorted_evidence_refs(self.evidence_refs, field_name="output evidence refs"),
        )
        if type(self.timeframe) is not str or not self.timeframe:
            raise DemoTradingValidationError("output timeframe must be non-empty str")
        if type(self.session) is not str or not self.session:
            raise DemoTradingValidationError("output session must be non-empty str")
        if type(self.decision) is not DemoTradingDecision:
            raise DemoTradingValidationError("output decision must be DemoTradingDecision")
        _validate_timestamp(self.evaluated_at, field_name="output evaluated_at")
        if self.decision is DemoTradingDecision.SETUP:
            if type(self.side) is not DemoTradingSetupSide:
                raise DemoTradingValidationError("setup output requires a side")
            if type(self.setup) is not DemoTradingSetupSpec:
                raise DemoTradingValidationError("setup output requires DemoTradingSetupSpec")
            if self.setup.side is not self.side:
                raise DemoTradingValidationError("setup side must match output side")
            if self.abstain_reason is not None:
                raise DemoTradingValidationError("setup output must not carry abstain reason")
        else:
            if self.side is not None or self.setup is not None:
                raise DemoTradingValidationError("abstain output must not carry a setup")
            if type(self.abstain_reason) is not DemoTradingAbstainReason:
                raise DemoTradingValidationError(
                    "abstain output requires DemoTradingAbstainReason"
                )
        if type(self.output_fingerprint) is not DemoTradingConfigFingerprint:
            raise DemoTradingValidationError(
                "output requires a DemoTradingConfigFingerprint logical identity"
            )
        expected = compute_trader_output_fingerprint(
            trader_code=self.trader_code,
            version=self.version,
            config_fingerprint=self.config_fingerprint,
            methodology_id=self.methodology_id,
            methodology_version=self.methodology_version,
            methodology_fingerprint=self.methodology_fingerprint,
            evidence_refs=self.evidence_refs,
            timeframe=self.timeframe,
            session=self.session,
            decision=self.decision,
            side=self.side,
            setup=self.setup,
            abstain_reason=self.abstain_reason,
            evaluated_at=self.evaluated_at,
        )
        if self.output_fingerprint != expected:
            raise DemoTradingValidationError(
                "output fingerprint must match the exact retained output"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_code.logical_values(),
            self.version.logical_values(),
            self.config_fingerprint.logical_values(),
            self.methodology_id.logical_values(),
            self.methodology_version.logical_values(),
            self.methodology_fingerprint.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
            self.timeframe,
            self.session,
            self.decision.value,
            None if self.side is None else self.side.value,
            None if self.setup is None else self.setup.logical_values(),
            None if self.abstain_reason is None else self.abstain_reason.value,
            _utc_iso(self.evaluated_at, field_name="output evaluated_at"),
            self.output_fingerprint.logical_values(),
        )


def compute_trader_output_fingerprint(
    *,
    trader_code: DemoTradingTraderCode,
    version: DemoTradingTraderVersion,
    config_fingerprint: DemoTradingConfigFingerprint,
    methodology_id: DemoTradingMethodologyId,
    methodology_version: DemoTradingMethodologyVersion,
    methodology_fingerprint: DemoTradingMethodologyFingerprint,
    evidence_refs: tuple[DemoTradingEvidenceRef, ...],
    timeframe: str,
    session: str,
    decision: DemoTradingDecision,
    side: DemoTradingSetupSide | None,
    setup: DemoTradingSetupSpec | None,
    abstain_reason: DemoTradingAbstainReason | None,
    evaluated_at: datetime,
) -> DemoTradingConfigFingerprint:
    """Derive the reproducible logical identity of one deterministic output."""

    if type(trader_code) is not DemoTradingTraderCode:
        raise DemoTradingValidationError("output fingerprint requires DemoTradingTraderCode")
    if type(version) is not DemoTradingTraderVersion:
        raise DemoTradingValidationError("output fingerprint requires DemoTradingTraderVersion")
    if type(config_fingerprint) is not DemoTradingConfigFingerprint:
        raise DemoTradingValidationError(
            "output fingerprint requires DemoTradingConfigFingerprint"
        )
    if type(methodology_id) is not DemoTradingMethodologyId:
        raise DemoTradingValidationError(
            "output fingerprint requires DemoTradingMethodologyId"
        )
    if type(methodology_version) is not DemoTradingMethodologyVersion:
        raise DemoTradingValidationError(
            "output fingerprint requires DemoTradingMethodologyVersion"
        )
    if type(methodology_fingerprint) is not DemoTradingMethodologyFingerprint:
        raise DemoTradingValidationError(
            "output fingerprint requires DemoTradingMethodologyFingerprint"
        )
    ordered_refs = _sorted_evidence_refs(evidence_refs, field_name="output evidence refs")
    if type(timeframe) is not str or not timeframe:
        raise DemoTradingValidationError("output fingerprint requires non-empty timeframe")
    if type(session) is not str or not session:
        raise DemoTradingValidationError("output fingerprint requires non-empty session")
    if type(decision) is not DemoTradingDecision:
        raise DemoTradingValidationError("output fingerprint requires DemoTradingDecision")
    if decision is DemoTradingDecision.SETUP:
        if type(side) is not DemoTradingSetupSide:
            raise DemoTradingValidationError(
                "setup output fingerprint requires DemoTradingSetupSide"
            )
        if type(setup) is not DemoTradingSetupSpec:
            raise DemoTradingValidationError(
                "setup output fingerprint requires DemoTradingSetupSpec"
            )
        if setup.side is not side:
            raise DemoTradingValidationError(
                "setup side must match the output side"
            )
        if abstain_reason is not None:
            raise DemoTradingValidationError(
                "setup output fingerprint must not carry an abstain reason"
            )
    else:
        if side is not None or setup is not None:
            raise DemoTradingValidationError(
                "abstain output fingerprint must not carry a side or setup"
            )
        if type(abstain_reason) is not DemoTradingAbstainReason:
            raise DemoTradingValidationError(
                "abstain output fingerprint requires DemoTradingAbstainReason"
            )
    _validate_timestamp(evaluated_at, field_name="output fingerprint evaluated_at")
    canonical: dict[str, object] = {
        "schema": "qore.trader.output.v1",
        "trader_code": trader_code.value,
        "version": version.value,
        "config_fingerprint": config_fingerprint.value,
        "methodology_id": methodology_id.value,
        "methodology_version": methodology_version.value,
        "methodology_fingerprint": methodology_fingerprint.value,
        "evidence_refs": [item.value for item in ordered_refs],
        "timeframe": timeframe,
        "session": session,
        "decision": decision.value,
        "side": None if side is None else side.value,
        "setup": None if setup is None else list(setup.logical_values()),
        "abstain_reason": None if abstain_reason is None else abstain_reason.value,
        "evaluated_at": _utc_iso(evaluated_at, field_name="output evaluated_at"),
    }
    return DemoTradingConfigFingerprint(sha256(_canonical_json(canonical)).hexdigest())
