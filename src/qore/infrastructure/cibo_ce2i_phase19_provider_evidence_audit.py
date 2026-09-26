"""Fail-closed audit of historical provider-economics evidence for Phase 19.

The Phase-18 bound-trade ledgers are causal strategy evidence. This module
verifies whether they also retain the broker/provider fields required for an
exact historical USD capital replay. Absence is evidence too: it must be
recorded explicitly rather than repaired with current snapshots or guesses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

HISTORICAL_PROVIDER_ECONOMIC_FIELDS = (
    "bid",
    "ask",
    "spread",
    "spread_points",
    "commission",
    "commission_per_volume_usd",
    "slippage",
    "slippage_reserve_per_volume_usd",
    "margin_per_volume",
    "margin_per_volume_usd",
    "tick_value",
    "contract_size",
    "minimum_volume",
    "maximum_volume",
    "volume_step",
)


class HistoricalProviderFieldStatus(StrEnum):
    EXACT_HISTORICAL_PRESENT = "EXACT_HISTORICAL_PRESENT"
    ABSENT_FROM_BOUND_ROWS = "ABSENT_FROM_BOUND_ROWS"


@dataclass(frozen=True, slots=True)
class HistoricalProviderEconomicsRowAudit:
    row_count: int
    economics_status_values: tuple[str, ...]
    field_status: tuple[tuple[str, HistoricalProviderFieldStatus], ...]
    exact_historical_usd_replay_supported: bool

    def __post_init__(self) -> None:
        if type(self.row_count) is not int or self.row_count <= 0:
            raise CiboCapitalManagementError(
                "provider-economics audit requires positive row_count"
            )
        if not self.economics_status_values:
            raise CiboCapitalManagementError(
                "provider-economics audit requires economics status evidence"
            )
        if self.exact_historical_usd_replay_supported:
            required = {
                field
                for field, status in self.field_status
                if status is HistoricalProviderFieldStatus.EXACT_HISTORICAL_PRESENT
            }
            if set(HISTORICAL_PROVIDER_ECONOMIC_FIELDS) - required:
                raise CiboCapitalManagementError(
                    "exact historical replay cannot be supported with missing fields"
                )

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(
            field
            for field, status in self.field_status
            if status is HistoricalProviderFieldStatus.ABSENT_FROM_BOUND_ROWS
        )


def audit_historical_provider_economics_rows(
    rows: Sequence[Mapping[str, Any]],
) -> HistoricalProviderEconomicsRowAudit:
    """Audit exact provider-economic field retention in bound causal rows.

    A field counts as present only when every row carries a non-null value for
    that exact field. Semantic reconstruction from price bars or a current
    provider snapshot is intentionally out of scope.
    """

    if not rows:
        raise CiboCapitalManagementError(
            "provider-economics audit requires at least one bound row"
        )

    statuses: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise CiboCapitalManagementError(
                "provider-economics audit row must be mapping"
            )
        raw_status = row.get("economics_status")
        if not isinstance(raw_status, str) or not raw_status:
            raise CiboCapitalManagementError(
                "bound row missing explicit economics_status"
            )
        statuses.add(raw_status)

    field_status: list[tuple[str, HistoricalProviderFieldStatus]] = []
    for field in HISTORICAL_PROVIDER_ECONOMIC_FIELDS:
        present_everywhere = all(
            field in row and row[field] is not None for row in rows
        )
        status = (
            HistoricalProviderFieldStatus.EXACT_HISTORICAL_PRESENT
            if present_everywhere
            else HistoricalProviderFieldStatus.ABSENT_FROM_BOUND_ROWS
        )
        field_status.append((field, status))

    exact_supported = all(
        status is HistoricalProviderFieldStatus.EXACT_HISTORICAL_PRESENT
        for _field, status in field_status
    )
    return HistoricalProviderEconomicsRowAudit(
        row_count=len(rows),
        economics_status_values=tuple(sorted(statuses)),
        field_status=tuple(field_status),
        exact_historical_usd_replay_supported=exact_supported,
    )
