from __future__ import annotations

from types import SimpleNamespace

from qore.infrastructure.ctrader_metadata_read_only import (
    CTraderMetadataReadOnlyClientError,
    CTraderMetadataReadOnlyMessageClient,
)
from qore.kernel.result import Failure, Success


class _FakeClient:
    def __init__(self) -> None:
        self.is_ready = True
        self.account_id = 123
        self.calls: list[str] = []
        self.closed = False

    def connect_and_authenticate(self):
        return Success(None)

    def request(
        self,
        message_name: str,
        fields: object,
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        del fields, client_msg_id, timeout_seconds
        self.calls.append(message_name)
        return Success(SimpleNamespace(message_name=message_name))

    def wait_for_event(self, *args: object, **kwargs: object):
        del args, kwargs
        raise AssertionError("metadata wrapper must never delegate subscriptions")

    def close(self) -> None:
        self.closed = True


def test_metadata_firewall_admits_only_finite_read_requests() -> None:
    native = _FakeClient()
    client = CTraderMetadataReadOnlyMessageClient(native)  # type: ignore[arg-type]

    allowed = (
        "ProtoOAAssetListReq",
        "ProtoOAAssetClassListReq",
        "ProtoOASymbolByIdReq",
        "ProtoOASymbolCategoryListReq",
        "ProtoOASymbolsListReq",
    )
    for index, message_name in enumerate(allowed):
        result = client.request(
            message_name,
            {"ctidTraderAccountId": 123},
            client_msg_id=f"metadata-{index}",
            timeout_seconds=1.0,
        )
        assert isinstance(result, Success)

    assert native.calls == list(allowed)


def test_metadata_firewall_rejects_order_and_subscription_shapes() -> None:
    native = _FakeClient()
    client = CTraderMetadataReadOnlyMessageClient(native)  # type: ignore[arg-type]

    order = client.request(
        "ProtoOANewOrderReq",
        {"ctidTraderAccountId": 123},
        client_msg_id="forbidden-order",
        timeout_seconds=1.0,
    )
    subscription = client.wait_for_event(
        "ProtoOASpotEvent",
        timeout_seconds=1.0,
    )

    assert isinstance(order, Failure)
    assert isinstance(order.error, CTraderMetadataReadOnlyClientError)
    assert isinstance(subscription, Failure)
    assert isinstance(
        subscription.error,
        CTraderMetadataReadOnlyClientError,
    )
    assert native.calls == []
