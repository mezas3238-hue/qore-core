from __future__ import annotations

from datetime import datetime

from qore.infrastructure.universal_instrument_identity import (
    ExternalIdentityMappingRevision,
    IdentityMappingHistory,
    UniversalInstrumentIdentityError,
    UniversalInstrumentIdentityValidationError,
)


class IdentityMappingResolutionError(UniversalInstrumentIdentityError):
    """No governed mapping revision can be resolved for the requested view."""

    __slots__ = ()


def _validate_resolution_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise UniversalInstrumentIdentityValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise UniversalInstrumentIdentityValidationError(
            f"{field_name} must be timezone-aware"
        )


def resolve_identity_mapping_revision(
    history: IdentityMappingHistory,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> ExternalIdentityMappingRevision:
    """Resolve one reproducible mapping revision from a retained linear history.

    ``effective_at`` selects the economic interval being interpreted while
    ``known_at`` fixes the information cutoff for historical replay. Among
    revisions that were already recorded and whose half-open effective interval
    contains ``effective_at``, the highest retained revision has precedence.
    No wall clock, provider lookup, or caller-supplied precedence is consulted.
    """

    if not isinstance(history, IdentityMappingHistory):
        raise UniversalInstrumentIdentityValidationError(
            "identity mapping resolution history must be IdentityMappingHistory"
        )
    _validate_resolution_timestamp(effective_at, field_name="mapping resolution effective_at")
    _validate_resolution_timestamp(known_at, field_name="mapping resolution known_at")

    resolved: ExternalIdentityMappingRevision | None = None
    for revision in history.revisions:
        if revision.recorded_at > known_at:
            break
        if revision.effective_from > effective_at:
            continue
        if revision.effective_until is not None and effective_at >= revision.effective_until:
            continue
        resolved = revision

    if resolved is None:
        raise IdentityMappingResolutionError(
            "no identity mapping revision is effective within the requested knowledge cutoff"
        )
    return resolved
