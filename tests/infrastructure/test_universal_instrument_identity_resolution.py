from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.universal_instrument_identity import (
    CanonicalIdentityRef,
    EconomicIdentityId,
    ExternalIdentifier,
    ExternalIdentifierKind,
    ExternalIdentifierNamespace,
    ExternalIdentifierValue,
    ExternalIdentityMappingRevision,
    IdentityEvidenceRef,
    IdentityMappingHistory,
    IdentityMappingId,
    IdentityMappingRevision,
    UniversalInstrumentIdentityValidationError,
)
from qore.infrastructure.universal_instrument_identity_resolution import (
    IdentityMappingResolutionError,
    resolve_identity_mapping_revision,
)

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = datetime(2026, 2, 1, tzinfo=UTC)
_T2 = datetime(2026, 3, 1, tzinfo=UTC)
_T3 = datetime(2026, 4, 1, tzinfo=UTC)
_PLUS_THREE = timezone(timedelta(hours=3))


def _u(value: int) -> UUID:
    return UUID(int=value)


def _external() -> ExternalIdentifier:
    return ExternalIdentifier(
        kind=ExternalIdentifierKind.LEGACY_QORE,
        namespace=ExternalIdentifierNamespace("legacy.symbol"),
        value=ExternalIdentifierValue("EURUSD"),
    )


def _revision(
    *,
    mapping_id: IdentityMappingId,
    number: int,
    external: ExternalIdentifier,
    target: int,
    effective_from: datetime,
    effective_until: datetime | None,
    recorded_at: datetime,
) -> ExternalIdentityMappingRevision:
    return ExternalIdentityMappingRevision(
        mapping_id=mapping_id,
        revision=IdentityMappingRevision(number),
        parent_revision=IdentityMappingRevision(number - 1) if number > 1 else None,
        external_identity=external,
        target=CanonicalIdentityRef(EconomicIdentityId(_u(target))),
        effective_from=effective_from,
        effective_until=effective_until,
        recorded_at=recorded_at,
        evidence_ref=IdentityEvidenceRef(_u(10_000 + number)),
    )


def _overlapping_history() -> tuple[
    IdentityMappingHistory,
    ExternalIdentityMappingRevision,
    ExternalIdentityMappingRevision,
]:
    mapping_id = IdentityMappingId(_u(1_000))
    external = _external()
    first = _revision(
        mapping_id=mapping_id,
        number=1,
        external=external,
        target=101,
        effective_from=_T0,
        effective_until=None,
        recorded_at=_T0,
    )
    second = _revision(
        mapping_id=mapping_id,
        number=2,
        external=external,
        target=102,
        effective_from=_T1,
        effective_until=None,
        recorded_at=_T2,
    )
    return IdentityMappingHistory((first, second)), first, second


def test_resolution_requires_validated_history_and_explicit_aware_instants() -> None:
    history, _, _ = _overlapping_history()

    with pytest.raises(UniversalInstrumentIdentityValidationError, match="history"):
        resolve_identity_mapping_revision(
            cast(IdentityMappingHistory, "bad"),
            effective_at=_T1,
            known_at=_T2,
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="effective_at"):
        resolve_identity_mapping_revision(
            history,
            effective_at=datetime(2026, 2, 1),
            known_at=_T2,
        )
    with pytest.raises(UniversalInstrumentIdentityValidationError, match="known_at"):
        resolve_identity_mapping_revision(
            history,
            effective_at=_T1,
            known_at=datetime(2026, 3, 1),
        )


def test_resolution_uses_half_open_effective_interval() -> None:
    mapping_id = IdentityMappingId(_u(2_000))
    external = _external()
    revision = _revision(
        mapping_id=mapping_id,
        number=1,
        external=external,
        target=201,
        effective_from=_T0,
        effective_until=_T1,
        recorded_at=_T0,
    )
    history = IdentityMappingHistory((revision,))

    assert (
        resolve_identity_mapping_revision(
            history,
            effective_at=_T0,
            known_at=_T0,
        )
        == revision
    )
    with pytest.raises(IdentityMappingResolutionError):
        resolve_identity_mapping_revision(
            history,
            effective_at=_T1,
            known_at=_T1,
        )


def test_latest_revision_property_is_not_historical_currentness() -> None:
    history, first, second = _overlapping_history()

    assert history.latest_revision == second
    assert (
        resolve_identity_mapping_revision(
            history,
            effective_at=_T1,
            known_at=_T1,
        )
        == first
    )


def test_latest_known_effective_revision_has_overlap_precedence() -> None:
    history, _, second = _overlapping_history()

    assert (
        resolve_identity_mapping_revision(
            history,
            effective_at=_T1,
            known_at=_T2,
        )
        == second
    )


def test_backfilled_revision_does_not_rewrite_historical_replay() -> None:
    mapping_id = IdentityMappingId(_u(3_000))
    external = _external()
    first = _revision(
        mapping_id=mapping_id,
        number=1,
        external=external,
        target=301,
        effective_from=_T0,
        effective_until=None,
        recorded_at=_T0,
    )
    backfill = _revision(
        mapping_id=mapping_id,
        number=2,
        external=external,
        target=302,
        effective_from=_T0,
        effective_until=_T1,
        recorded_at=_T2,
    )
    history = IdentityMappingHistory((first, backfill))

    assert (
        resolve_identity_mapping_revision(
            history,
            effective_at=_T0,
            known_at=_T1,
        )
        == first
    )
    assert (
        resolve_identity_mapping_revision(
            history,
            effective_at=_T0,
            known_at=_T2,
        )
        == backfill
    )


def test_older_revision_remains_applicable_outside_later_effective_window() -> None:
    mapping_id = IdentityMappingId(_u(4_000))
    external = _external()
    first = _revision(
        mapping_id=mapping_id,
        number=1,
        external=external,
        target=401,
        effective_from=_T0,
        effective_until=None,
        recorded_at=_T0,
    )
    bounded_override = _revision(
        mapping_id=mapping_id,
        number=2,
        external=external,
        target=402,
        effective_from=_T1,
        effective_until=_T2,
        recorded_at=_T2,
    )
    history = IdentityMappingHistory((first, bounded_override))

    assert (
        resolve_identity_mapping_revision(
            history,
            effective_at=_T3,
            known_at=_T3,
        )
        == first
    )


def test_resolution_fails_closed_when_no_known_revision_is_applicable() -> None:
    history, _, _ = _overlapping_history()

    with pytest.raises(IdentityMappingResolutionError):
        resolve_identity_mapping_revision(
            history,
            effective_at=_T0,
            known_at=_T0 - timedelta(microseconds=1),
        )


def test_resolution_treats_timezone_equivalent_instants_identically() -> None:
    history, _, second = _overlapping_history()

    resolved = resolve_identity_mapping_revision(
        history,
        effective_at=_T1.astimezone(_PLUS_THREE),
        known_at=_T2.astimezone(_PLUS_THREE),
    )
    assert resolved == second
