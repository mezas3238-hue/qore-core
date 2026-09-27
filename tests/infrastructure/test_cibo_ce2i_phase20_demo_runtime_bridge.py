from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_runtime_bridge import (
    observe_ctrader_demo_m5_phase20_epoch,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_m5_shadow_batch import (
    Phase20M5ShadowTerminal,
    build_ctrader_demo_m5_observed_opportunity,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.r34_xauusd_live import R34LiveSignal
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)

OPENED = datetime(2026, 9, 27, 19, 30, tzinfo=UTC)
DEADLINE = OPENED + timedelta(seconds=2)
SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY")


def _bars(symbol_index: int) -> tuple[Bar, ...]:
    rows: list[Bar] = []
    base = Decimal("100") + Decimal(symbol_index * 10)
    for index in range(100):
        opened = OPENED - timedelta(minutes=5 * (100 - index))
        close = base + Decimal(index) / Decimal("1000")
        rows.append(
            Bar(
                opened_at=opened,
                closed_at=opened + timedelta(minutes=5),
                open=close - Decimal("0.01"),
                high=close + Decimal("0.10"),
                low=close - Decimal("0.10"),
                close=close,
            )
        )
    return tuple(rows)


def _snapshot(symbol: str, index: int) -> M5BoundarySnapshot:
    observed = OPENED + timedelta(milliseconds=100)
    bars = _bars(index)
    return M5BoundarySnapshot(
        symbol=symbol,
        anchor=OPENED,
        evidence=Evidence(symbol=symbol, digits=5, bars=bars),
        current_open=bars[-1].close,
        broker_tick_at=observed,
        observed_at=observed,
        new_bar_first_seen_at=observed,
        market_state_updated_at=observed,
        aggregate_finished_at=observed,
        complete_bars=bars,
        h1=(),
        h4=(),
        d1=(),
    )


def _spec(symbol: str) -> CTraderDemoSymbolSpecification:
    return CTraderDemoSymbolSpecification(
        provider_symbol=symbol,
        bid=Decimal("100.00"),
        ask=Decimal("100.01"),
        spread_points=Decimal("1"),
        digits=2,
        point=Decimal("0.01"),
        contract_size=Decimal("1"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("1"),
        minimum_stop_distance_points=Decimal("1"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("10"),
        trade_enabled=True,
        session_open=True,
        observed_at=OPENED + timedelta(milliseconds=100),
        open_commission_per_lot_usd=Decimal("0"),
    )


def _account_state() -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal("1000"),
        equity=Decimal("1000"),
        margin=Decimal("0"),
        free_margin=Decimal("1000"),
        observed_at=OPENED + timedelta(milliseconds=150),
    )


def _capital() -> VersionedCapitalSourceLedger:
    return VersionedCapitalSourceLedger(
        generation=1,
        ledger=CapitalSourceLedger().add_source(
            source_id="phase20d-demo-assigned-base:test",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("1000"),
        ),
    )


def _terminals(
    *,
    candidate: Phase20M5ShadowTerminal | None = None,
) -> tuple[Phase20M5ShadowTerminal, ...]:
    rows: list[Phase20M5ShadowTerminal] = []
    for index, symbol in enumerate(SYMBOLS):
        identity = {
            "XAUUSD": "R34_XAUUSD",
            "EURUSD": "R38_EURUSD",
            "GBPUSD": "R43_GBPUSD",
            "GBPJPY": "R38_GBPJPY",
            "AUDJPY": "R42_AUDJPY",
        }[symbol]
        if candidate is not None and candidate.identity == identity:
            rows.append(candidate)
            continue
        rows.append(
            Phase20M5ShadowTerminal(
                identity=identity,
                symbol=symbol,
                observed_at=OPENED + timedelta(
                    milliseconds=200 + index * 10
                ),
                disposition=Phase20ForwardPopulationDisposition.ABSTAIN,
                reason="CAUSAL_ABSTAIN",
            )
        )
    return tuple(rows)


def _observe(
    tmp_path: Path,
    *,
    terminals: tuple[Phase20M5ShadowTerminal, ...],
):
    evidence = DurablePhase20ForwardEvidenceStore(
        tmp_path / "forward-evidence.json"
    )
    policy = DurablePhase20ForwardPolicyStore(
        tmp_path / "forward-policy.json"
    )
    risk = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )
    result = observe_ctrader_demo_m5_phase20_epoch(
        epoch_scope="ctrader-demo:m5:test",
        opened_at=OPENED,
        deadline_at=DEADLINE,
        terminals=terminals,
        snapshots=tuple(
            _snapshot(symbol, index)
            for index, symbol in enumerate(SYMBOLS)
        ),
        provider_specs=tuple(_spec(symbol) for symbol in SYMBOLS),
        evidence_store=evidence,
        policy_store=policy,
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref="demo-runtime-bridge",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        account_state=_account_state(),
        risk=risk,
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        open_position_ids=(),
        pending_broker_worst_case_loss_usd=Decimal("0"),
        capital_state=_capital(),
        highest_closed_balance=Decimal("1000"),
        current_step=0,
    )
    return result, evidence, policy


def test_runtime_bridge_seals_zero_candidate_epoch_without_execution(
    tmp_path: Path,
) -> None:
    result, evidence, policy = _observe(
        tmp_path,
        terminals=_terminals(),
    )

    assert result.broker_mutation_performed is False
    assert result.execution_authority is False
    assert result.regime_policy_sha256.startswith("sha256:")
    assert evidence.load().generation == 1
    assert policy.load().generation == 1
    decision = evidence.load().decisions[0]
    assert decision.signal_fingerprints == ()


def test_runtime_bridge_seals_candidate_before_any_broker_action(
    tmp_path: Path,
) -> None:
    spec = _spec("XAUUSD")
    signal = R34LiveSignal(
        signal_fingerprint="b" * 64,
        entry_at=OPENED,
        timeframe="H1",
        side="long",
        certified_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        target_rank=1,
        target_route="TEST",
        decision_source="TEST",
        family=None,
        risk_scale=Decimal("1"),
    )
    opportunity = build_ctrader_demo_m5_observed_opportunity(
        identity="R34_XAUUSD",
        signal=signal,
        provider_spec=spec,
        observed_at=OPENED + timedelta(milliseconds=250),
    )
    candidate = Phase20M5ShadowTerminal(
        identity="R34_XAUUSD",
        symbol="XAUUSD",
        observed_at=OPENED + timedelta(milliseconds=250),
        disposition=Phase20ForwardPopulationDisposition.CANDIDATE,
        reason="VALID_TRADER_OPPORTUNITY",
        opportunity=opportunity,
    )

    result, evidence, policy = _observe(
        tmp_path,
        terminals=_terminals(candidate=candidate),
    )

    decision = evidence.load().decisions[0]
    assert decision.signal_fingerprints == ("b" * 64,)
    assert policy.load().decisions[0].evidence_sha256 == decision.evidence_sha256
    assert result.observation.broker_mutation_performed is False
