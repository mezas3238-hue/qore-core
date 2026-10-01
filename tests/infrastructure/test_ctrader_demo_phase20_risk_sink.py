from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from threading import Lock
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_risk_bridge import (
    authorize_phase20_demo_request,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    CiboDemoCapabilitySolvencyBudget,
)
from qore.infrastructure.ctrader_demo_allocation_only import (
    equal_active_trader_allocations,
)
from qore.infrastructure.ctrader_demo_free_sink import CTraderDemoFreeSink
from qore.infrastructure.ctrader_demo_trade_registry import (
    CTraderDemoTradeRegistry,
    DemoTradeRegistryEntry,
)
from qore.kernel.result import Success

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


class _Binding:
    @staticmethod
    def contract(symbol: str) -> SimpleNamespace:
        assert symbol == "EURUSD"
        return SimpleNamespace(
            symbol_name="EURUSD",
            lot_size_units=Decimal("100000"),
        )


class _Runtime:
    def __init__(self) -> None:
        self.fences: list[dict[str, str]] = []
        self.submissions: list[object] = []

    def stage_risk_fence(self, submission, **kwargs):
        del submission
        self.fences.append(dict(kwargs))
        return Success(None)

    def submit_authorized(self, submission):
        self.submissions.append(submission)
        return Success(SimpleNamespace(provider_order_ref="demo-risk-1"))


class _Positions:
    @staticmethod
    def positions() -> tuple[SimpleNamespace, ...]:
        return (
            SimpleNamespace(
                trader_id=TraderLineage.R38_EURUSD,
                qore_symbol="EURUSD",
                position_id=9001,
            ),
        )


class _Registry:
    def __init__(self) -> None:
        self.rows: list[DemoTradeRegistryEntry] = []

    def register(self, entry: DemoTradeRegistryEntry) -> None:
        self.rows.append(entry)


class _Behavior:
    @staticmethod
    def record_raw(payload, *, source: str) -> None:
        del payload, source


def _request() -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id="risk-sink-1",
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="risk-sink-signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        requested_volume=Decimal("10"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        stop_loss_per_volume=Decimal("5"),
        margin_per_volume=Decimal("20"),
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        capital_provenance=(
            CiboCapitalProvenanceLot(
                source_kind="ORIGINAL_BASE_CAPITAL",
                source_id="demo-base",
                amount_usd=Decimal("50"),
            ),
        ),
    )


def _snapshot() -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="ctrader-demo-risk-sink",
        equity=Decimal("100"),
        margin_used=Decimal("0"),
        free_margin=Decimal("100"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100"),
        provider_budget=CiboDemoCapabilitySolvencyBudget(
            provider_headroom=Decimal("100"),
            max_risk_at_any_time=Decimal("100"),
            active_mll=Decimal("0"),
            hard_breach=False,
        ),
        reconciled_at=NOW,
    )


def _sink(tmp_path: Path) -> tuple[CTraderDemoFreeSink, _Runtime, _Registry]:
    sink = object.__new__(CTraderDemoFreeSink)
    runtime = _Runtime()
    registry = _Registry()
    object.__setattr__(sink, "_root", tmp_path)
    object.__setattr__(sink, "_binding", _Binding())
    object.__setattr__(
        sink,
        "_book",
        equal_active_trader_allocations(Decimal("700000")),
    )
    object.__setattr__(sink, "_client", None)
    object.__setattr__(sink, "_runtime", runtime)
    object.__setattr__(sink, "_positions", _Positions())
    object.__setattr__(sink, "_registry", registry)
    object.__setattr__(
        sink,
        "_source_contract_sizes",
        {"EURUSD": Decimal("100000")},
    )
    object.__setattr__(sink, "_events", tmp_path / "events.jsonl")
    object.__setattr__(sink, "_behavior", _Behavior())
    object.__setattr__(sink, "_lock", Lock())
    return sink, runtime, registry


def test_sink_uses_risk_reduce_and_persists_request_vs_authorized(
    tmp_path: Path,
) -> None:
    risk = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )
    request = _request()
    risk_result = authorize_phase20_demo_request(
        risk=risk,
        request=request,
        snapshot=_snapshot(),
        observed_at=NOW,
    )
    assert risk_result.execution_request is not None
    assert risk_result.execution_request.requested_volume == Decimal("5")

    sink, runtime, registry = _sink(tmp_path)
    result = sink.submit(
        request,
        risk_authorization=risk_result.authorization,
        now=NOW,
    )

    assert result.state == "SUBMITTED"
    assert len(runtime.submissions) == 1
    assert runtime.fences == [
        {
            "risk_authorization_id": (
                risk_result.authorization.authorization_id
            ),
            "risk_authorization_fingerprint": (
                risk_result.authorization.authorization_fingerprint
            ),
            "risk_reservation_id": (
                risk_result.authorization.authorization_id
            ),
        }
    ]
    row = registry.rows[0]
    assert row.requested_volume == "10"
    assert row.authorized_source_volume == "5"
    assert row.risk_decision == "REDUCE"
    assert (
        row.risk_authorization_id
        == risk_result.authorization.authorization_id
    )
    assert row.risk_authorized_stop_risk_usd == "25"
    assert row.risk_authorized_margin_usd == "100"
    assert row.capital_provenance == (
        ("ORIGINAL_BASE_CAPITAL", "demo-base", "25"),
    )


def test_registry_round_trip_preserves_risk_provenance(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    registry = CTraderDemoTradeRegistry(path)
    row = DemoTradeRegistryEntry(
        trader=TraderLineage.R38_EURUSD.value,
        signal_fingerprint="risk-registry-signal",
        request_id="risk-registry-request",
        client_order_id="client-1",
        provider_order_ref="provider-1",
        qore_symbol="EURUSD",
        requested_volume="10",
        requested_stop_risk="50",
        submitted_at=NOW.isoformat(),
        expires_at=(NOW + timedelta(minutes=5)).isoformat(),
        authorized_source_volume="5",
        risk_authorization_id="risk-auth-1",
        risk_authorization_fingerprint="a" * 64,
        risk_decision="REDUCE",
        risk_authorized_at=NOW.isoformat(),
        risk_authorized_margin_usd="100",
        risk_authorized_stop_risk_usd="25",
        capital_provenance=(
            ("ORIGINAL_BASE_CAPITAL", "demo-base", "25"),
        ),
    )
    registry.register(row)

    restarted = CTraderDemoTradeRegistry(path)
    assert restarted.entries() == (row,)
