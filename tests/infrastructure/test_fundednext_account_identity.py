from __future__ import annotations

import pytest

from qore.infrastructure.fundednext_account_identity import (
    fundednext_mt5_account_fingerprint,
)


def _fingerprint(login: int) -> str:
    return fundednext_mt5_account_fingerprint(
        login=login,
        server="FundedNext-Server",
        company="FundedNext",
        currency="USD",
        leverage=100,
    )


def test_fingerprint_is_deterministic_and_account_unique() -> None:
    first = _fingerprint(123456)
    assert first == _fingerprint(123456)
    assert first != _fingerprint(654321)
    assert len(first) == 64
    assert first == first.lower()


def test_fingerprint_rejects_invalid_identity_inputs() -> None:
    with pytest.raises(ValueError, match="login"):
        _fingerprint(0)
    with pytest.raises(ValueError, match="server"):
        fundednext_mt5_account_fingerprint(
            login=123456,
            server="",
            company="FundedNext",
            currency="USD",
            leverage=100,
        )
    with pytest.raises(ValueError, match="leverage"):
        fundednext_mt5_account_fingerprint(
            login=123456,
            server="FundedNext-Server",
            company="FundedNext",
            currency="USD",
            leverage=0,
        )
