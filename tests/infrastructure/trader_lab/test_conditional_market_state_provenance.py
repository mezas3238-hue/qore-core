from __future__ import annotations

import pytest

from qore.infrastructure.trader_lab.conditional_market_state_analytics import (
    ConditionalMarketStateAnalyticsError,
    _analytics_software_sha,
)


def test_analytics_software_sha_is_optional_for_library_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QORE_ANALYTICS_SOFTWARE_SHA", raising=False)
    assert _analytics_software_sha() is None


def test_analytics_software_sha_binds_exact_git_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "a" * 40
    monkeypatch.setenv("QORE_ANALYTICS_SOFTWARE_SHA", expected)
    assert _analytics_software_sha() == expected


def test_analytics_software_sha_rejects_non_git_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QORE_ANALYTICS_SOFTWARE_SHA", "not-a-git-sha")
    with pytest.raises(ConditionalMarketStateAnalyticsError, match="40-character"):
        _analytics_software_sha()
