from __future__ import annotations

from dataclasses import fields
from inspect import getsource
from typing import get_type_hints

import qore.infrastructure.instrument_universe_registry as registry
from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode


def test_registry_reuses_umi02_family_authority_instead_of_defining_taxonomy() -> None:
    assert get_type_hints(registry.InstrumentUniverseEntry)["family"] is IdentityFamilyCode
    source = getsource(registry)
    assert "class IdentityFamilyCode" not in source
    assert "class AssetClass" not in source
    assert "class InstrumentTaxonomy" not in source


def test_registry_has_no_provider_execution_valuation_risk_or_settlement_authority_fields() -> None:
    field_names = {
        field.name
        for cls in (
            registry.InstrumentUniverseEvidenceRecord,
            registry.InstrumentUniverseEntry,
            registry.InstrumentUniverseRegistrySnapshot,
        )
        for field in fields(cls)
    }
    prohibited = {
        "provider_symbol",
        "provider_id",
        "provider_supported",
        "platform_supported",
        "execution_supported",
        "route",
        "routing",
        "order",
        "execution",
        "valuation_method",
        "valuation_model",
        "risk_limit",
        "margin",
        "capacity",
        "settlement_instruction",
        "settlement_status",
    }
    assert field_names.isdisjoint(prohibited)


def test_registry_status_model_does_not_contain_support_state() -> None:
    status_values = {status.value for status in registry.InstrumentUniverseCoverageStatus}
    status_names = {status.name for status in registry.InstrumentUniverseCoverageStatus}
    assert "supported" not in status_values
    assert "SUPPORTED" not in status_names


def test_registry_module_contains_no_implicit_time_identity_or_side_effect_mechanism() -> None:
    source = getsource(registry).lower()
    prohibited_fragments = (
        "datetime.now",
        "date.today",
        "uuid4",
        "time.sleep",
        "asyncio.sleep",
        "threading",
        "subprocess",
        "requests.",
        "httpx.",
        "urllib.",
        "socket.",
        "sqlalchemy",
        "sqlite",
        "psycopg",
        "pymongo",
        "redis.",
    )
    for fragment in prohibited_fragments:
        assert fragment not in source


def test_registry_module_has_no_provider_package_dependency() -> None:
    source = getsource(registry)
    assert "qore.providers" not in source
    assert "qore.infrastructure.oanda" not in source
    assert "qore.infrastructure.ctrader" not in source
    assert "qore.infrastructure.execution" not in source


def test_registry_exposes_logical_material_but_no_hash_as_evidence_substitute() -> None:
    assert hasattr(registry.InstrumentUniverseEntry, "logical_values")
    assert hasattr(registry.InstrumentUniverseRegistrySnapshot, "logical_values")
    assert not hasattr(registry.InstrumentUniverseRegistrySnapshot, "fingerprint")
    assert not hasattr(registry.InstrumentUniverseRegistrySnapshot, "digest")
