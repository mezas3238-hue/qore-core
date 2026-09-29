"""Pure source-only governance for the WP-05 post-V14 provider catalogue."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

POST_V14_PROVIDER_CATALOG_IDENTITY: Final = (
    "QORE_SHARED_WP05_POST_V14_PROVIDER_CATALOG_AUDIT_001"
)


class PostV14ProviderCatalogError(ValueError):
    """The source-only provider catalogue violated its frozen contract."""


@dataclass(frozen=True, slots=True)
class ProviderCatalogEntry:
    provider_symbol_id: int
    provider_symbol: str
    normalized_symbol: str

    def __post_init__(self) -> None:
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise PostV14ProviderCatalogError(
                "provider_symbol_id must be a positive int"
            )
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise PostV14ProviderCatalogError(
                "provider_symbol must be a non-empty trimmed string"
            )
        if (
            not isinstance(self.normalized_symbol, str)
            or not self.normalized_symbol
            or self.normalized_symbol != normalize_provider_symbol(
                self.provider_symbol
            )
        ):
            raise PostV14ProviderCatalogError("normalized_symbol drift")


def normalize_provider_symbol(value: str) -> str:
    """Normalize provider display syntax without inventing semantic identity."""

    if not isinstance(value, str) or not value or value != value.strip():
        raise PostV14ProviderCatalogError(
            "provider symbol must be a non-empty trimmed string"
        )
    normalized = "".join(
        character for character in value.upper() if character.isalnum()
    )
    if not normalized:
        raise PostV14ProviderCatalogError("provider symbol normalized empty")
    return normalized


def freeze_enabled_provider_catalog(
    rows: Sequence[tuple[int, str, bool]],
) -> tuple[ProviderCatalogEntry, ...]:
    """Freeze exact enabled provider identities with no performance selection."""

    if isinstance(rows, (str, bytes)):
        raise PostV14ProviderCatalogError("provider catalogue must be a sequence")

    by_id: dict[int, str] = {}
    by_name: dict[str, int] = {}
    entries: list[ProviderCatalogEntry] = []

    for symbol_id, symbol_name, enabled in rows:
        if type(enabled) is not bool:
            raise PostV14ProviderCatalogError("enabled flag must be bool")
        if not enabled:
            continue
        if type(symbol_id) is not int or symbol_id <= 0:
            raise PostV14ProviderCatalogError(
                "enabled provider symbol id must be positive int"
            )
        normalized = normalize_provider_symbol(symbol_name)

        previous_name = by_id.get(symbol_id)
        if previous_name is not None and previous_name != symbol_name:
            raise PostV14ProviderCatalogError(
                "provider symbol id maps to conflicting names"
            )
        previous_id = by_name.get(symbol_name)
        if previous_id is not None and previous_id != symbol_id:
            raise PostV14ProviderCatalogError(
                "provider symbol name maps to conflicting ids"
            )
        if previous_name is not None:
            continue

        by_id[symbol_id] = symbol_name
        by_name[symbol_name] = symbol_id
        entries.append(
            ProviderCatalogEntry(
                provider_symbol_id=symbol_id,
                provider_symbol=symbol_name,
                normalized_symbol=normalized,
            )
        )

    if not entries:
        raise PostV14ProviderCatalogError("enabled provider catalogue is empty")

    return tuple(
        sorted(
            entries,
            key=lambda item: (
                item.provider_symbol,
                item.provider_symbol_id,
            ),
        )
    )


def provider_catalog_sha256(
    entries: Sequence[ProviderCatalogEntry],
) -> str:
    """Hash the frozen exact provider catalogue deterministically."""

    if not entries:
        raise PostV14ProviderCatalogError("catalogue digest requires entries")
    payload = [
        {
            "provider_symbol_id": item.provider_symbol_id,
            "provider_symbol": item.provider_symbol,
            "normalized_symbol": item.normalized_symbol,
        }
        for item in entries
    ]
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
