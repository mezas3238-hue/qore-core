from __future__ import annotations

from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_account_discovery import (
    CTraderDemoAccountDiscoveryError,
    select_single_demo_account_id,
)


def _account(*, account_id: object, is_live: object) -> object:
    return SimpleNamespace(ctidTraderAccountId=account_id, isLive=is_live)


def test_selects_exactly_one_demo_and_ignores_live_accounts() -> None:
    selected = select_single_demo_account_id(
        (
            _account(account_id=11, is_live=True),
            _account(account_id=22, is_live=False),
            _account(account_id=33, is_live=True),
        )
    )

    assert selected == 22


def test_rejects_when_token_has_no_explicit_demo_account() -> None:
    with pytest.raises(
        CTraderDemoAccountDiscoveryError,
        match="exactly one explicitly classified DEMO account",
    ):
        select_single_demo_account_id(
            (
                _account(account_id=11, is_live=True),
                SimpleNamespace(ctidTraderAccountId=22),
            )
        )


def test_rejects_when_token_has_multiple_demo_accounts() -> None:
    with pytest.raises(
        CTraderDemoAccountDiscoveryError,
        match="exactly one explicitly classified DEMO account",
    ):
        select_single_demo_account_id(
            (
                _account(account_id=11, is_live=False),
                _account(account_id=22, is_live=False),
            )
        )


def test_rejects_invalid_internal_demo_account_id() -> None:
    with pytest.raises(
        CTraderDemoAccountDiscoveryError,
        match="positive int",
    ):
        select_single_demo_account_id(
            (_account(account_id=0, is_live=False),)
        )
