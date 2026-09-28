from __future__ import annotations

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiPermissionScope,
    ctrader_permission_scope_matches,
)


def test_view_scope_requires_exact_read_only_provider_scope() -> None:
    assert ctrader_permission_scope_matches(
        0,
        CTraderOpenApiPermissionScope.VIEW,
    )
    assert not ctrader_permission_scope_matches(
        1,
        CTraderOpenApiPermissionScope.VIEW,
    )


def test_trade_scope_requires_exact_trading_provider_scope() -> None:
    assert ctrader_permission_scope_matches(
        1,
        CTraderOpenApiPermissionScope.TRADE,
    )
    assert not ctrader_permission_scope_matches(
        0,
        CTraderOpenApiPermissionScope.TRADE,
    )


def test_permission_scope_rejects_bool_and_unknown_values() -> None:
    assert not ctrader_permission_scope_matches(
        True,
        CTraderOpenApiPermissionScope.TRADE,
    )
    assert not ctrader_permission_scope_matches(
        2,
        CTraderOpenApiPermissionScope.TRADE,
    )
