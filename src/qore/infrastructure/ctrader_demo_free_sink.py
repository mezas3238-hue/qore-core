"""Operational cTrader DEMO sink for unrestricted Trader/CIBO observation.

This path is DEMO-only. QORE Risk allocates virtual capital by Trader lineage;
Trader/CIBO own setup selection and requested size. No FundedNext portfolio-risk
reduction is applied here.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from uuid import NAMESPACE_URL, uuid5

from qore.domain.events import CorrelationId
from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.ctrader_demo_allocation_only import (
    CTraderDemoBrokerContract,
    DemoCapitalAllocationBook,
    allocation_fence_values,
    authorize_allocation_only,
    build_allocation_only_submission,
    equal_active_trader_allocations,
)
from qore.infrastructure.ctrader_demo_free_binding import (
    CTraderDemoFreeBinding,
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_demo_free_position_service import (
    CTraderDemoFreePositionService,
)
from qore.infrastructure.ctrader_demo_trade_registry import (
    CTraderDemoTradeRegistry,
    DemoTradeRegistryEntry,
)
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    JsonFileCTraderDemoMutationLedger,
)
from qore.infrastructure.ctrader_demo_operational_runtime import (
    CTraderDemoOperationalRuntime,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.market_test_environment import (
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure


class CTraderDemoFreeSinkError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CTraderDemoFreeSubmitResult:
    state: str
    trader_id: TraderLineage
    qore_symbol: str
    requested_volume: Decimal
    assigned_capital: Decimal
    provider_order_ref: str | None
    client_order_id: str | None
    position_id: int | None
    recorded_at: datetime


class CTraderDemoFreeSink:
    __slots__ = (
        "_root",
        "_binding",
        "_book",
        "_client",
        "_runtime",
        "_positions",
        "_registry",
        "_source_contract_sizes",
        "_events",
        "_lock",
    )

    def __init__(
        self,
        *,
        root: Path,
        credentials: CTraderOpenApiCredentials,
        source_contract_sizes: dict[str, Decimal],
    ) -> None:
        if not isinstance(root, Path):
            raise CTraderDemoFreeSinkError("root must be Path")
        if not source_contract_sizes:
            raise CTraderDemoFreeSinkError("source contract sizes are required")
        self._root = root
        self._events = root / "var" / "ctrader_demo_free" / "events.jsonl"
        self._events.parent.mkdir(parents=True, exist_ok=True)
        self._source_contract_sizes = dict(source_contract_sizes)
        self._lock = Lock()

        client = SpotwareCTraderOpenApiClient(credentials=credentials)
        binding = discover_free_account_binding(client)
        if binding.account.account_ref != str(credentials.ctid_trader_account_id):
            client.close()
            raise CTraderDemoFreeSinkError("authenticated cTrader DEMO account mismatch")
        self._binding = binding
        self._book = equal_active_trader_allocations(binding.balance)
        self._client = client

        authorization = MarketTestEnvironmentAuthorization(
            account=binding.account,
            policy_id="qore.ctrader-demo.free-account.v1",
            authorized_at=datetime.now(UTC),
        )
        descriptor = ExternalSourceDescriptor(
            adapter_id=AdapterId(uuid5(NAMESPACE_URL, "qore:ctrader-demo-free:adapter")),
            source_id=SourceId(uuid5(NAMESPACE_URL, "qore:ctrader-demo-free:source")),
            port_name=PortName("market-data.ctrader-demo-free"),
        )
        ledger = JsonFileCTraderDemoMutationLedger(
            root / "var" / "ctrader_demo_free" / "mutations.json"
        )
        self._runtime = CTraderDemoOperationalRuntime(
            configuration=binding.configuration,
            credentials=credentials,
            environment_authorization=authorization,
            market_data_descriptor=descriptor,
            mutation_ledger=ledger,
            client=client,
        )
        self._positions = CTraderDemoFreePositionService(
            client=client,
            configuration=binding.configuration,
        )
        self._registry = CTraderDemoTradeRegistry(
            root / "var" / "ctrader_demo_free" / "trade-registry.json"
        )
        self._log(
            {
                "event": "CTRADER_DEMO_FREE_SINK_STARTED",
                "balance": format(binding.balance, "f"),
                "traders": len(self._book.allocations),
                "symbols": len(binding.contracts),
                "risk_role": "CAPITAL_ALLOCATOR_ONLY",
                "cibo_role": "SIZING_AND_POSITION_INTELLIGENCE_SOVEREIGN",
            }
        )

    @property
    def binding(self) -> CTraderDemoFreeBinding:
        return self._binding

    @property
    def client(self) -> SpotwareCTraderOpenApiClient:
        return self._client

    @property
    def position_service(self) -> CTraderDemoFreePositionService:
        return self._positions

    @property
    def registry(self) -> CTraderDemoTradeRegistry:
        return self._registry

    @property
    def client(self) -> SpotwareCTraderOpenApiClient:
        return self._client

    def capital_for(self, trader: TraderLineage) -> Decimal:
        return self._book.capital_for(trader)

    def _contract(self, request: CiboRiskRequest) -> CTraderDemoBrokerContract:
        native = self._binding.contract(request.qore_symbol)
        try:
            source_size = self._source_contract_sizes[request.qore_symbol]
        except KeyError as error:
            raise CTraderDemoFreeSinkError(
                f"missing source contract size for {request.qore_symbol}"
            ) from error
        return CTraderDemoBrokerContract(
            qore_symbol=request.qore_symbol,
            provider_symbol=native.symbol_name,
            source_contract_size_units=source_size,
            ctrader_lot_size_units=native.lot_size_units,
        )

    def submit(self, request: CiboRiskRequest, *, now: datetime | None = None) -> CTraderDemoFreeSubmitResult:
        observed = now or datetime.now(UTC)
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise CTraderDemoFreeSinkError("submit time must be timezone-aware")
        with self._lock:
            capital = self._book.capital_for(request.trader_id)
            # No cross-trade or per-trader busy gate lives in the DEMO sink.
            # Strategy-owned state decides whether another entry is legitimate.
            # Canonical idempotency prevents duplicate submission of the same signal.
            allocation = authorize_allocation_only(
                request,
                book=self._book,
                now=observed,
            )
            submission = build_allocation_only_submission(
                allocation,
                contract=self._contract(request),
                submitted_at=observed,
            )
            auth_id, auth_fingerprint, reservation_id = allocation_fence_values(allocation)
            staged = self._runtime.stage_risk_fence(
                submission,
                risk_authorization_id=auth_id,
                risk_authorization_fingerprint=auth_fingerprint,
                risk_reservation_id=reservation_id,
            )
            if isinstance(staged, Failure):
                raise CTraderDemoFreeSinkError(str(staged.error))
            sent = self._runtime.submit_authorized(submission)
            if isinstance(sent, Failure):
                raise CTraderDemoFreeSinkError(str(sent.error))
            client_order_id = f"qore-{submission.idempotency_key.value.hex[:24]}"
            recorded_at = datetime.now(UTC)
            position_id: int | None = None
            open_for_trader = [
                item for item in self._positions.positions()
                if item.trader_id is request.trader_id
            ]
            if len(open_for_trader) == 1:
                position_id = open_for_trader[0].position_id
            self._registry.register(
                DemoTradeRegistryEntry(
                    trader=request.trader_id.value,
                    signal_fingerprint=request.signal_fingerprint,
                    request_id=request.request_id,
                    client_order_id=client_order_id,
                    provider_order_ref=sent.value.provider_order_ref,
                    qore_symbol=request.qore_symbol,
                    requested_volume=format(request.requested_volume, "f"),
                    requested_stop_risk=format(request.requested_stop_risk, "f"),
                    submitted_at=recorded_at.isoformat(),
                    expires_at=request.expires_at.isoformat(),
                    position_id=position_id,
                )
            )
            result = CTraderDemoFreeSubmitResult(
                state="SUBMITTED",
                trader_id=request.trader_id,
                qore_symbol=request.qore_symbol,
                requested_volume=request.requested_volume,
                assigned_capital=allocation.assigned_capital,
                provider_order_ref=sent.value.provider_order_ref,
                client_order_id=client_order_id,
                position_id=position_id,
                recorded_at=recorded_at,
            )
            self._log_result(result, request)
            return result

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            account = self._positions.account_snapshot()
            positions = self._positions.positions()
            return {
                "balance": format(account.balance, "f"),
                "equity": format(account.equity, "f"),
                "net_unrealized_pnl": format(account.net_unrealized_pnl, "f"),
                "open_positions": len(positions),
                "open_by_trader": {
                    trader.value: sum(1 for item in positions if item.trader_id is trader)
                    for trader in self._book.allocations
                },
                "observed_at": account.observed_at.isoformat(),
            }

    def _log_result(self, result: CTraderDemoFreeSubmitResult, request: CiboRiskRequest) -> None:
        self._log(
            {
                "event": "CTRADER_DEMO_FREE_SUBMIT",
                "state": result.state,
                "trader": result.trader_id.value,
                "symbol": result.qore_symbol,
                "signal_fingerprint": request.signal_fingerprint,
                "requested_volume": format(result.requested_volume, "f"),
                "assigned_capital": format(result.assigned_capital, "f"),
                "provider_order_ref": result.provider_order_ref,
                "client_order_id": result.client_order_id,
                "position_id": result.position_id,
                "request_id": request.request_id,
                "side": request.side,
                "intended_entry": format(request.intended_entry, "f"),
                "stop_loss": format(request.stop_loss, "f"),
                "take_profit": format(request.take_profit, "f"),
                "requested_stop_risk": format(request.requested_stop_risk, "f"),
                "recorded_at": result.recorded_at.isoformat(),
            }
        )

    def _log(self, payload: dict[str, object]) -> None:
        row = dict(payload)
        row.setdefault("recorded_at", datetime.now(UTC).isoformat())
        with self._events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    def close(self) -> None:
        self._runtime.close()


def credentials_from_environment() -> CTraderOpenApiCredentials:
    required = {
        "client_id": os.environ.get("QORE_CTRADER_CLIENT_ID", ""),
        "client_secret": os.environ.get("QORE_CTRADER_CLIENT_SECRET", ""),
        "access_token": os.environ.get("QORE_CTRADER_ACCESS_TOKEN", ""),
        "refresh_token": os.environ.get("QORE_CTRADER_REFRESH_TOKEN", ""),
        "account_id": os.environ.get("QORE_CTRADER_DEMO_ACCOUNT_ID", ""),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise CTraderDemoFreeSinkError(
            "missing cTrader DEMO environment inputs: " + ",".join(missing)
        )
    try:
        account_id = int(required["account_id"])
    except ValueError as error:
        raise CTraderDemoFreeSinkError("cTrader DEMO account id must be numeric") from error
    return CTraderOpenApiCredentials(
        client_id=required["client_id"],
        client_secret=required["client_secret"],
        access_token=required["access_token"],
        refresh_token=required["refresh_token"],
        ctid_trader_account_id=account_id,
    )

_GLOBAL_SINK: CTraderDemoFreeSink | None = None


def configure_global_sink(sink: CTraderDemoFreeSink) -> None:
    global _GLOBAL_SINK
    if not isinstance(sink, CTraderDemoFreeSink):
        raise CTraderDemoFreeSinkError("global sink must be CTraderDemoFreeSink")
    if _GLOBAL_SINK is not None and _GLOBAL_SINK is not sink:
        raise CTraderDemoFreeSinkError("global cTrader DEMO sink already configured")
    _GLOBAL_SINK = sink


def global_sink() -> CTraderDemoFreeSink:
    if _GLOBAL_SINK is None:
        raise CTraderDemoFreeSinkError("global cTrader DEMO sink is not configured")
    return _GLOBAL_SINK


def demo_capital_for(trader: TraderLineage) -> Decimal:
    return global_sink().capital_for(trader)


def submit_demo_request(request: CiboRiskRequest) -> CTraderDemoFreeSubmitResult:
    return global_sink().submit(request)
