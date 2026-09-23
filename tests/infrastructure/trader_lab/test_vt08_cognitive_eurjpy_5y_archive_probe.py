from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_eurjpy_5y_archive_probe import (
    ARCHIVE_LOOKBACK_DAYS,
    ARCHIVE_SYMBOL,
    MIN_ARCHIVE_SPAN_DAYS,
    REQUIRED_PERIODS,
    validate_five_year_coverage,
)


def _payload(first: datetime, last: datetime) -> dict[str, object]:
    coverage = {
        period: {
            "first_opened_at": first.isoformat(),
            "last_closed_at": last.isoformat(),
        }
        for period in REQUIRED_PERIODS
    }
    return {
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "symbol": {"symbol_name": ARCHIVE_SYMBOL},
        "coverage": coverage,
    }


def test_five_year_archive_contract_is_strict() -> None:
    assert ARCHIVE_LOOKBACK_DAYS == 1825
    assert MIN_ARCHIVE_SPAN_DAYS == 1815


def test_short_archive_fails_closed() -> None:
    checked = datetime(2026, 9, 23, tzinfo=UTC)
    requested = checked - timedelta(days=1825)
    with pytest.raises(ValueError):
        validate_five_year_coverage(
            _payload(requested, requested + timedelta(days=1000)),
            requested_opened_at=requested,
            checked_at=checked,
        )
