"""Fail-closed cTrader metadata-only message firewall for Shared GEN-2."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
    CTraderOpenApiMessageClientBoundary,
)
from qore.kernel.result import Failure, Result, Success

_METADATA_READ_ONLY_MESSAGES = frozenset(
    {
        "ProtoOAAssetListReq",
        "ProtoOAAssetClassListReq",
        "ProtoOASymbolByIdReq",
        "ProtoOASymbolCategoryListReq",
        "ProtoOASymbolsListReq",
    }
)


class CTraderMetadataReadOnlyClientError(CTraderOpenApiClientError):
    """GEN-2 metadata firewall rejected a non-observation operation."""


class CTraderMetadataReadOnlyMessageClient:
    """Admit only finite account-scoped metadata reads required by Shared GEN-2."""

    __slots__ = ("_client",)

    def __init__(self, client: CTraderOpenApiMessageClientBoundary) -> None:
        self._client = client

    @property
    def is_ready(self) -> bool:
        return self._client.is_ready

    @property
    def account_id(self) -> int:
        return self._client.account_id

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]:
        return self._client.connect_and_authenticate()

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        if message_name not in _METADATA_READ_ONLY_MESSAGES:
            return Failure(
                CTraderMetadataReadOnlyClientError(
                    "GEN-2 metadata client rejected non-read-only provider message"
                )
            )
        result = self._client.request(
            message_name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=timeout_seconds,
        )
        if isinstance(result, Failure):
            return Failure(result.error)
        return Success(result.value)

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        del message_name, timeout_seconds, predicate
        return Failure(
            CTraderMetadataReadOnlyClientError(
                "GEN-2 metadata client does not admit provider subscriptions"
            )
        )

    def close(self) -> None:
        self._client.close()
