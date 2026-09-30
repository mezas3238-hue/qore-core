from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_provider_evidence_audit import (
    HISTORICAL_PROVIDER_ECONOMIC_FIELDS,
    HistoricalProviderFieldStatus,
    audit_historical_provider_economics_rows,
)


def test_r_denominated_rows_fail_closed_when_provider_economics_absent() -> None:
    audit = audit_historical_provider_economics_rows(
        (
            {
                "economics_status": "R_DENOMINATED_ONLY",
                "entry_price": "1.10",
                "structural_stop": "1.09",
            },
            {
                "economics_status": "R_DENOMINATED_ONLY",
                "entry_price": "1.11",
                "structural_stop": "1.10",
            },
        )
    )

    assert audit.row_count == 2
    assert audit.economics_status_values == ("R_DENOMINATED_ONLY",)
    assert audit.exact_historical_usd_replay_supported is False
    assert set(audit.missing_fields) == set(HISTORICAL_PROVIDER_ECONOMIC_FIELDS)


def test_exact_fields_must_be_present_on_every_bound_row() -> None:
    complete = {
        "economics_status": "PROVIDER_ECONOMICS_COMPLETE",
        **{
            field: Decimal("1")
            for field in HISTORICAL_PROVIDER_ECONOMIC_FIELDS
        },
    }
    incomplete = dict(complete)
    del incomplete["tick_value"]

    audit = audit_historical_provider_economics_rows((complete, incomplete))

    status = dict(audit.field_status)
    assert status["tick_value"] is (
        HistoricalProviderFieldStatus.ABSENT_FROM_BOUND_ROWS
    )
    assert status["bid"] is (
        HistoricalProviderFieldStatus.EXACT_HISTORICAL_PRESENT
    )
    assert audit.exact_historical_usd_replay_supported is False


def test_complete_exact_field_population_can_support_exact_replay_contract() -> None:
    rows = tuple(
        {
            "economics_status": "PROVIDER_ECONOMICS_COMPLETE",
            **{
                field: Decimal(str(index + 1))
                for field in HISTORICAL_PROVIDER_ECONOMIC_FIELDS
            },
        }
        for index in range(2)
    )

    audit = audit_historical_provider_economics_rows(rows)

    assert audit.exact_historical_usd_replay_supported is True
    assert audit.missing_fields == ()


def test_audit_rejects_row_without_explicit_economics_status() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="economics_status",
    ):
        audit_historical_provider_economics_rows(({"entry_price": "1.10"},))
