from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r90_m1_provider_depth_probe as r90,
)
from qore.kernel.result import Success


class _FakeClient:
    account_id = 123

    def __init__(self) -> None:
        self.fields: dict[str, object] | None = None

    def request(
        self,
        message_name: str,
        fields: dict[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Success[object]:
        assert message_name == "ProtoOAGetTrendbarsReq"
        assert client_msg_id
        assert timeout_seconds == 60.0
        self.fields = fields
        minute = int(
            datetime(2018, 9, 17, 0, 0, tzinfo=UTC).timestamp() // 60
        )
        row = SimpleNamespace(
            utcTimestampInMinutes=minute,
            low=100000,
            deltaOpen=10,
            deltaHigh=20,
            deltaClose=15,
        )
        return Success(SimpleNamespace(trendbar=(row,)))


def test_r90_probe_uses_native_m1_without_count() -> None:
    fake = _FakeClient()
    row = r90._probe_window(
        cast(SpotwareCTraderOpenApiClient, fake),
        canonical_symbol="NAS100",
        provider_symbol="USTEC",
        symbol_id=77,
        opened_at=datetime(2018, 9, 17, 0, 0, tzinfo=UTC),
    )
    assert fake.fields is not None
    assert fake.fields["period"] == 1
    assert "count" not in fake.fields
    assert row.retained_m1_bars == 1
    assert row.m1_available is True
    assert row.provider_payload_valid is True


def test_r90_fixed_probe_dates_span_required_history() -> None:
    assert r90.PROBE_OPENINGS[0] == datetime(
        2016, 9, 19, 0, 0, tzinfo=UTC
    )
    assert r90.PROBE_OPENINGS[1] == datetime(
        2018, 9, 17, 0, 0, tzinfo=UTC
    )
    assert r90.PROBE_OPENINGS[-1] == datetime(
        2026, 9, 14, 0, 0, tzinfo=UTC
    )


def test_r90_scope_is_indices_only_and_native_m1() -> None:
    assert r90.PERIOD_M1 == 1
    assert r90.PROVIDER_SYMBOLS == {
        "NAS100": "USTEC",
        "SP500": "US500",
        "US30": "US30",
    }
