from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID

import pytest

from qore.infrastructure.research_lineage_canonical import (
    _canonical_attrs,
    _canonical_state_content,
    _state_tagged,
    _utc_iso,
    canonical_strategy_configuration_manifest,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageCanonicalValueError,
)
from qore.infrastructure.research_run import ResearchStrategyConfigurationId
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyConfigurationDigest,
    ResearchStrategyConfigurationManifest,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    compute_research_strategy_configuration_digest,
)


def test_utc_iso_normalizes_offset_with_microseconds() -> None:
    value = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        123456,
        tzinfo=timezone(timedelta(hours=5)),
    )
    assert _utc_iso(value) == "2026-01-01T07:00:00.123456+00:00"


def test_utc_iso_rejects_naive_datetime() -> None:
    with pytest.raises(ResearchLineageCanonicalValueError):
        _utc_iso(datetime(2026, 1, 1, 12, 0))


def test_metadata_canonicalization_preserves_scalar_type_identity() -> None:
    identity = UUID("12345678-1234-5678-1234-567812345678")
    values = MappingProxyType(
        {
            "uuid": identity,
            "text": str(identity),
            "float": 1.0,
            "float_text": (1.0).hex(),
            "bool": True,
            "int": 1,
        }
    )
    projected = _canonical_attrs(values)
    assert projected["uuid"] != projected["text"]
    assert projected["float"] != projected["float_text"]
    assert projected["bool"] != projected["int"]


def test_state_tagged_preserves_uuid_datetime_bool_int_and_tuple_identity() -> None:
    identity = UUID("12345678-1234-5678-1234-567812345678")
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert _state_tagged(identity) != _state_tagged(str(identity))
    assert _state_tagged(instant) != _state_tagged(_utc_iso(instant))
    assert _state_tagged(True) != _state_tagged(1)
    nested = _state_tagged((1, True, "x", identity))
    assert nested["type"] == "tuple"
    assert [item["type"] for item in nested["items"]] == [
        "int",
        "bool",
        "str",
        "uuid",
    ]


def test_state_content_requires_mapping_with_string_keys() -> None:
    with pytest.raises(ResearchLineageCanonicalValueError):
        _canonical_state_content({1: "bad"})
    projected = _canonical_state_content({"x": 1})
    assert projected["schema"] == "qore.research-state-content-tagged.v1"
    assert projected["content"]["x"] == {"type": "int", "value": "1"}


def _strategy_manifest(value: Decimal) -> ResearchStrategyConfigurationManifest:
    schema = ResearchStrategySchemaVersion("v1")
    parameters = (ResearchStrategyParameter(name="alpha", value=value),)
    digest = compute_research_strategy_configuration_digest(
        schema_version=schema,
        parameters=parameters,
    )
    return ResearchStrategyConfigurationManifest(
        configuration_id=ResearchStrategyConfigurationId(
            UUID("55000000-0000-0000-0000-000000000001")
        ),
        schema_version=schema,
        parameters=parameters,
        content_digest=ResearchStrategyConfigurationDigest(digest.value),
        frozen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID("55000000-0000-0000-0000-000000000002")
        ),
    )


def test_strategy_projector_reuses_existing_decimal_canonical_value() -> None:
    one = canonical_strategy_configuration_manifest(
        _strategy_manifest(Decimal("1.0"))
    )
    one_hundredths = canonical_strategy_configuration_manifest(
        _strategy_manifest(Decimal("1.00"))
    )
    negative_zero = canonical_strategy_configuration_manifest(
        _strategy_manifest(Decimal("-0.0"))
    )
    assert one["parameters"][0]["value"] == "1"
    assert one_hundredths["parameters"][0]["value"] == "1"
    assert negative_zero["parameters"][0]["value"] == "0"
