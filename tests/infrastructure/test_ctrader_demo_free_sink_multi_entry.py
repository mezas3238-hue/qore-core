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
from qore.infrastructure.ctrader_demo_allocation_only import equal_active_trader_allocations
from qore.infrastructure.ctrader_demo_free_sink import CTraderDemoFreeSink
from qore.kernel.result import Success

NOW = datetime(2026, 9, 24, 18, 0, tzinfo=UTC)


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
        self.submissions: list[object] = []

    def stage_risk_fence(self, submission, **kwargs):
        del submission, kwargs
        return Success(None)

    def submit_authorized(self, submission):
        self.submissions.append(submission)
        return Success(SimpleNamespace(provider_order_ref=f"demo-{len(self.submissions)}"))


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


class _Behavior:
    @staticmethod
    def record_raw(payload, *, source: str) -> None:
        del payload, source


class _Registry:
    def __init__(self) -> None:
        self.entries: list[object] = []

    def register(self, entry) -> None:
        self.entries.append(entry)


def _request(sequence: int, volume: str) -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=f"same-trader-{sequence}",
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint=f"{sequence:064x}",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10000"),
        stop_loss=Decimal("1.09500"),
        take_profit=Decimal("1.11000"),
        requested_volume=Decimal(volume),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("500"),
        margin_per_volume=Decimal("1000"),
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        strategy_requested_risk_usd=None,
        capital_provenance=(
            CiboCapitalProvenanceLot(
                source_kind="ORIGINAL_BASE_CAPITAL",
                source_id=f"demo-base-{sequence}",
                amount_usd=Decimal(volume) * Decimal("500"),
            ),
        ),
    )


def _sink(tmp_path: Path) -> tuple[CTraderDemoFreeSink, _Runtime]:
    sink = object.__new__(CTraderDemoFreeSink)
    runtime = _Runtime()
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
    object.__setattr__(sink, "_registry", _Registry())
    object.__setattr__(sink, "_behavior", _Behavior())
    object.__setattr__(
        sink,
        "_source_contract_sizes",
        {"EURUSD": Decimal("100000")},
    )
    events = tmp_path / "events.jsonl"
    object.__setattr__(sink, "_events", events)
    object.__setattr__(sink, "_lock", Lock())
    return sink, runtime


def test_same_trader_open_position_does_not_block_second_or_third_cibo_entry(
    tmp_path: Path,
) -> None:
    sink, runtime = _sink(tmp_path)
    risk = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )
    snapshot = AccountRiskSnapshot(
        account_binding_id="demo-multi-entry",
        equity=Decimal("100000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("100000"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100000"),
        provider_budget=CiboDemoCapabilitySolvencyBudget(
            provider_headroom=Decimal("100000"),
            max_risk_at_any_time=Decimal("100000"),
            active_mll=Decimal("0"),
            hard_breach=False,
        ),
        reconciled_at=NOW,
    )

    results = []
    for sequence, volume in ((1, "0.10"), (2, "0.20"), (3, "0.30")):
        request = _request(sequence, volume)
        decision = authorize_phase20_demo_request(
            risk=risk,
            request=request,
            snapshot=snapshot,
            observed_at=NOW + timedelta(seconds=sequence),
        )
        assert decision.execution_request is not None
        results.append(
            sink.submit(
                request,
                risk_authorization=decision.authorization,
                now=NOW + timedelta(seconds=sequence),
            )
        )

    assert [item.state for item in results] == ["SUBMITTED", "SUBMITTED", "SUBMITTED"]
    assert [item.requested_volume for item in results] == [
        Decimal("0.10"),
        Decimal("0.20"),
        Decimal("0.30"),
    ]
    assert len(runtime.submissions) == 3
    assert "SKIPPED_TRADER_BUSY" not in (tmp_path / "events.jsonl").read_text(
        encoding="utf-8"
    )
