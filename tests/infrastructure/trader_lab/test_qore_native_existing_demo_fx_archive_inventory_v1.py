"""Source-prefix gates: archive is DEMO and only metadata is inspected."""
import json

import pytest

from qore.infrastructure.trader_lab.qore_native_existing_demo_fx_archive_inventory_v1 import (
    SOURCE_SCOPE,
    SYMBOLS,
    build_inventory,
    metadata_prefix,
)


def _fixture(tmp_path, *, live=False, intended=SOURCE_SCOPE):
    source = tmp_path / "raw-7y-base.json"
    payload = {
        "account_discovered": True,
        "account_is_live": live,
        "environment": "demo",
        "intended_future_use": intended,
        "coverage": {
            tf: {
                "bar_count": 100,
                "first_opened_at": "2019-09-27T01:00:00+00:00",
                "last_closed_at": "2026-09-25T00:00:00+00:00",
            } for tf in ("M1", "M5", "M15", "H4")
        },
    }
    head = json.dumps(payload, separators=(",", ":"))[:-1]
    source.write_text(head + ',"periods":{"M5":[{"open":"1","close":"9999"}]}}')
    return source


def test_two_symbols_only() -> None:
    assert SYMBOLS == ("EURJPY", "USDCHF")


def test_existing_archive_metadata_only(tmp_path) -> None:
    src = _fixture(tmp_path)
    assert metadata_prefix(src)["account_is_live"] is False
    result = build_inventory("EURJPY", src)
    assert result["coverage"]["M5"]["bar_count"] == 100
    assert result["cTrader_auth_required_for_reuse"] is False
    assert result["admission_to_new_trader_not_authorized"] is True
    assert result["virgin_oos_claimed"] is False
    assert "9999" not in json.dumps(result)


def test_reject_live(tmp_path) -> None:
    with pytest.raises(ValueError, match="DEMO"):
        build_inventory("USDCHF", _fixture(tmp_path, live=True))


def test_reject_different_reserved_scope(tmp_path) -> None:
    with pytest.raises(ValueError, match="reserved use"):
        build_inventory("USDCHF", _fixture(tmp_path, intended="anything_else"))


def test_reject_other_symbol(tmp_path) -> None:
    with pytest.raises(ValueError, match="EURJPY/USDCHF"):
        build_inventory("EURUSD", _fixture(tmp_path))
